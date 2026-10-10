"""Ponte entre o SUMO (TraCI) e o controlo.

É o único sítio, além de `executar.py`, que conhece o `traci`. Traduz o simulador para os tipos
de `comum/` e aplica no simulador o que o controlo decide.
"""

import traci.constants as tc
from traci import trafficlight

from gestao_trafego.comum.tipos import (
    ESPACO_POR_VEICULO_M,
    FaseVerde,
    LeituraDeFaixa,
    Movimento,
    TopologiaDoNo,
)

# Um programa com uma só fase que praticamente nunca expira: é o que impede o SUMO de retomar o
# seu programa de tempo fixo por cima das nossas decisões.
_DURACAO_QUE_NUNCA_EXPIRA_S = 86400


def _e_fase_verde(estado: str) -> bool:
    return any(s in "Gg" for s in estado) and not any(s in "yY" for s in estado)


class PonteSumo:
    def __init__(self, ligacao):
        self._ligacao = ligacao
        self._capacidade: dict[str, float] = {}

    def descobrir_topologias(self) -> dict[str, TopologiaDoNo]:
        """Lê do programa de tempo fixo quais são as fases verdes e que fluxos cada uma abre."""
        topologias = {}
        for no_id in self._ligacao.trafficlight.getIDList():
            logica = self._ligacao.trafficlight.getAllProgramLogics(no_id)[0]
            ligacoes = self._ligacao.trafficlight.getControlledLinks(no_id)
            fases = []
            for indice, fase in enumerate(logica.phases):
                if not _e_fase_verde(fase.state):
                    continue
                movimentos = tuple(
                    Movimento(ligacoes[sinal][0][0], ligacoes[sinal][0][1])
                    for sinal, estado in enumerate(fase.state)
                    if estado in "Gg" and ligacoes[sinal]
                )
                fases.append(FaseVerde(indice, fase.state, movimentos))
            topologias[no_id] = TopologiaDoNo(no_id, tuple(fases))
        return topologias

    def subscrever_faixas(self, topologias: dict[str, TopologiaDoNo]) -> None:
        """Subscrição: o SUMO devolve todas as faixas de uma vez em vez de uma chamada por faixa."""
        faixas = {
            f
            for t in topologias.values()
            for fase in t.fases
            for m in fase.movimentos
            for f in (m.faixa_entrada, m.faixa_saida)
        }
        for faixa in faixas:
            self._capacidade[faixa] = max(1.0, self._ligacao.lane.getLength(faixa) / ESPACO_POR_VEICULO_M)
            self._ligacao.lane.subscribe(faixa, [tc.LAST_STEP_VEHICLE_NUMBER, tc.LAST_STEP_VEHICLE_HALTING_NUMBER])

    def ler_faixas(self) -> dict[str, LeituraDeFaixa]:
        resultados = self._ligacao.lane.getAllSubscriptionResults()
        return {
            faixa: LeituraDeFaixa(
                veiculos=dados[tc.LAST_STEP_VEHICLE_NUMBER],
                parados=dados[tc.LAST_STEP_VEHICLE_HALTING_NUMBER],
                capacidade=self._capacidade[faixa],
            )
            for faixa, dados in resultados.items()
        }

    def assumir_controlo(self, no_id: str, estado_inicial: str) -> None:
        fase = trafficlight.Phase(_DURACAO_QUE_NUNCA_EXPIRA_S, estado_inicial)
        self._ligacao.trafficlight.setProgramLogic(no_id, trafficlight.Logic("controlo", 0, 0, phases=[fase]))

    def aplicar_estado(self, no_id: str, estado: str) -> None:
        self._ligacao.trafficlight.setRedYellowGreenState(no_id, estado)
