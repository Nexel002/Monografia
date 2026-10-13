import pytest
from fastapi.testclient import TestClient

from gestao_trafego.api.app import criar_app
from gestao_trafego.dados import repositorio
from gestao_trafego.dados.ligacao import ligar


@pytest.fixture
def cliente(url, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", url)  # o servidor de testes, não o embebido do projecto
    with ligar(url) as con:
        for tabela in ("previsao", "contagem_via", "amostra", "execucao"):
            con.execute(f"DELETE FROM {tabela}")
        con.commit()
    with TestClient(criar_app()) as c:
        yield c


def execucao(cenario="fixo", semente=1, espera=100.0, vias=False) -> dict:
    return {
        "cenario": cenario, "semente": semente, "escala": 1.0, "incidente": True, "vias_alternativas": vias,
        "tempo_simulado_s": 4000, "veiculos_concluidos": 2000, "veiculos_nao_concluidos": 0,
        "espera_media_s": espera, "perda_de_tempo_media_s": 1.0, "duracao_viagem_media_s": 300.0,
        "fila_media_veiculos": 40.0, "fila_maxima_veiculos": 100, "velocidade_media_ms": 8.0, "teleportes": 0, "colisoes": 0,
    }


SERIE = [{"tempo_s": 10, "veiculos_na_rede": 5, "veiculos_parados": 1, "velocidade_media_ms": 9.0}]


def test_saude(cliente):
    assert cliente.get("/api/saude").json() == {"estado": "ok"}


def test_rede_devolve_ruas_e_semaforos_com_os_sinais_posicionados(cliente):
    rede = cliente.get("/api/rede").json()

    assert len(rede["ruas"]) > 1000
    assert len(rede["semaforos"]) == 13
    assert all(len(s["sinais"]) > 0 for s in rede["semaforos"])
    assert rede["limites"]["x_max"] > rede["limites"]["x_min"]


def test_execucoes_serie_e_comparacao(cliente, url):
    with ligar(url) as con:
        id_ = repositorio.guardar_execucao(con, "fixo_s1", execucao("fixo", 1, 100), SERIE)
        repositorio.guardar_execucao(con, "local_s1", execucao("local", 1, 80), SERIE)
        con.commit()

    assert [e["nome"] for e in cliente.get("/api/execucoes").json()] == ["fixo_s1", "local_s1"]
    assert cliente.get(f"/api/execucoes/{id_}/serie").json()[0]["veiculos_parados"] == 1
    tabela = {l["configuracao"]: l for l in cliente.get("/api/comparacao?incidente=true").json()}
    assert tabela["fixo"]["espera_media_s"] == 100 and tabela["local"]["espera_media_s"] == 80


def test_serie_de_execucao_inexistente_da_404(cliente):
    assert cliente.get("/api/execucoes/999999/serie").status_code == 404


def test_previsao_sem_dados_da_404_e_com_dados_devolve_os_pontos(cliente, url):
    with ligar(url) as con:
        id_ = repositorio.guardar_execucao(con, "x", execucao(), SERIE)
        repositorio.guardar_previsoes(con, "lstm", id_, 60, [(70, 3.0, 4.0)])
        con.commit()

    assert cliente.get(f"/api/previsao/{id_}?horizonte_s=180").status_code == 404
    assert cliente.get(f"/api/previsao/{id_}?horizonte_s=60").json() == [{"tempo_s": 70, "previsto": 3.0, "real": 4.0}]


@pytest.mark.parametrize("nome", ["visao_nao_existe", "abc", "..", "visao_..%2F..%2Fsegredo"])
def test_visao_rejeita_nomes_invalidos_ou_inexistentes(cliente, nome):
    assert cliente.get(f"/api/visao/{nome}/resumo").status_code == 404
    assert cliente.get(f"/api/visao/{nome}/video").status_code == 404


def test_visao_lista_as_pastas_sem_rebentar(cliente):
    resposta = cliente.get("/api/visao")

    assert resposta.status_code == 200 and isinstance(resposta.json(), list)


def test_websocket_com_configuracao_invalida_responde_erro(cliente):
    with cliente.websocket_connect("/ws/simulacao?esquerda=inventado") as ws:
        mensagem = ws.receive_json()

    assert mensagem["tipo"] == "erro" and "inventado" in mensagem["mensagem"]


@pytest.mark.slow
def test_websocket_envia_o_estado_das_duas_simulacoes_e_termina(cliente):
    with cliente.websocket_connect("/ws/simulacao?velocidade=60&limite=40&esquerda=fixo&direita=local&incidente=false") as ws:
        assert ws.receive_json()["tipo"] == "inicio"
        mensagem = ws.receive_json()
        while mensagem["tipo"] == "estado" and mensagem["t"] < 40:
            assert set(mensagem) == {"tipo", "t", "esquerda", "direita"}
            for lado in ("esquerda", "direita"):
                assert set(mensagem[lado]) == {"v", "s", "k"}
                assert set(mensagem[lado]["k"]) >= {"na_rede", "parados", "chegados", "espera_media_s"}
            mensagem = ws.receive_json()
        assert mensagem["tipo"] in ("estado", "fim")
