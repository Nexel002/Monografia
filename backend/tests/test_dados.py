import json

import pytest

pgserver = pytest.importorskip("pgserver")

from gestao_trafego.dados import repositorio  # noqa: E402
from gestao_trafego.dados.importar import importar  # noqa: E402
from gestao_trafego.dados.ligacao import ligar  # noqa: E402


@pytest.fixture
def ligacao(url):
    with ligar(url) as con:
        for tabela in ("previsao", "contagem_via", "amostra", "execucao"):
            con.execute(f"DELETE FROM {tabela}")
        con.commit()  # sem isto os testes que abrem uma 2.ª ligação (importar) bloqueiam nesta
        yield con


def resumo(cenario="fixo", semente=1, espera=100.0, vias=False, incidente=True, escala=1.0) -> dict:
    return {
        "cenario": cenario, "semente": semente, "escala": escala, "incidente": incidente, "vias_alternativas": vias,
        "tempo_simulado_s": 4000, "veiculos_concluidos": 2000, "veiculos_nao_concluidos": 0,
        "espera_media_s": espera, "perda_de_tempo_media_s": espera * 1.4, "duracao_viagem_media_s": 300.0,
        "fila_media_veiculos": 40.0, "fila_maxima_veiculos": 100, "velocidade_media_ms": 8.0,
        "teleportes": 2, "colisoes": 0,
    }


SERIE = [
    {"tempo_s": 10, "veiculos_na_rede": 5, "veiculos_parados": 1, "velocidade_media_ms": 9.0},
    {"tempo_s": 20, "veiculos_na_rede": 9, "veiculos_parados": 3, "velocidade_media_ms": 7.5},
]


def test_guardar_e_ler_uma_execucao_com_a_sua_serie(ligacao):
    id_ = repositorio.guardar_execucao(ligacao, "fixo_s1", resumo(), SERIE)

    execucoes = repositorio.listar_execucoes(ligacao)
    assert [e["nome"] for e in execucoes] == ["fixo_s1"]
    assert execucoes[0]["configuracao"] == "fixo"
    assert [a["veiculos_parados"] for a in repositorio.serie_da_execucao(ligacao, id_)] == [1, 3]


def test_configuracao_inclui_as_vias_alternativas(ligacao):
    repositorio.guardar_execucao(ligacao, "x", resumo("local", vias=True), SERIE)

    assert repositorio.listar_execucoes(ligacao)[0]["configuracao"] == "local+vias"


def test_guardar_de_novo_substitui_em_vez_de_duplicar(ligacao):
    repositorio.guardar_execucao(ligacao, "fixo_s1", resumo(espera=100), SERIE)
    repositorio.guardar_execucao(ligacao, "fixo_s1", resumo(espera=50), SERIE[:1])

    execucoes = repositorio.listar_execucoes(ligacao)
    assert len(execucoes) == 1 and execucoes[0]["espera_media_s"] == 50
    assert len(repositorio.serie_da_execucao(ligacao, execucoes[0]["id"])) == 1


def test_comparar_so_usa_as_sementes_comuns_a_todas_as_configuracoes(ligacao):
    repositorio.guardar_execucao(ligacao, "f1", resumo("fixo", 1, 100), SERIE)
    repositorio.guardar_execucao(ligacao, "f2", resumo("fixo", 2, 200), SERIE)
    repositorio.guardar_execucao(ligacao, "l2", resumo("local", 2, 80), SERIE)  # o local só tem a semente 2

    tabela = {linha["configuracao"]: linha for linha in repositorio.comparar_configuracoes(ligacao, True)}

    # Se a semente 1 contasse, o fixo teria média 150 e pareceria pior do que é na semente 2.
    assert tabela["fixo"]["espera_media_s"] == 200 and tabela["fixo"]["sementes"] == 1
    assert tabela["local"]["espera_media_s"] == 80


def test_comparar_separa_incidente_de_hora_normal(ligacao):
    repositorio.guardar_execucao(ligacao, "a", resumo("fixo", 1, 100, incidente=True), SERIE)
    repositorio.guardar_execucao(ligacao, "b", resumo("fixo", 1, 40, incidente=False), SERIE)

    assert repositorio.comparar_configuracoes(ligacao, True)[0]["espera_media_s"] == 100
    assert repositorio.comparar_configuracoes(ligacao, False)[0]["espera_media_s"] == 40


def test_comparar_devolve_as_configuracoes_pela_ordem_do_estudo(ligacao):
    for i, cfg in enumerate(["coordenado+vias", "fixo", "local"]):
        cenario, _, vias = cfg.partition("+")
        repositorio.guardar_execucao(ligacao, cfg, resumo(cenario, 1, 100 - i, vias=bool(vias)), SERIE)

    assert [l["configuracao"] for l in repositorio.comparar_configuracoes(ligacao, True)] == ["fixo", "local", "coordenado+vias"]


JANELAS = [
    {"via": "v", "inicio_s": 0, "fim_s": 10, "por_tipo": {"carro": 9}, "total": 9, "fluxo_veiculos_por_hora": 3240, "fila_media_veiculos": 1.5},
    {"via": "v", "inicio_s": 10, "fim_s": 20, "por_tipo": {"carro": 8, "camiao": 1}, "total": 9, "fluxo_veiculos_por_hora": 3240, "fila_media_veiculos": 2.0},
]


def test_guardar_contagens_e_ler_por_origem(ligacao):
    repositorio.guardar_contagens(ligacao, "video_a", JANELAS)
    repositorio.guardar_contagens(ligacao, "video_b", JANELAS[:1])
    repositorio.guardar_contagens(ligacao, "video_a", JANELAS)  # repetir não duplica

    assert len(repositorio.listar_contagens(ligacao, "video_a")) == 2
    assert len(repositorio.listar_contagens(ligacao)) == 3
    assert repositorio.listar_contagens(ligacao, "video_a")[1]["por_tipo"] == {"carro": 8, "camiao": 1}


def test_previsoes_guardam_se_por_execucao_e_horizonte(ligacao):
    id_ = repositorio.guardar_execucao(ligacao, "x", resumo(), SERIE)

    repositorio.guardar_previsoes(ligacao, "lstm", id_, 60, [(70, 3.2, 3.0), (80, 4.0, 5.0)])
    repositorio.guardar_previsoes(ligacao, "lstm", id_, 60, [(70, 9.0, 3.0)])  # substitui

    assert repositorio.listar_previsoes(ligacao, id_, 60) == [{"tempo_s": 70, "previsto": 9.0, "real": 3.0}]
    assert repositorio.listar_previsoes(ligacao, id_, 180) == []


def test_importar_le_pastas_de_resultados_e_ignora_ensaios_curtos(tmp_path, url, ligacao):
    def pasta(nome, **kw):
        p = tmp_path / nome
        p.mkdir()
        (p / "resumo.json").write_text(json.dumps(resumo(**kw)), encoding="utf-8")
        (p / "serie.csv").write_text(
            "tempo_s,veiculos_na_rede,veiculos_parados,velocidade_media_ms\n10,5,1,9.0\n20,9,3,7.5\n", encoding="utf-8"
        )

    pasta("fixo_s1_x1.0_incidente", semente=1)
    pasta("fixo_s2_x1.0_lim1800", semente=2)
    visao = tmp_path / "visao_x"
    visao.mkdir()
    (visao / "contagem.json").write_text(json.dumps({"janelas": JANELAS}), encoding="utf-8")
    sem_janelas = tmp_path / "visao_antigo"
    sem_janelas.mkdir()
    (sem_janelas / "contagem.json").write_text(json.dumps({"total": 54}), encoding="utf-8")

    resultado = importar(tmp_path, url)

    assert resultado == {"execucoes": 1, "janelas_de_contagem": 2, "ignoradas": 2}
    assert importar(tmp_path, url) == resultado  # idempotente
    assert [e["nome"] for e in repositorio.listar_execucoes(ligacao)] == ["fixo_s1_x1.0_incidente"]
