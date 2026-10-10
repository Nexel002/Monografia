"""KPIs da simulação (secções 3.8 e 3.10 da monografia).

Funções puras: recebem os dados já lidos e devolvem números. Assim testam-se sem correr o SUMO
e servem tanto o cenário de tempo fixo como o inteligente, o que garante que a comparação
mede exactamente a mesma coisa nos dois lados.
"""

from dataclasses import dataclass
from pathlib import Path
from statistics import mean, pstdev
from xml.etree import ElementTree as ET


@dataclass(frozen=True)
class Viagem:
    espera_s: float  # tempo parado (velocidade < 0,1 m/s): é o "tempo de espera" da monografia
    perda_de_tempo_s: float  # tempo a mais face a andar sempre à velocidade permitida
    duracao_s: float


@dataclass(frozen=True)
class Amostra:
    tempo_s: int
    veiculos_na_rede: int
    veiculos_parados: int
    velocidade_media_ms: float


def ler_viagens(tripinfo: Path) -> list[Viagem]:
    """Só aparecem aqui os veículos que chegaram ao destino."""
    raiz = ET.parse(tripinfo).getroot()
    return [
        Viagem(
            espera_s=float(v.get("waitingTime")),
            perda_de_tempo_s=float(v.get("timeLoss")),
            duracao_s=float(v.get("duration")),
        )
        for v in raiz.iter("tripinfo")
    ]


def resumir(
    viagens: list[Viagem],
    amostras: list[Amostra],
    nao_concluidos: int,
    teleportes: int,
    colisoes: int,
    tempo_simulado_s: int,
) -> dict:
    """Junta tudo no resumo que o dashboard e a monografia vão ler.

    `nao_concluidos` conta os veículos ainda na rede no fim: se for alto, a média de espera dos
    que chegaram está optimista, porque os piores casos ainda não terminaram.
    """
    esperas = [v.espera_s for v in viagens]
    return {
        "tempo_simulado_s": tempo_simulado_s,
        "veiculos_concluidos": len(viagens),
        "veiculos_nao_concluidos": nao_concluidos,
        "espera_media_s": mean(esperas) if esperas else 0.0,
        "espera_desvio_padrao_s": pstdev(esperas) if esperas else 0.0,
        "perda_de_tempo_media_s": mean(v.perda_de_tempo_s for v in viagens) if viagens else 0.0,
        "duracao_viagem_media_s": mean(v.duracao_s for v in viagens) if viagens else 0.0,
        "fila_media_veiculos": mean(a.veiculos_parados for a in amostras) if amostras else 0.0,
        "fila_maxima_veiculos": max((a.veiculos_parados for a in amostras), default=0),
        "velocidade_media_ms": mean(a.velocidade_media_ms for a in amostras) if amostras else 0.0,
        # Teleporte = o SUMO tirou um veículo preso há >300 s: sinal de bloqueio total da rede.
        "teleportes": teleportes,
        "colisoes": colisoes,
    }
