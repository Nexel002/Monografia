"""Junta as tabelas de dados/resultados/comparacao_*.csv e resume por configuração.

Uso (a partir de backend/):
    uv run python scripts/resumir_comparacao.py dados/resultados/comparacao_a.csv comparacao_b.csv ...
"""

import csv
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

linhas = [l for caminho in sys.argv[1:] for l in csv.DictReader(Path(caminho).open(encoding="utf-8"))]
por_conf = defaultdict(dict)
for l in linhas:
    por_conf[l["configuracao"]][int(l["semente"])] = l

sementes = sorted(set.intersection(*(set(d) for d in por_conf.values())))
fixo = {s: float(por_conf["fixo"][s]["espera_media_s"]) for s in sementes}
print(f"sementes comuns a todas as configurações ({len(sementes)}): {sementes}")
print(f"{'configuração':16} {'espera média':>12} {'desvio':>7} {'mediana':>8} {'vs fixo':>8} {'melhor que fixo':>16} {'teleportes (soma)':>18}")
for nome, d in por_conf.items():
    e = [float(d[s]["espera_media_s"]) for s in sementes]
    tele = sum(int(d[s]["teleportes"]) for s in sementes)
    melhor = sum(1 for s, v in zip(sementes, e) if v < fixo[s])
    variacao = (st.mean(e) / st.mean(fixo.values()) - 1) * 100
    print(f"{nome:16} {st.mean(e):12.1f} {st.pstdev(e):7.1f} {st.median(e):8.1f} {variacao:+7.0f}% {melhor:>10}/{len(sementes)} {tele:18d}")
