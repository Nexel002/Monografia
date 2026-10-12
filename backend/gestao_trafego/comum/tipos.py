"""Contratos partilhados entre simulação, controlo e (mais tarde) API.

Só dados, sem lógica de SUMO: é isto que deixa o controlo ser testado sem simulador e,
no futuro, ligado a semáforos reais em vez do SUMO.
"""

from dataclasses import dataclass

# Comprimento médio que um veículo ocupa parado: ~4,5 m de carro + ~2,5 m de distância de
# segurança. Serve para converter o comprimento de uma faixa na sua capacidade em veículos.
ESPACO_POR_VEICULO_M = 7.5

# A fila junto ao semáforo mede-se contra, no máximo, este número de veículos (~150 m). Sem este
# tecto, uma faixa de entrada de 1 km nunca parecia cheia: 20 carros parados davam «15 % de
# ocupação» e perdiam a pressão contra uma saída curta, deixando essa fila sem verde.
FILA_DE_REFERENCIA_VEICULOS = 20


@dataclass(frozen=True)
class Movimento:
    """Um fluxo que o semáforo deixa passar: de uma faixa de entrada para uma faixa de saída."""

    faixa_entrada: str
    faixa_saida: str


@dataclass(frozen=True)
class FaseVerde:
    """Uma fase com verde (as de amarelo são geradas pelo controlador, não escolhidas)."""

    indice: int  # posição no programa de tempo fixo original
    estado: str  # estado vermelho/amarelo/verde de cada sinal, ex.: "GGrrGg"
    movimentos: tuple[Movimento, ...]


@dataclass(frozen=True)
class TopologiaDoNo:
    id: str
    fases: tuple[FaseVerde, ...]


@dataclass(frozen=True)
class LeituraDeFaixa:
    veiculos: int
    parados: int
    capacidade: float  # em veículos

    @property
    def ocupacao(self) -> float:
        """0 = vazia, 1 = cheia (risco de a saída bloquear o cruzamento anterior)."""
        return min(1.0, self.veiculos / self.capacidade) if self.capacidade > 0 else 0.0

    @property
    def fila(self) -> float:
        """0 = sem fila, 1 = fila de referência parada. Só conta os veículos parados."""
        referencia = min(self.capacidade, FILA_DE_REFERENCIA_VEICULOS)
        return min(1.0, self.parados / referencia) if referencia > 0 else 0.0


@dataclass(frozen=True)
class OrdemDeModo:
    """Ordem da camada 2 (coordenador) a um cruzamento. A omissão é «sem ordem»."""

    faixas_vedadas: frozenset[str] = frozenset()  # faixas de saída que não devem receber mais carros
    peso_saida: float = 1.0  # quanto pesa, na pressão, encher a faixa de saída (>1 = mais cautela)


@dataclass(frozen=True)
class ContagemPorVia:
    """O que a visão entrega ao resto do sistema: tráfego de uma via numa janela de tempo.

    É o mesmo tipo de dado que, na simulação, os detectores do SUMO produzem; o controlo só vê isto,
    venha de uma câmara ou do simulador.
    """

    via: str
    inicio_s: float
    fim_s: float
    por_tipo: dict[str, int]
    fila_media_veiculos: float  # veículos parados a montante da linha, em média na janela

    @property
    def total(self) -> int:
        return sum(self.por_tipo.values())

    @property
    def fluxo_veiculos_por_hora(self) -> float:
        duracao = self.fim_s - self.inicio_s
        return self.total * 3600 / duracao if duracao > 0 else 0.0
