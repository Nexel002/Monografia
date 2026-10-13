"""As funções que o assistente pode usar para consultar os resultados.

São TODAS de leitura e devolvem números já calculados. O assistente (um modelo de linguagem) não escreve
SQL livre, não corre simulações e não toca nos semáforos: escolhe uma destas funções, recebe o resultado e
explica-o. Cada resultado traz a sua `fonte` e, quando é o caso, um `aviso` (valores assumidos, dados que não
existem), para o assistente os repetir em vez de os esconder.
"""

import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import psycopg

from gestao_trafego.comum.configuracao import RAIZ
from gestao_trafego.dados import repositorio
from gestao_trafego.previsao.caminhos import CAMINHO_DAS_METRICAS

PROCURA = RAIZ / "dados" / "cenarios" / "procura_hora_de_ponta.json"

# nome para o assistente -> (incidente, escala)
CENARIOS = {
    "hora_de_ponta_com_via_cortada": (True, 1.0),
    "hora_de_ponta": (False, 1.0),
    "hora_normal": (False, 0.5),
}
_AVISO_SIMULACAO = "São resultados de simulação com procura assumida (sem dados de campo), não medições reais."


@dataclass(frozen=True)
class Ferramenta:
    nome: str
    descricao: str
    parametros: dict  # esquema JSON (subconjunto aceite pelo Gemini)
    executar: Callable[[psycopg.Connection, dict], dict[str, Any]]

    def declaracao(self) -> dict:
        return {"name": self.nome, "description": self.descricao, "parameters": self.parametros}


def _sem_parametros() -> dict:
    return {"type": "OBJECT", "properties": {}}


def comparar_configuracoes(ligacao: psycopg.Connection, args: dict) -> dict:
    cenario = args.get("cenario", "hora_de_ponta_com_via_cortada")
    if cenario not in CENARIOS:
        return {"erro": f"Cenário desconhecido: {cenario!r}.", "cenarios_validos": list(CENARIOS)}
    incidente, escala = CENARIOS[cenario]
    linhas = repositorio.comparar_configuracoes(ligacao, incidente, escala)
    fixo = next((l for l in linhas if l["configuracao"] == "fixo"), None)
    return {
        "cenario": cenario,
        "unidade": "segundos de espera média por veículo (menos é melhor)",
        "linhas": [
            {
                "configuracao": l["configuracao"],
                "sementes": l["sementes"],
                "espera_media_s": round(l["espera_media_s"], 1),
                "desvio_padrao_s": round(l["espera_desvio_s"], 1) if l["espera_desvio_s"] is not None else None,
                "variacao_face_ao_tempo_fixo_pct": round(100 * (l["espera_media_s"] / fixo["espera_media_s"] - 1), 1)
                if fixo and l["configuracao"] != "fixo"
                else None,
                "fila_media_veiculos": round(l["fila_media_veiculos"], 1),
                "velocidade_media_kmh": round(l["velocidade_media_ms"] * 3.6, 1),
                "teleportes_somados": int(l["teleportes"]),
            }
            for l in linhas
        ],
        "fonte": "simulações SUMO guardadas na base de dados",
        "aviso": _AVISO_SIMULACAO + " A camada de coordenação sozinha não melhorou o controlo local; o ganho vem do controlo adaptativo e das vias alternativas.",
    }


def precisao_da_previsao(_: psycopg.Connection, __: dict) -> dict:
    if not CAMINHO_DAS_METRICAS.exists():
        return {"disponivel": False, "motivo": "O modelo de previsão ainda não foi treinado."}
    m = json.loads(CAMINHO_DAS_METRICAS.read_text(encoding="utf-8"))
    return {
        "disponivel": True,
        "unidade": "erro absoluto médio em veículos parados na rede; a fila média no teste foi "
        f"{m['fila_media_do_teste_veiculos']:.0f}",
        "por_horizonte": [
            {
                "horizonte_min": h["horizonte_s"] // 60,
                "erro_lstm": round(h["mae_lstm_veiculos"], 1),
                "erro_persistencia": round(h["mae_persistencia_veiculos"], 1),
                "melhoria_pct": round(h["melhoria_percentual"]),
            }
            for h in m["por_horizonte"]
        ],
        "por_configuracao": {
            c: [{"horizonte_min": h["horizonte_s"] // 60, "erro_lstm": round(h["mae_lstm_veiculos"], 1), "erro_persistencia": round(h["mae_persistencia_veiculos"], 1)} for h in hs]
            for c, hs in m["por_configuracao"].items()
        },
        "fonte": "avaliação do LSTM em execuções que não viu no treino",
        "aviso": "O ganho é grande nos semáforos de tempo fixo (ciclo regular); com controlo adaptativo é pequeno a 1 minuto e a 5 minutos não existe.",
    }


def contagens_da_visao(ligacao: psycopg.Connection, args: dict) -> dict:
    janelas = repositorio.listar_contagens(ligacao, args.get("origem"))
    if not janelas:
        return {"disponivel": False, "motivo": "Não há contagens de visão importadas."}
    por_origem: dict[str, list[dict]] = {}
    for j in janelas:
        por_origem.setdefault(j["origem"], []).append(j)
    resultado = []
    for origem, js in por_origem.items():
        por_tipo: dict[str, int] = {}
        for j in js:
            for tipo, n in j["por_tipo"].items():
                por_tipo[tipo] = por_tipo.get(tipo, 0) + n
        maior = max(js, key=lambda j: j["total"])
        resultado.append(
            {
                "processamento": origem,
                "total_contado": sum(j["total"] for j in js),
                "por_tipo": por_tipo,
                "janela_de_maior_fluxo": {"inicio_s": maior["inicio_s"], "veiculos": maior["total"], "fluxo_veiculos_por_hora": round(maior["fluxo_veiculos_por_hora"])},
                "fila_media_veiculos": round(sum(j["fila_media_veiculos"] for j in js) / len(js), 1),
            }
        )
    return {
        "processamentos": resultado,
        "fonte": "contagem de veículos por visão computacional (YOLO) nos vídeos de teste",
        "aviso": "A precisão da contagem não está medida contra uma contagem manual. Os vídeos não são de Maputo.",
    }


def procura_por_via(_: psycopg.Connection, __: dict) -> dict:
    dados = json.loads(PROCURA.read_text(encoding="utf-8"))
    fluxos = sorted(dados["fluxos"], key=lambda f: -f["veiculos_por_hora"])
    return {
        "unidade": "veículos por hora, na hora de ponta simulada",
        "vias_por_procura": [{"fluxo": f["id"], "descricao": f["descricao"], "veiculos_por_hora": f["veiculos_por_hora"]} for f in fluxos],
        "mistura_de_veiculos": {t["id"]: f"{round(100 * t['proporcao'])} %" for t in dados["tipos"]},
        "fonte": "ficheiro de procura do cenário",
        "aviso": "VALORES ASSUMIDOS: ainda não há contagens de campo (a planilha de observação não foi usada).",
    }


def indicadores_de_risco(ligacao: psycopg.Connection, _: dict) -> dict:
    linhas = ligacao.execute(
        "SELECT configuracao, SUM(colisoes) AS colisoes, SUM(teleportes) AS teleportes, COUNT(*) AS corridas "
        "FROM execucao GROUP BY configuracao"
    ).fetchall()
    return {
        "por_configuracao": [{"configuracao": l["configuracao"], "colisoes_simuladas": int(l["colisoes"]), "bloqueios_teleportes": int(l["teleportes"]), "corridas": int(l["corridas"])} for l in linhas],
        "fonte": "simulações SUMO",
        "aviso": "NÃO há dados de acidentes reais nem índice de sinistralidade. O simulador só dá colisões simuladas e «teleportes» "
        "(veículos retirados por estarem presos há mais de 5 min, sinal de bloqueio da rede). É um indicador indirecto.",
    }


def momentos_de_pico(ligacao: psycopg.Connection, args: dict) -> dict:
    configuracao = args.get("configuracao", "fixo")
    linhas = ligacao.execute(
        """
        SELECT (a.tempo_s / 600) * 10 AS minuto_inicial, AVG(a.veiculos_parados) AS parados, AVG(a.veiculos_na_rede) AS na_rede
        FROM amostra a JOIN execucao e ON e.id = a.execucao_id
        WHERE e.configuracao = %s AND e.escala = 1 AND e.incidente = TRUE
        GROUP BY 1 ORDER BY 1
        """,
        (configuracao,),
    ).fetchall()
    if not linhas:
        return {"disponivel": False, "motivo": f"Não há séries para a configuração {configuracao!r}."}
    pico = max(linhas, key=lambda l: l["parados"])
    return {
        "configuracao": configuracao,
        "unidade": "médias por intervalos de 10 minutos de simulação (média de todas as sementes)",
        "intervalos": [{"minuto_inicial": int(l["minuto_inicial"]), "veiculos_parados_medio": round(float(l["parados"]), 1), "veiculos_na_rede_medio": round(float(l["na_rede"]), 1)} for l in linhas],
        "intervalo_de_maior_congestionamento": {"minuto_inicial": int(pico["minuto_inicial"]), "veiculos_parados_medio": round(float(pico["parados"]), 1)},
        "fonte": "séries das simulações com via cortada aos 20 minutos",
        "aviso": "O «pico» é o da simulação (a hora de ponta e o incidente são assumidos), não uma hora do dia real.",
    }


FERRAMENTAS: list[Ferramenta] = [
    Ferramenta(
        "comparar_configuracoes",
        "Compara as cinco formas de controlar os semáforos (tempo fixo, local, local+vias, coordenado, coordenado+vias): espera média, "
        "fila, velocidade e variação face ao tempo fixo. Usar para perguntas sobre resultados, desempenho do sistema e melhorias.",
        {"type": "OBJECT", "properties": {"cenario": {"type": "STRING", "enum": list(CENARIOS), "description": "Cenário a comparar. Por omissão, hora de ponta com via cortada."}}},
        comparar_configuracoes,
    ),
    Ferramenta("precisao_da_previsao", "Mostra quanto erra o modelo LSTM de previsão de congestionamento a 1, 3 e 5 minutos, contra a previsão simples.", _sem_parametros(), precisao_da_previsao),
    Ferramenta(
        "contagens_da_visao",
        "Contagens de veículos feitas por visão computacional nos vídeos: total, por tipo, fluxo por hora e fila.",
        {"type": "OBJECT", "properties": {"origem": {"type": "STRING", "description": "Nome do processamento (opcional)."}}},
        contagens_da_visao,
    ),
    Ferramenta("procura_por_via", "Vias e entradas com mais procura de tráfego na hora de ponta simulada, e a mistura de tipos de veículo (valores assumidos).", _sem_parametros(), procura_por_via),
    Ferramenta("indicadores_de_risco", "Colisões simuladas e bloqueios por configuração. Não há acidentes reais.", _sem_parametros(), indicadores_de_risco),
    Ferramenta(
        "momentos_de_pico",
        "Em que momentos da simulação há mais veículos parados (horas de ponta simuladas), para uma configuração.",
        {"type": "OBJECT", "properties": {"configuracao": {"type": "STRING", "enum": ["fixo", "local", "local+vias", "coordenado", "coordenado+vias"]}}},
        momentos_de_pico,
    ),
]
POR_NOME = {f.nome: f for f in FERRAMENTAS}


def executar(ligacao: psycopg.Connection, nome: str, args: dict | None) -> dict:
    ferramenta = POR_NOME.get(nome)
    if ferramenta is None:
        return {"erro": f"Ferramenta desconhecida: {nome!r}.", "ferramentas_validas": list(POR_NOME)}
    return ferramenta.executar(ligacao, args or {})
