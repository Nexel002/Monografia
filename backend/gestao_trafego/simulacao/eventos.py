"""Eventos que perturbam a simulação: o incidente que corta uma via.

A aresta que se corta é escolhida de propósito: tem de estar no eixo principal da procura, senão
o incidente passa despercebido e o cenário não testa nada.
"""

import json
from dataclasses import dataclass
from pathlib import Path

from gestao_trafego.simulacao.metricas import PREFIXO_VEICULO_DO_INCIDENTE

_ROTA_DO_INCIDENTE = "rota_do_incidente"


@dataclass(frozen=True)
class Incidente:
    aresta: str
    inicio_s: int
    duracao_s: int
    posicao_m: float


def carregar_incidente(caminho: Path) -> Incidente:
    dados = json.loads(caminho.read_text(encoding="utf-8"))
    return Incidente(dados["aresta"], dados["inicio_s"], dados["duracao_s"], dados["posicao_m"])


class GestorDeIncidente:
    """Imobiliza um veículo em cada faixa da aresta durante `duracao_s`."""

    def __init__(self, ligacao, incidente: Incidente):
        self._ligacao = ligacao
        self._incidente = incidente
        self._ocorreu = False

    def passo(self, tempo_s: int) -> None:
        if self._ocorreu or tempo_s < self._incidente.inicio_s:
            return
        self._ocorreu = True
        i = self._incidente
        self._ligacao.route.add(_ROTA_DO_INCIDENTE, [i.aresta])
        for faixa in range(self._ligacao.edge.getLaneNumber(i.aresta)):
            veiculo = f"{PREFIXO_VEICULO_DO_INCIDENTE}{faixa}"
            self._ligacao.vehicle.add(
                veiculo,
                _ROTA_DO_INCIDENTE,
                typeID="carro",
                depart="now",
                departLane=str(faixa),
                departPos=str(i.posicao_m),
                departSpeed="0",
            )
            self._ligacao.vehicle.setStop(veiculo, i.aresta, pos=i.posicao_m, laneIndex=faixa, duration=i.duracao_s)
