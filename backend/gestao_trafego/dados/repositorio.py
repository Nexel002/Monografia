"""Leituras e escritas na base de dados. Cada função recebe a ligação: quem chama decide a transacção."""

import json

import psycopg

CONFIGURACOES = ("fixo", "local", "local+vias", "coordenado", "coordenado+vias")

_KPIS = (
    "tempo_simulado_s", "veiculos_concluidos", "veiculos_nao_concluidos", "espera_media_s",
    "perda_de_tempo_media_s", "duracao_viagem_media_s", "fila_media_veiculos", "fila_maxima_veiculos",
    "velocidade_media_ms", "teleportes", "colisoes",
)


def nome_da_configuracao(cenario: str, vias_alternativas: bool) -> str:
    return f"{cenario}+vias" if vias_alternativas else cenario


def guardar_execucao(
    ligacao: psycopg.Connection, nome: str, resumo: dict, serie: list[dict]
) -> int:
    """Insere (ou substitui) uma execução e a sua série temporal. Devolve o id."""
    vias = bool(resumo.get("vias_alternativas", False))
    colunas = ["nome", "configuracao", "cenario", "semente", "escala", "incidente", "vias_alternativas", *_KPIS]
    valores = [
        nome, nome_da_configuracao(resumo["cenario"], vias), resumo["cenario"], resumo["semente"],
        resumo["escala"], bool(resumo.get("incidente", False)), vias, *(resumo[k] for k in _KPIS),
    ]
    # Substituir (e não ignorar) porque uma execução repetida com o mesmo nome é uma versão mais nova.
    ligacao.execute("DELETE FROM execucao WHERE nome = %s", (nome,))
    id_ = ligacao.execute(
        f"INSERT INTO execucao ({', '.join(colunas)}) VALUES ({', '.join(['%s'] * len(colunas))}) RETURNING id",
        valores,
    ).fetchone()["id"]
    with ligacao.cursor() as cursor:
        cursor.executemany(
            "INSERT INTO amostra (execucao_id, tempo_s, veiculos_na_rede, veiculos_parados, velocidade_media_ms) "
            "VALUES (%s, %s, %s, %s, %s)",
            [(id_, a["tempo_s"], a["veiculos_na_rede"], a["veiculos_parados"], a["velocidade_media_ms"]) for a in serie],
        )
    return id_


def listar_execucoes(ligacao: psycopg.Connection) -> list[dict]:
    return ligacao.execute(
        "SELECT id, nome, configuracao, semente, escala, incidente, espera_media_s, fila_media_veiculos, "
        "velocidade_media_ms, teleportes, veiculos_concluidos FROM execucao ORDER BY configuracao, semente"
    ).fetchall()


def serie_da_execucao(ligacao: psycopg.Connection, execucao_id: int) -> list[dict]:
    return ligacao.execute(
        "SELECT tempo_s, veiculos_na_rede, veiculos_parados, velocidade_media_ms FROM amostra "
        "WHERE execucao_id = %s ORDER BY tempo_s",
        (execucao_id,),
    ).fetchall()


def comparar_configuracoes(ligacao: psycopg.Connection, incidente: bool, escala: float = 1.0) -> list[dict]:
    """Média e dispersão dos KPIs por configuração, só sobre as sementes comuns a todas.

    Comparar médias de conjuntos de sementes diferentes mede o acaso das sementes; por isso só entram
    as sementes que existem em todas as configurações presentes.
    """
    return ligacao.execute(
        """
        WITH base AS (
            SELECT * FROM execucao WHERE incidente = %(incidente)s AND escala = %(escala)s
        ), comuns AS (
            SELECT semente FROM base GROUP BY semente
            HAVING COUNT(DISTINCT configuracao) = (SELECT COUNT(DISTINCT configuracao) FROM base)
        )
        SELECT b.configuracao,
               COUNT(*) AS sementes,
               AVG(b.espera_media_s) AS espera_media_s,
               STDDEV_POP(b.espera_media_s) AS espera_desvio_s,
               AVG(b.fila_media_veiculos) AS fila_media_veiculos,
               AVG(b.velocidade_media_ms) AS velocidade_media_ms,
               SUM(b.teleportes) AS teleportes
        FROM base b JOIN comuns c USING (semente)
        GROUP BY b.configuracao
        ORDER BY array_position(%(ordem)s::text[], b.configuracao)
        """,
        {"incidente": incidente, "escala": escala, "ordem": list(CONFIGURACOES)},
    ).fetchall()


def guardar_contagens(ligacao: psycopg.Connection, origem: str, janelas: list[dict]) -> None:
    ligacao.execute("DELETE FROM contagem_via WHERE origem = %s", (origem,))
    with ligacao.cursor() as cursor:
        cursor.executemany(
            "INSERT INTO contagem_via (origem, via, inicio_s, fim_s, por_tipo, total, fluxo_veiculos_por_hora, fila_media_veiculos) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
            [
                (origem, j["via"], j["inicio_s"], j["fim_s"], json.dumps(j["por_tipo"]), j["total"],
                 j["fluxo_veiculos_por_hora"], j["fila_media_veiculos"])
                for j in janelas
            ],
        )


def listar_contagens(ligacao: psycopg.Connection, origem: str | None = None) -> list[dict]:
    return ligacao.execute(
        "SELECT origem, via, inicio_s, fim_s, por_tipo, total, fluxo_veiculos_por_hora, fila_media_veiculos "
        "FROM contagem_via WHERE (%s::text IS NULL OR origem = %s) ORDER BY origem, inicio_s",
        (origem, origem),
    ).fetchall()


def guardar_previsoes(
    ligacao: psycopg.Connection, modelo: str, execucao_id: int, horizonte_s: int, pontos: list[tuple[int, float, float]]
) -> None:
    """`pontos`: (tempo_s a que a previsão diz respeito, previsto, real)."""
    ligacao.execute(
        "DELETE FROM previsao WHERE modelo = %s AND execucao_id = %s AND horizonte_s = %s",
        (modelo, execucao_id, horizonte_s),
    )
    with ligacao.cursor() as cursor:
        cursor.executemany(
            "INSERT INTO previsao (modelo, execucao_id, horizonte_s, tempo_s, previsto, real) VALUES (%s, %s, %s, %s, %s, %s)",
            [(modelo, execucao_id, horizonte_s, t, p, r) for t, p, r in pontos],
        )


def listar_previsoes(ligacao: psycopg.Connection, execucao_id: int, horizonte_s: int) -> list[dict]:
    return ligacao.execute(
        "SELECT tempo_s, previsto, real FROM previsao WHERE execucao_id = %s AND horizonte_s = %s ORDER BY tempo_s",
        (execucao_id, horizonte_s),
    ).fetchall()
