"""Camada 2 — coordenador da rede: impede que um cruzamento encha a rua que o seguinte não escoa.

O Max-Pressure local só vê a rua de saída imediata. Quando essa rua enche porque o cruzamento
seguinte também está parado, o local continua a despejar nela e o bloqueio sobe a avenida nó a nó
(*spillback*). O coordenador vê a rede toda e dá a cada nó uma ordem: «não mandes carros para
estas faixas». A ordem propaga-se para montante: se o nó B não consegue escoar a faixa f, f conta
como bloqueada para o nó A que a alimenta, mesmo antes de estar cheia.

Lógica pura: recebe leituras e devolve ordens. Não importa `traci`.
"""

from dataclasses import dataclass

from gestao_trafego.comum.tipos import LeituraDeFaixa, OrdemDeModo, TopologiaDoNo


@dataclass(frozen=True)
class ParametrosDoCoordenador:
    limiar_alto: float = 0.6  # ocupação a partir da qual uma faixa passa a bloqueada
    limiar_baixo: float = 0.35  # só deixa de estar bloqueada abaixo disto (histerese: não oscilar)
    limiar_propagacao: float = 0.4  # faixa já a encher cuja saída está toda bloqueada
    # Válvula de alívio. Num anel de ruas cheias (A espera por B, B por C, C por A) a vedação
    # eterna é um impasse: ao fim de `vedacao_maxima_s` liberta-se a faixa por `alivio_s`.
    vedacao_maxima_s: float = 45.0
    alivio_s: float = 20.0
    peso_saida: float = 2.0  # cautela dos nós com alguma saída vedada


class CoordenadorAntiBloqueio:
    def __init__(
        self,
        topologias: dict[str, TopologiaDoNo],
        parametros: ParametrosDoCoordenador | None = None,
    ):
        self.parametros = parametros or ParametrosDoCoordenador()
        self._saidas_por_no: dict[str, set[str]] = {}
        # Para cada faixa de entrada de um nó: as faixas para onde esse nó a despeja.
        self._destinos_da_entrada: dict[str, set[str]] = {}
        for no_id, topologia in topologias.items():
            saidas: set[str] = set()
            for fase in topologia.fases:
                for m in fase.movimentos:
                    saidas.add(m.faixa_saida)
                    self._destinos_da_entrada.setdefault(m.faixa_entrada, set()).add(m.faixa_saida)
            self._saidas_por_no[no_id] = saidas
        self._saturadas: set[str] = set()
        self._desde_s: dict[str, float] = {}
        self._alivio_ate_s: dict[str, float] = {}

    def _actualizar_saturacao(self, tempo_s: float, leitura: dict[str, LeituraDeFaixa]) -> set[str]:
        p = self.parametros
        for faixa, dados in leitura.items():
            if faixa in self._saturadas:
                if dados.ocupacao <= p.limiar_baixo:
                    self._saturadas.discard(faixa)
                elif tempo_s - self._desde_s[faixa] > p.vedacao_maxima_s:
                    self._alivio_ate_s[faixa] = tempo_s + p.alivio_s
                    self._desde_s[faixa] = tempo_s + p.alivio_s
            elif dados.ocupacao >= p.limiar_alto:
                self._saturadas.add(faixa)
                self._desde_s[faixa] = tempo_s
        return {f for f in self._saturadas if tempo_s >= self._alivio_ate_s.get(f, 0.0)}

    def _propagar(self, bloqueadas: set[str], leitura: dict[str, LeituraDeFaixa]) -> set[str]:
        """Uma faixa a encher cujos destinos estão todos bloqueados também não escoa."""
        propagacao = self.parametros.limiar_propagacao
        bloqueadas = set(bloqueadas)
        for _ in range(len(self._destinos_da_entrada)):  # o ponto fixo demora, no máximo, tantas voltas
            novas = {
                entrada
                for entrada, destinos in self._destinos_da_entrada.items()
                if entrada not in bloqueadas
                and entrada in leitura
                and leitura[entrada].ocupacao >= propagacao
                and destinos <= bloqueadas
            }
            if not novas:
                break
            bloqueadas |= novas
        return bloqueadas

    def passo(self, tempo_s: float, leitura: dict[str, LeituraDeFaixa]) -> dict[str, OrdemDeModo]:
        """Ordem para cada nó. Um nó sem faixas a vedar recebe a ordem neutra."""
        bloqueadas = self._propagar(self._actualizar_saturacao(tempo_s, leitura), leitura)
        ordens = {}
        for no_id, saidas in self._saidas_por_no.items():
            vedadas = frozenset(saidas & bloqueadas)
            ordens[no_id] = (
                OrdemDeModo(vedadas, self.parametros.peso_saida) if vedadas else OrdemDeModo()
            )
        return ordens
