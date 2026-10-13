"""Corre uma bateria de cenários e escreve a tabela comparativa em dados/resultados/comparacao_*.csv.

Uso (a partir de backend/):
    uv run python scripts/comparar_cenarios.py --sementes 42 7 13 --incidente

Cada linha é uma corrida completa (~2-3 min). A tabela é o que alimenta os gráficos da monografia
(secção 3.10: média, desvio-padrão e comparação antes/depois).
"""

import argparse
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from gestao_trafego.simulacao.executar import PASTA_RESULTADOS, executar_simulacao, pasta_de_resultados  # noqa: E402

# (nome na tabela, cenário, com vias alternativas)
CONFIGURACOES = [
    ("fixo", "fixo", False),
    ("local", "local", False),
    ("local+vias", "local", True),
    ("coordenado", "coordenado", False),
    ("coordenado+vias", "coordenado", True),
]
COLUNAS = [
    "configuracao", "semente", "escala", "incidente", "espera_media_s", "perda_de_tempo_media_s",
    "duracao_viagem_media_s", "fila_media_veiculos", "fila_maxima_veiculos", "velocidade_media_ms",
    "veiculos_concluidos", "veiculos_nao_concluidos", "teleportes", "tempo_simulado_s",
]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--sementes", type=int, nargs="+", default=[42, 7, 13])
    parser.add_argument("--escala", type=float, default=1.0)
    parser.add_argument("--incidente", action="store_true")
    parser.add_argument("--saltar-existentes", action="store_true", help="não repete corridas que já têm resumo.json (lê-o para a tabela)")
    parser.add_argument("--etiqueta", default="", help="sufixo do ficheiro, para não sobrescrever outra bateria")
    parser.add_argument("--configuracoes", nargs="+", default=[c[0] for c in CONFIGURACOES])
    argumentos = parser.parse_args()

    destino = PASTA_RESULTADOS / f"comparacao_x{argumentos.escala}{'_incidente' if argumentos.incidente else ''}{argumentos.etiqueta}.csv"
    destino.parent.mkdir(parents=True, exist_ok=True)
    with destino.open("w", newline="", encoding="utf-8") as f:
        escritor = csv.DictWriter(f, fieldnames=COLUNAS)
        escritor.writeheader()
        for nome, cenario, vias in CONFIGURACOES:
            if nome not in argumentos.configuracoes:
                continue
            for semente in argumentos.sementes:
                existente = pasta_de_resultados(cenario, semente, argumentos.escala, argumentos.incidente, vias) / "resumo.json"
                if argumentos.saltar_existentes and existente.exists():
                    r = json.loads(existente.read_text(encoding="utf-8"))
                    print(f"{nome:16} s{semente:<3} (já existia)", flush=True)
                else:
                    r = executar_simulacao(
                        cenario, semente=semente, escala=argumentos.escala,
                        incidente=argumentos.incidente, vias_alternativas=vias,
                    )
                escritor.writerow({"configuracao": nome, **{c: r[c] for c in COLUNAS if c != "configuracao"}})
                f.flush()
                print(f"{nome:16} s{semente:<3} espera={r['espera_media_s']:.1f} fila={r['fila_media_veiculos']:.1f} "
                      f"nao_concluidos={r['veiculos_nao_concluidos']} teleportes={r['teleportes']}", flush=True)
    print(f"Tabela em {destino}")


if __name__ == "__main__":
    main()
