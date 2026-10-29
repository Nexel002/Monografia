"""Testes estatísticos emparelhados sobre as simulações guardadas na base de dados.

Uso (a partir de backend/):
    uv run python scripts/testes_estatisticos.py

Para cada cenário compara, semente a semente (a mesma procura nas duas configurações), a espera média de
cada configuração com a do tempo fixo e, em separado, as comparações que isolam o efeito de cada peça:
as vias alternativas (local+vias contra local) e a coordenação (coordenado contra local).
Escreve também dados/resultados/testes_estatisticos.json.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from gestao_trafego.comum.configuracao import RAIZ  # noqa: E402
from gestao_trafego.comum.estatistica import ajuste_de_holm, comparar_emparelhado  # noqa: E402
from gestao_trafego.dados.ligacao import ligar  # noqa: E402

CENARIOS = {
    "hora_de_ponta_com_via_cortada": (True, 1.0),
    "hora_de_ponta": (False, 1.0),
    "hora_normal": (False, 0.5),
}
# (alternativa, referência, o que isola)
COMPARACOES = [
    ("local", "fixo", "controlo adaptativo local"),
    ("local+vias", "fixo", "local + vias alternativas"),
    ("coordenado", "fixo", "coordenado"),
    ("coordenado+vias", "fixo", "sistema completo (coordenado + vias)"),
    ("local+vias", "local", "efeito das vias alternativas (sobre o local)"),
    ("coordenado", "local", "efeito da coordenação (sobre o local)"),
    ("coordenado+vias", "local+vias", "efeito da coordenação (com as vias)"),
]


def esperas(ligacao, incidente: bool, escala: float) -> dict[str, dict[int, float]]:
    linhas = ligacao.execute(
        "SELECT configuracao, semente, espera_media_s FROM execucao WHERE incidente = %s AND escala = %s",
        (incidente, escala),
    ).fetchall()
    por_configuracao: dict[str, dict[int, float]] = {}
    for l in linhas:
        por_configuracao.setdefault(l["configuracao"], {})[l["semente"]] = l["espera_media_s"]
    return por_configuracao


def main() -> None:
    resultado: dict = {}
    with ligar() as ligacao:
        for cenario, (incidente, escala) in CENARIOS.items():
            dados = esperas(ligacao, incidente, escala)
            resultado[cenario] = []
            print(f"\n{cenario.replace('_', ' ').upper()}")
            print(f"{'comparação':48}{'redução':>9}{'melhorou':>10}{'p Wilcoxon':>12}{'p Holm*':>9}")
            for alternativa, referencia, rotulo in COMPARACOES:
                if alternativa not in dados or referencia not in dados:
                    continue
                sementes = sorted(set(dados[alternativa]) & set(dados[referencia]))  # só as sementes comuns às duas
                r = comparar_emparelhado([dados[referencia][s] for s in sementes], [dados[alternativa][s] for s in sementes])
                resultado[cenario].append({"comparacao": rotulo, "alternativa": alternativa, "referencia": referencia, **r})
            # Holm sobre as 4 comparações face ao tempo fixo (a pergunta principal); as outras são exploratórias.
            principais = [x for x in resultado[cenario] if x["referencia"] == "fixo"]
            for x, ajustado in zip(principais, ajuste_de_holm([x["p_wilcoxon"] for x in principais]), strict=True):
                x["p_wilcoxon_holm"] = ajustado
            for r in resultado[cenario]:
                holm = f"{r['p_wilcoxon_holm']:9.4f}" if "p_wilcoxon_holm" in r else f"{'—':>9}"
                print(f"{r['comparacao']:48}{r['reducao_percentual']:+8.1f}%{r['sementes_que_melhoraram']:>6}/{r['sementes']:<3}{r['p_wilcoxon']:12.4f}{holm}")
    destino = RAIZ / "dados" / "resultados" / "testes_estatisticos.json"
    destino.write_text(json.dumps(resultado, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nEscrito em {destino}")
    print("* Holm: correcção para as 4 comparações face ao tempo fixo de cada cenário; as restantes são exploratórias.")
    print("Convenção: redução positiva = menos espera do que a referência; p < 0,05 = diferença estatisticamente significativa.")


if __name__ == "__main__":
    main()
