"""Modo de segurança: respostas sem modelo de linguagem, calculadas a partir das mesmas ferramentas.

Serve para a defesa não depender da internet nem da chave: se o Gemini falhar, o assistente continua a
responder às perguntas mais prováveis, com os números reais e os mesmos avisos. As respostas são
modelos de texto preenchidos com os resultados; não há aqui nada de «inteligente», e a interface diz
que está neste modo.
"""

import unicodedata

import psycopg

from gestao_trafego.assistente import ferramentas

ROTULO = {
    "fixo": "tempo fixo (como hoje)",
    "local": "adaptativo local",
    "local+vias": "local com vias alternativas",
    "coordenado": "coordenado",
    "coordenado+vias": "coordenado com vias alternativas",
}

PERGUNTAS_SUGERIDAS = [
    "Como se comparam as configurações de semáforos?",
    "Qual a precisão da previsão de congestionamento?",
    "Quais as vias com mais procura?",
    "Em que momentos há mais congestionamento?",
    "Que tipos de veículo predominam?",
    "Há dados de acidentes?",
]


def _normalizar(texto: str) -> str:
    sem_acentos = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return sem_acentos.lower()


def _comparacao(r: dict) -> str:
    if not r.get("linhas"):
        return "Ainda não há simulações importadas para esse cenário."
    linhas = []
    for l in r["linhas"]:
        variacao = "" if l["variacao_face_ao_tempo_fixo_pct"] is None else f" ({l['variacao_face_ao_tempo_fixo_pct']:+.0f} % face ao tempo fixo)"
        linhas.append(f"- {ROTULO.get(l['configuracao'], l['configuracao'])}: espera média de {l['espera_media_s']:.0f} s{variacao}")
    return f"Espera média por veículo no cenário «{r['cenario'].replace('_', ' ')}»:\n" + "\n".join(linhas) + f"\n\n{r['aviso']}"


def _previsao(r: dict) -> str:
    if not r.get("disponivel"):
        return r.get("motivo", "A previsão não está disponível.")
    linhas = [f"- a {h['horizonte_min']} min: erro do LSTM {h['erro_lstm']} contra {h['erro_persistencia']} da previsão simples ({h['melhoria_pct']:+d} %)" for h in r["por_horizonte"]]
    return "Erro da previsão de veículos parados:\n" + "\n".join(linhas) + f"\n\n{r['aviso']}"


def _procura(r: dict) -> str:
    topo = r["vias_por_procura"][:4]
    linhas = [f"- {v['descricao']}: {v['veiculos_por_hora']} veículos/hora" for v in topo]
    mistura = ", ".join(f"{k} {v}" for k, v in r["mistura_de_veiculos"].items())
    return "Entradas com mais procura na hora de ponta simulada:\n" + "\n".join(linhas) + f"\n\nMistura de veículos: {mistura}.\n{r['aviso']}"


def _picos(r: dict) -> str:
    if not r.get("disponivel", True):
        return r.get("motivo", "Sem dados.")
    p = r["intervalo_de_maior_congestionamento"]
    return (
        f"Na configuração «{ROTULO.get(r['configuracao'], r['configuracao'])}», o maior congestionamento da simulação está nos minutos "
        f"{p['minuto_inicial']} a {p['minuto_inicial'] + 10}, com cerca de {p['veiculos_parados_medio']:.0f} veículos parados em média.\n\n{r['aviso']}"
    )


def _risco(r: dict) -> str:
    linhas = [f"- {ROTULO.get(l['configuracao'], l['configuracao'])}: {l['colisoes_simuladas']} colisões simuladas, {l['bloqueios_teleportes']} bloqueios" for l in r["por_configuracao"]]
    return "Não há dados de acidentes reais. " + r["aviso"] + "\n" + "\n".join(linhas)


def _contagens(r: dict) -> str:
    if not r.get("processamentos"):
        return r.get("motivo", "Sem contagens importadas.")
    linhas = [f"- {p['processamento']}: {p['total_contado']} veículos ({', '.join(f'{k} {v}' for k, v in p['por_tipo'].items())})" for p in r["processamentos"]]
    return "Contagens por visão computacional:\n" + "\n".join(linhas) + f"\n\n{r['aviso']}"


def responder(ligacao: psycopg.Connection, pergunta: str) -> tuple[str, list[str]]:
    """Devolve (texto, ferramentas usadas). Escolhe a ferramenta por palavras-chave da pergunta."""
    q = _normalizar(pergunta)
    usadas: list[str] = []

    def usar(nome: str, args: dict | None = None) -> dict:
        usadas.append(nome)
        return ferramentas.executar(ligacao, nome, args)

    if any(p in q for p in ("acident", "risco", "colis", "sinistr", "seguranca")):
        return _risco(usar("indicadores_de_risco")), usadas
    if any(p in q for p in ("previs", "lstm", "prever")):
        return _previsao(usar("precisao_da_previsao")), usadas
    if any(p in q for p in ("tipo", "predomin", "chapa", "camiao", "carro", "mota", "autocarro")):
        textos = [_procura(usar("procura_por_via")), _contagens(usar("contagens_da_visao"))]
        return "\n\n".join(textos), usadas
    if any(p in q for p in ("pico", "hora", "momento", "congestion")):
        return _picos(usar("momentos_de_pico", {"configuracao": "fixo"})), usadas
    if any(p in q for p in ("via", "movimentad", "procura", "entrada")):
        return _procura(usar("procura_por_via")), usadas
    if any(p in q for p in ("contag", "video", "visao", "camara")):
        return _contagens(usar("contagens_da_visao")), usadas
    if any(p in q for p in ("compar", "resultado", "melhor", "espera", "fixo", "sistema", "semaforo", "configur", "ganho", "reduz")):
        return _comparacao(usar("comparar_configuracoes")), usadas
    return (
        "Neste momento estou sem ligação ao modelo de linguagem e só sei responder a perguntas como:\n" + "\n".join(f"- {p}" for p in PERGUNTAS_SUGERIDAS),
        usadas,
    )


def relatorio(ligacao: psycopg.Connection) -> tuple[str, list[str]]:
    """Relatório de resultados sem modelo: as secções principais, uma a seguir à outra."""
    usadas: list[str] = []
    secoes = []
    for titulo, nome, args, formatar in (
        ("Comparação das configurações (hora de ponta com via cortada)", "comparar_configuracoes", {}, _comparacao),
        ("Previsão de congestionamento", "precisao_da_previsao", {}, _previsao),
        ("Contagem por visão computacional", "contagens_da_visao", {}, _contagens),
        ("Indicadores de risco", "indicadores_de_risco", {}, _risco),
    ):
        usadas.append(nome)
        secoes.append(f"{titulo}\n{formatar(ferramentas.executar(ligacao, nome, args))}")
    return "\n\n".join(secoes), usadas
