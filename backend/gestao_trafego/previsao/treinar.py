"""Treina e avalia o LSTM com as simulações guardadas na base de dados.

Uso (a partir de backend/; importar primeiro: `python -m gestao_trafego.dados.importar`):
    uv run python -m gestao_trafego.previsao.treinar

A divisão treino/teste é POR SEMENTE, não por execução. A mesma semente dá a mesma procura nas cinco
configurações; se uma execução ficasse no treino e outra da mesma semente no teste, o modelo seria
avaliado em tráfego que já viu e o erro sairia optimista.
"""

import argparse
import json
from pathlib import Path

import numpy as np

from gestao_trafego.dados import repositorio
from gestao_trafego.dados.ligacao import ligar
from gestao_trafego.previsao.dataset import (
    PASSO_S,
    erro_absoluto_medio,
    janelas_deslizantes,
    previsao_por_persistencia,
)
from gestao_trafego.previsao.caminhos import CAMINHO_DAS_METRICAS, CAMINHO_DO_MODELO
from gestao_trafego.previsao.modelo import treinar

MODELO = "lstm"
HORIZONTES_S = (60, 180, 300)
RECUO_PASSOS = 30  # 5 minutos de histórico


def _series_por_execucao(ligacao) -> list[tuple[dict, np.ndarray]]:
    resultado = []
    for execucao in repositorio.listar_execucoes(ligacao):
        amostras = repositorio.serie_da_execucao(ligacao, execucao["id"])
        matriz = np.array(
            [[a["veiculos_parados"], a["veiculos_na_rede"], a["velocidade_media_ms"]] for a in amostras], dtype=np.float32
        )
        resultado.append((execucao, matriz))
    return resultado


def treinar_e_avaliar(
    sementes_de_teste: tuple[int, ...] = (5, 13), epocas: int = 40, escondido: int = 32, guardar: bool = True, url: str | None = None
) -> dict:
    horizontes = tuple(h // PASSO_S for h in HORIZONTES_S)
    with ligar(url) as ligacao:
        todas = _series_por_execucao(ligacao)
        treino = [(e, m) for e, m in todas if e["semente"] not in sementes_de_teste]
        teste = [(e, m) for e, m in todas if e["semente"] in sementes_de_teste]
        if not treino or not teste:
            raise ValueError("É preciso haver execuções de treino e de teste (importar os resultados primeiro).")

        janelas_treino = janelas_deslizantes([m for _, m in treino], RECUO_PASSOS, horizontes)
        janelas_teste = janelas_deslizantes([m for _, m in teste], RECUO_PASSOS, horizontes)
        modelo, perdas = treinar(janelas_treino, horizontes, RECUO_PASSOS, epocas=epocas, escondido=escondido)

        previsto_lstm = modelo.prever(janelas_teste.entradas)
        previsto_persistencia = previsao_por_persistencia(janelas_teste)
        erro_lstm = erro_absoluto_medio(previsto_lstm, janelas_teste.alvos)
        erro_persistencia = erro_absoluto_medio(previsto_persistencia, janelas_teste.alvos)

        if guardar:
            modelo.guardar(CAMINHO_DO_MODELO)
            # Previsões do teste na base de dados, para o dashboard mostrar «previsto contra real».
            for indice, (execucao, _) in enumerate(teste):
                mascara = janelas_teste.origem == indice
                for coluna, horizonte_s in enumerate(HORIZONTES_S):
                    repositorio.guardar_previsoes(
                        ligacao, MODELO, execucao["id"], horizonte_s,
                        [
                            (int(t), float(p), float(r))
                            for t, p, r in zip(
                                janelas_teste.instantes_alvo_s[mascara, coluna],
                                previsto_lstm[mascara, coluna],
                                janelas_teste.alvos[mascara, coluna],
                            )
                        ],
                    )

    # Por configuração: com semáforos de tempo fixo o ciclo é periódico e mais fácil de prever; separar
    # mostra se o LSTM só aprendeu o ciclo ou também prevê o tráfego sob controlo adaptativo.
    por_configuracao = {}
    for configuracao in sorted({e["configuracao"] for e, _ in teste}):
        indices = [i for i, (e, _) in enumerate(teste) if e["configuracao"] == configuracao]
        mascara = np.isin(janelas_teste.origem, indices)
        e_lstm = erro_absoluto_medio(previsto_lstm[mascara], janelas_teste.alvos[mascara])
        e_pers = erro_absoluto_medio(previsto_persistencia[mascara], janelas_teste.alvos[mascara])
        por_configuracao[configuracao] = [
            {"horizonte_s": h, "mae_lstm_veiculos": float(e_lstm[i]), "mae_persistencia_veiculos": float(e_pers[i])}
            for i, h in enumerate(HORIZONTES_S)
        ]

    metricas = {
        "fila_media_do_teste_veiculos": float(janelas_teste.alvos.mean()),
        "recuo_s": RECUO_PASSOS * PASSO_S,
        "sementes_de_teste": list(sementes_de_teste),
        "execucoes_de_treino": len(treino),
        "execucoes_de_teste": len(teste),
        "janelas_de_treino": int(len(janelas_treino.alvos)),
        "janelas_de_teste": int(len(janelas_teste.alvos)),
        "epocas": epocas,
        "perda_final": perdas[-1],
        "por_horizonte": [
            {
                "horizonte_s": h,
                "mae_lstm_veiculos": float(erro_lstm[i]),
                "mae_persistencia_veiculos": float(erro_persistencia[i]),
                "melhoria_percentual": float(100 * (1 - erro_lstm[i] / erro_persistencia[i])) if erro_persistencia[i] else 0.0,
            }
            for i, h in enumerate(HORIZONTES_S)
        ],
        "por_configuracao": por_configuracao,
    }
    if guardar:
        CAMINHO_DAS_METRICAS.write_text(json.dumps(metricas, indent=2, ensure_ascii=False), encoding="utf-8")
    return metricas


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--sementes-de-teste", type=int, nargs="+", default=[5, 13])
    parser.add_argument("--epocas", type=int, default=40)
    argumentos = parser.parse_args()
    print(json.dumps(treinar_e_avaliar(tuple(argumentos.sementes_de_teste), argumentos.epocas), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
