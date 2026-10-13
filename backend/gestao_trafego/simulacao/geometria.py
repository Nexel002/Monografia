"""Geometria da rede para desenhar o mapa no dashboard: ruas, e a posição de cada sinal de semáforo.

As coordenadas ficam nas unidades do SUMO (metros, y para cima). Quem desenha converte para o ecrã.
"""

from functools import lru_cache
from pathlib import Path

import sumolib

from gestao_trafego.simulacao.sessao import REDE


@lru_cache(maxsize=1)
def _ler_rede(caminho: Path):
    return sumolib.net.readNet(str(caminho), withInternal=False, withPrograms=True)


def geometria_da_rede(caminho: Path = REDE) -> dict:
    rede = _ler_rede(caminho)
    x_min, y_min, x_max, y_max = rede.getBoundary()

    ruas = []
    for aresta in rede.getEdges():
        ruas.append(
            {
                "id": aresta.getID(),
                "nome": aresta.getName(),
                "faixas": aresta.getLaneNumber(),
                # arredondar a 1 casa (décimos de metro) reduz o JSON sem perda visível
                "pontos": [[round(x, 1), round(y, 1)] for x, y in aresta.getShape()],
            }
        )

    semaforos = []
    for semaforo in rede.getTrafficLights():
        # Um sinal por ligação controlada, no fim da faixa de entrada (a linha de paragem): é aí que
        # o dashboard põe a bolinha vermelha/amarela/verde. A ordem bate com o estado do SUMO.
        sinais = []
        ligacoes_por_indice = semaforo.getLinks()  # índice do sinal -> [[faixa de entrada, faixa de saída, n.º]]
        for indice in sorted(ligacoes_por_indice):
            entrada = ligacoes_por_indice[indice][0][0]
            x, y = entrada.getShape()[-1]
            sinais.append([round(x, 1), round(y, 1)])
        no = rede.getNode(semaforo.getID()) if rede.hasNode(semaforo.getID()) else None
        semaforos.append({"id": semaforo.getID(), "centro": list(no.getCoord()) if no else None, "sinais": sinais})

    return {
        "limites": {"x_min": x_min, "y_min": y_min, "x_max": x_max, "y_max": y_max},
        "ruas": ruas,
        "semaforos": semaforos,
    }
