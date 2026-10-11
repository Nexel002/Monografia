"""Recomendação de vias alternativas: manda recalcular a rota pelo tempo de viagem actual.

Na vida real seria um painel ou uma app; aqui, `conformidade` é a fracção de condutores que segue
a recomendação. Quem não segue mantém a rota que já tinha, como hoje.
"""

import zlib

from gestao_trafego.simulacao.metricas import PREFIXO_VEICULO_DO_INCIDENTE


class RecomendadorDeRotas:
    def __init__(self, ligacao, conformidade: float = 0.5, periodo_s: int = 30):
        self._ligacao = ligacao
        self._conformidade = conformidade
        self._periodo_s = periodo_s

    def _segue_a_recomendacao(self, veiculo: str) -> bool:
        # Determinístico por veículo (e não sorteado a cada vez) para a corrida ser repetível
        # e o mesmo condutor ser sempre «obediente» ou «teimoso» ao longo da viagem.
        return zlib.crc32(veiculo.encode()) % 100 < self._conformidade * 100

    def passo(self, tempo_s: int) -> None:
        if tempo_s % self._periodo_s:
            return
        for veiculo in self._ligacao.vehicle.getIDList():
            if veiculo.startswith(PREFIXO_VEICULO_DO_INCIDENTE) or not self._segue_a_recomendacao(veiculo):
                continue
            self._ligacao.vehicle.rerouteTraveltime(veiculo)
