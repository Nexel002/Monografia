"""Importa para o PostgreSQL os resultados que as simulações e a visão deixaram em dados/resultados/.

Uso (a partir de backend/):
    uv run python -m gestao_trafego.dados.importar

É idempotente: importar duas vezes dá o mesmo estado (cada execução é substituída pelo nome).
"""

import csv
import json
from pathlib import Path

from gestao_trafego.comum.configuracao import RAIZ
from gestao_trafego.dados import repositorio
from gestao_trafego.dados.ligacao import ligar

PASTA_RESULTADOS = RAIZ / "dados" / "resultados"


def _ler_serie(caminho: Path) -> list[dict]:
    with caminho.open(encoding="utf-8") as f:
        return [
            {
                "tempo_s": int(linha["tempo_s"]),
                "veiculos_na_rede": int(linha["veiculos_na_rede"]),
                "veiculos_parados": int(linha["veiculos_parados"]),
                "velocidade_media_ms": float(linha["velocidade_media_ms"]),
            }
            for linha in csv.DictReader(f)
        ]


def importar(pasta_resultados: Path = PASTA_RESULTADOS, url: str | None = None) -> dict[str, int]:
    execucoes = contagens = ignoradas = 0
    with ligar(url) as ligacao:
        for pasta in sorted(p for p in pasta_resultados.iterdir() if p.is_dir()):
            resumo_sim, serie, contagem = pasta / "resumo.json", pasta / "serie.csv", pasta / "contagem.json"
            if resumo_sim.exists() and serie.exists():
                # Ensaios curtos (`_limN`) cortam a simulação a meio: as médias deles não são comparáveis.
                if "_lim" in pasta.name:
                    ignoradas += 1
                    continue
                resumo = json.loads(resumo_sim.read_text(encoding="utf-8"))
                repositorio.guardar_execucao(ligacao, pasta.name, resumo, _ler_serie(serie))
                execucoes += 1
            elif contagem.exists():
                janelas = json.loads(contagem.read_text(encoding="utf-8")).get("janelas")
                if janelas:
                    repositorio.guardar_contagens(ligacao, pasta.name, janelas)
                    contagens += len(janelas)
                else:
                    ignoradas += 1
    return {"execucoes": execucoes, "janelas_de_contagem": contagens, "ignoradas": ignoradas}


if __name__ == "__main__":
    print(json.dumps(importar(), indent=2))
