"""Camada 1 — controlo local de um cruzamento por Max-Pressure.

A cada fase atribui-se uma «pressão»: quanto enche as faixas que serve menos quanto enchem as
faixas para onde despeja. O cruzamento dá verde à fase de maior pressão, ou seja, serve a fila
maior sem mandar carros para uma rua já cheia. É por isto que o Max-Pressure coordena nós
vizinhos sem mensagens: a ocupação da rua de saída de um nó é a fila de entrada do seguinte.

Lógica pura: recebe leituras e devolve o estado dos sinais. Não importa `traci`.
"""

from dataclasses import dataclass

from gestao_trafego.comum.tipos import LeituraDeFaixa, OrdemDeModo, TopologiaDoNo


@dataclass(frozen=True)
class ParametrosLocais:
    # Com 10 s o cruzamento trocava de fase de 15 em 15 s e gastava ~25 % do tempo em amarelos:
    # a espera média ficava pior do que o tempo fixo. Com 20 s, melhora (ver plano, Fase 2).
    verde_minimo_s: float = 20.0
    # Se a fase aberta já não tem nenhum veículo à frente, não vale a pena segurá-la tanto tempo.
    # Diagnóstico da semente 13: C4 mantinha 14 s de verde numa fase vazia, enquanto a Av. de
    # Tanzânia tinha 18 carros parados à espera.
    verde_minimo_sem_procura_s: float = 5.0
    verde_maximo_s: float = 60.0  # impede que uma fase fique com o cruzamento para sempre
    amarelo_s: float = 4.0
    # Sem isto, uma travessa com pouco tráfego nunca ganhava a pressão e esperava indefinidamente.
    vermelho_maximo_s: float = 120.0
    # Só se troca de fase se a nova ganhar por mais do que isto; evita oscilar a cada segundo
    # entre duas fases de pressão quase igual, o que gastaria o ciclo em amarelos.
    histerese: float = 0.2


def estado_de_amarelo(estado_actual: str, estado_alvo: str) -> str:
    """Sinais que fecham passam a amarelo; os que continuam abertos mantêm-se; o resto fica vermelho."""
    return "".join(
        ("G" if actual in "Gg" and alvo in "Gg" else "y" if actual in "Gg" else "r")
        for actual, alvo in zip(estado_actual, estado_alvo, strict=True)
    )


class ControladorLocal:
    def __init__(self, topologia: TopologiaDoNo, parametros: ParametrosLocais | None = None):
        if not topologia.fases:
            raise ValueError(f"O nó {topologia.id} não tem nenhuma fase verde.")
        self.topologia = topologia
        self.parametros = parametros or ParametrosLocais()
        self.fase = 0
        self.estado = topologia.fases[0].estado
        self._inicio_verde_s = 0.0
        self._ultimo_verde_s = {i: 0.0 for i in range(len(topologia.fases))}
        self._alvo: int | None = None
        self._fim_do_amarelo_s = 0.0
        self._ordem = OrdemDeModo()

    def receber_ordem(self, ordem: OrdemDeModo) -> None:
        """Ordem da camada 2. Sem ordem (a neutra), o nó comporta-se como Max-Pressure puro."""
        self._ordem = ordem

    def _fase_vedada(self, indice_fase: int) -> bool:
        """Uma fase está vedada quando TODOS os seus fluxos despejam em faixas bloqueadas."""
        movimentos = self.topologia.fases[indice_fase].movimentos
        return bool(movimentos) and all(m.faixa_saida in self._ordem.faixas_vedadas for m in movimentos)

    def pressao(self, indice_fase: int, leitura: dict[str, LeituraDeFaixa]) -> float:
        """Soma, por faixa de entrada servida, (fila de entrada − ocupação média das saídas).

        A entrada mede-se pela fila parada junto ao semáforo e a saída pela ocupação total da
        faixa: o que interessa à entrada é quem espera, e à saída é se há espaço para receber.
        """
        saidas_por_entrada: dict[str, list[float]] = {}
        for m in self.topologia.fases[indice_fase].movimentos:
            # Uma faixa fora da rede recortada não tem leitura: conta como vazia (escoa livremente).
            ocupacao_saida = leitura[m.faixa_saida].ocupacao if m.faixa_saida in leitura else 0.0
            if m.faixa_saida in self._ordem.faixas_vedadas:
                ocupacao_saida = 1.0  # a camada 2 diz que não escoa: tratar como cheia
            saidas_por_entrada.setdefault(m.faixa_entrada, []).append(ocupacao_saida)
        total = 0.0
        for faixa_entrada, saidas in saidas_por_entrada.items():
            fila_entrada = leitura[faixa_entrada].fila if faixa_entrada in leitura else 0.0
            total += fila_entrada - self._ordem.peso_saida * sum(saidas) / len(saidas)
        return total

    def _tem_procura(self, indice_fase: int, leitura: dict[str, LeituraDeFaixa]) -> bool:
        return any(
            leitura[m.faixa_entrada].veiculos > 0
            for m in self.topologia.fases[indice_fase].movimentos
            if m.faixa_entrada in leitura
        )

    def _escolher_fase(self, tempo_s: float, leitura: dict[str, LeituraDeFaixa]) -> int:
        p = self.parametros
        todas = range(len(self.topologia.fases))
        # Fases vedadas pela camada 2 não são candidatas, a menos que sejam todas: um cruzamento
        # que não abre nenhuma fase deixa de ser cruzamento e bloqueia a rede de outra maneira.
        candidatas = [i for i in todas if not self._fase_vedada(i)] or list(todas)

        esperando = [
            (tempo_s - self._ultimo_verde_s[i], i)
            for i in candidatas
            if i != self.fase
            and tempo_s - self._ultimo_verde_s[i] > p.vermelho_maximo_s
            and self._tem_procura(i, leitura)
        ]
        if esperando:
            return max(esperando)[1]

        pressoes = {i: self.pressao(i, leitura) for i in candidatas}
        # Em empate de pressão ganha a fase que já está aberta (não gasta um amarelo à toa).
        melhor = max(candidatas, key=lambda i: (pressoes[i], i == self.fase))
        verde_s = tempo_s - self._inicio_verde_s

        if self.fase not in candidatas:
            # A fase aberta passou a despejar só em faixas bloqueadas: sair já, sem histerese.
            return melhor if self._tem_procura(melhor, leitura) else self.fase
        if verde_s >= p.verde_maximo_s:
            outras = [i for i in candidatas if i != self.fase and pressoes[i] > 0]
            return max(outras, key=lambda i: pressoes[i]) if outras else self.fase
        if melhor != self.fase and pressoes[melhor] > pressoes[self.fase] + p.histerese:
            return melhor
        return self.fase

    def passo(self, tempo_s: float, leitura: dict[str, LeituraDeFaixa]) -> str:
        """Devolve o estado dos sinais a aplicar neste segundo."""
        if self._alvo is not None:
            if tempo_s >= self._fim_do_amarelo_s:
                self.fase, self._alvo = self._alvo, None
                self._inicio_verde_s = tempo_s
                self.estado = self.topologia.fases[self.fase].estado
            return self.estado

        self._ultimo_verde_s[self.fase] = tempo_s
        minimo = (
            self.parametros.verde_minimo_s
            if self._tem_procura(self.fase, leitura)
            else self.parametros.verde_minimo_sem_procura_s
        )
        if tempo_s - self._inicio_verde_s < minimo:
            return self.estado

        proxima = self._escolher_fase(tempo_s, leitura)
        if proxima != self.fase:
            self._alvo = proxima
            self._fim_do_amarelo_s = tempo_s + self.parametros.amarelo_s
            self.estado = estado_de_amarelo(self.estado, self.topologia.fases[proxima].estado)
        return self.estado
