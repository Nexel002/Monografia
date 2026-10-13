"""Preparação dos dados para a previsão de congestionamento.

Cada série é a sequência, de 10 em 10 segundos, de [veículos parados, veículos na rede, velocidade
média] de uma simulação. A previsão pergunta: dada a última janela de `recuo` passos, quantos
veículos parados haverá daqui a `h` passos? Lógica pura (numpy), sem PyTorch.
"""

from dataclasses import dataclass

import numpy as np

PASSO_S = 10  # intervalo entre amostras de serie.csv
COLUNA_ALVO = 0  # veículos parados: a medida de congestionamento que o controlo também usa


@dataclass(frozen=True)
class Janelas:
    entradas: np.ndarray  # (N, recuo, n_variaveis)
    alvos: np.ndarray  # (N, n_horizontes): parados daqui a cada horizonte
    instantes_alvo_s: np.ndarray  # (N, n_horizontes): tempo (s) a que cada alvo diz respeito
    origem: np.ndarray  # (N,): índice da série de onde veio a janela


def janelas_deslizantes(series: list[np.ndarray], recuo: int, horizontes_passos: tuple[int, ...]) -> Janelas:
    """Todas as janelas possíveis de cada série. Uma série curta de mais não dá nenhuma."""
    maximo = max(horizontes_passos)
    entradas, alvos, instantes, origem = [], [], [], []
    for indice, serie in enumerate(series):
        for fim in range(recuo, len(serie) - maximo + 1):  # `fim` = primeiro passo ainda por observar
            entradas.append(serie[fim - recuo : fim])
            ultimo = fim - 1
            alvos.append([serie[ultimo + h, COLUNA_ALVO] for h in horizontes_passos])
            instantes.append([(ultimo + h + 1) * PASSO_S for h in horizontes_passos])
            origem.append(indice)
    n_variaveis = series[0].shape[1] if series else 0
    return Janelas(
        np.asarray(entradas, dtype=np.float32).reshape(-1, recuo, n_variaveis),
        np.asarray(alvos, dtype=np.float32).reshape(-1, len(horizontes_passos)),
        np.asarray(instantes, dtype=np.float32).reshape(-1, len(horizontes_passos)),
        np.asarray(origem, dtype=np.int64),
    )


def previsao_por_persistencia(janelas: Janelas) -> np.ndarray:
    """Linha de base: «daqui a h passos estará igual ao último valor visto».

    É a previsão que o LSTM tem de bater para justificar a sua existência. Em séries lentas é difícil
    de bater, por isso é a comparação honesta.
    """
    ultimo = janelas.entradas[:, -1, COLUNA_ALVO]
    return np.repeat(ultimo[:, None], janelas.alvos.shape[1], axis=1)


def erro_absoluto_medio(previsto: np.ndarray, real: np.ndarray) -> np.ndarray:
    """Um valor por horizonte (coluna)."""
    return np.abs(previsto - real).mean(axis=0)


@dataclass(frozen=True)
class Normalizacao:
    media: np.ndarray
    desvio: np.ndarray

    @staticmethod
    def ajustar(entradas: np.ndarray) -> "Normalizacao":
        plano = entradas.reshape(-1, entradas.shape[-1])
        # Desvio zero (variável constante) daria divisão por zero: fica 1 e a variável passa só centrada.
        return Normalizacao(plano.mean(axis=0), np.where(plano.std(axis=0) < 1e-6, 1.0, plano.std(axis=0)))

    def aplicar(self, entradas: np.ndarray) -> np.ndarray:
        return ((entradas - self.media) / self.desvio).astype(np.float32)
