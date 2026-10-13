"""Corre uma simulação no SUMO via TraCI e grava as métricas.

Uso (a partir de backend/):
    uv run python -m gestao_trafego.simulacao.executar --cenario fixo

O cenário `fixo` deixa os semáforos com os programas de tempo fixo que o netconvert gerou: é o
cenário de referência (o funcionamento actual em Maputo) contra o qual se mede o sistema inteligente.
A simulação em si vive em `sessao.py`; aqui só se corre até ao fim e se gravam os resultados.
"""

import argparse
import csv
import json
from pathlib import Path

from gestao_trafego.controlo.coordenador.anti_bloqueio import ParametrosDoCoordenador
from gestao_trafego.controlo.local.max_pressure import ParametrosLocais
from gestao_trafego.simulacao.metricas import Amostra, ler_viagens, resumir
from gestao_trafego.simulacao.sessao import CENARIO_PROCURA, CENARIOS, RAIZ, SessaoDeSimulacao

PASTA_RESULTADOS = RAIZ / "dados" / "resultados"

INTERVALO_AMOSTRA_S = 10  # a cada passo seria CSV enorme sem ganho para os gráficos
# Depois de a procura acabar, deixa-se a rede esvaziar. Sem tecto, uma rede bloqueada nunca terminava.
MARGEM_PARA_ESVAZIAR_S = 3600


def pasta_de_resultados(
    cenario: str, semente: int, escala: float, incidente: bool, vias_alternativas: bool, limite_s: int | None = None
) -> Path:
    """Onde ficam os resultados de uma corrida. Um limite explícito (ensaio curto) vai no nome: sem isso, um
    ensaio de 30 minutos sobrescrevia os resultados da corrida completa com o mesmo cenário, semente e escala."""
    sufixo_limite = f"_lim{limite_s}" if limite_s else ""
    sufixo_eventos = ("_incidente" if incidente else "") + ("_vias" if vias_alternativas else "")
    return PASTA_RESULTADOS / f"{cenario}_s{semente}_x{escala}{sufixo_eventos}{sufixo_limite}"


def executar_simulacao(
    cenario: str = "fixo",
    semente: int = 42,
    escala: float = 1.0,
    limite_s: int | None = None,
    pasta_saida: Path | None = None,
    parametros_locais: ParametrosLocais | None = None,
    parametros_coordenador: ParametrosDoCoordenador | None = None,
    incidente: bool = False,
    vias_alternativas: bool = False,
) -> dict:
    """Devolve o resumo de KPIs e deixa tripinfo.xml, serie.csv e resumo.json em `pasta_saida`."""
    if cenario not in CENARIOS:
        raise ValueError(f"Cenário desconhecido: {cenario!r} (existem: {', '.join(CENARIOS)}).")

    duracao_procura_s = json.loads(CENARIO_PROCURA.read_text(encoding="utf-8"))["duracao_s"]
    limite_s_pedido = limite_s
    limite_s = limite_s or duracao_procura_s + MARGEM_PARA_ESVAZIAR_S
    pasta = pasta_saida or pasta_de_resultados(cenario, semente, escala, incidente, vias_alternativas, limite_s_pedido)

    amostras: list[Amostra] = []
    sessao = SessaoDeSimulacao(
        cenario, semente, escala, incidente, vias_alternativas, pasta, parametros_locais, parametros_coordenador
    )
    with sessao:
        while sessao.tempo_s < limite_s and not sessao.terminou():
            sessao.passo()
            if sessao.tempo_s % INTERVALO_AMOSTRA_S == 0:
                amostras.append(sessao.amostra())
        nao_concluidos = sessao.nao_concluidos()
    # O tripinfo só fica completo depois de a sessão fechar o SUMO.

    resumo = resumir(
        ler_viagens(pasta / "tripinfo.xml"), amostras, nao_concluidos, sessao.teleportes, sessao.colisoes, sessao.tempo_s
    )
    resumo.update(
        {"cenario": cenario, "semente": semente, "escala": escala, "incidente": incidente,
         "vias_alternativas": vias_alternativas}
    )

    with (pasta / "serie.csv").open("w", newline="", encoding="utf-8") as f:
        escritor = csv.writer(f)
        escritor.writerow(["tempo_s", "veiculos_na_rede", "veiculos_parados", "velocidade_media_ms"])
        for a in amostras:
            escritor.writerow([a.tempo_s, a.veiculos_na_rede, a.veiculos_parados, f"{a.velocidade_media_ms:.3f}"])
    (pasta / "resumo.json").write_text(json.dumps(resumo, indent=2, ensure_ascii=False), encoding="utf-8")
    return resumo


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--cenario", default="fixo", choices=CENARIOS)
    parser.add_argument("--semente", type=int, default=42)
    parser.add_argument("--escala", type=float, default=1.0, help="multiplica a procura (0,5 = hora normal)")
    parser.add_argument("--limite", type=int, default=None, help="tempo máximo simulado, em segundos")
    parser.add_argument("--incidente", action="store_true", help="corta a Av. 24 de Julho durante 10 minutos")
    parser.add_argument("--vias-alternativas", action="store_true", help="recomenda rotas alternativas a 50 %% dos condutores")
    parser.add_argument("--verde-minimo", type=float, default=ParametrosLocais.verde_minimo_s)
    parser.add_argument("--histerese", type=float, default=ParametrosLocais.histerese)
    argumentos = parser.parse_args()
    parametros = ParametrosLocais(verde_minimo_s=argumentos.verde_minimo, histerese=argumentos.histerese)
    resumo = executar_simulacao(
        argumentos.cenario, argumentos.semente, argumentos.escala, argumentos.limite, parametros_locais=parametros,
        incidente=argumentos.incidente, vias_alternativas=argumentos.vias_alternativas,
    )
    print(json.dumps(resumo, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
