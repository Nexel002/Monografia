import base64
import json

import httpx
import pytest

from gestao_trafego.assistente import ferramentas, seguranca, voz
from gestao_trafego.assistente.gemini import MAXIMO_DE_VOLTAS, ClienteGemini, ErroDoAssistente
from gestao_trafego.assistente.servico import ServicoDoAssistente
from gestao_trafego.dados import repositorio
from gestao_trafego.dados.ligacao import ligar


# --- dados de teste -------------------------------------------------------------------------------

def execucao(configuracao: str, semente: int, espera: float, incidente=True, escala=1.0, teleportes=0, colisoes=0) -> dict:
    cenario, _, vias = configuracao.partition("+")
    return {
        "cenario": cenario, "semente": semente, "escala": escala, "incidente": incidente, "vias_alternativas": bool(vias),
        "tempo_simulado_s": 4000, "veiculos_concluidos": 2000, "veiculos_nao_concluidos": 0,
        "espera_media_s": espera, "perda_de_tempo_media_s": 1.0, "duracao_viagem_media_s": 300.0,
        "fila_media_veiculos": 40.0, "fila_maxima_veiculos": 100, "velocidade_media_ms": 8.0,
        "teleportes": teleportes, "colisoes": colisoes,
    }


SERIE = [
    {"tempo_s": 100, "veiculos_na_rede": 50, "veiculos_parados": 5, "velocidade_media_ms": 9.0},
    {"tempo_s": 700, "veiculos_na_rede": 120, "veiculos_parados": 60, "velocidade_media_ms": 3.0},
]


@pytest.fixture
def ligacao(url):
    with ligar(url) as con:
        for tabela in ("previsao", "contagem_via", "amostra", "execucao"):
            con.execute(f"DELETE FROM {tabela}")
        con.commit()
        yield con


@pytest.fixture
def com_dados(ligacao):
    for config, espera in (("fixo", 100.0), ("local", 75.0), ("coordenado+vias", 50.0)):
        for semente in (1, 2):
            repositorio.guardar_execucao(ligacao, f"{config}_{semente}", execucao(config, semente, espera, teleportes=3, colisoes=1), SERIE)
    ligacao.commit()
    return ligacao


@pytest.fixture(autouse=True)
def sem_chaves(monkeypatch):
    # Os testes nunca podem usar as chaves reais do backend/.env: nem gastar dinheiro nem enviar dados.
    sem_nada = lambda nome, por_omissao=None: None  # noqa: E731
    for modulo in ("gestao_trafego.comum.configuracao", "gestao_trafego.assistente.voz", "gestao_trafego.assistente.servico"):
        monkeypatch.setattr(f"{modulo}.ler", sem_nada)


# --- ferramentas ----------------------------------------------------------------------------------

def test_comparar_calcula_a_variacao_face_ao_tempo_fixo(com_dados):
    r = ferramentas.executar(com_dados, "comparar_configuracoes", {"cenario": "hora_de_ponta_com_via_cortada"})

    linhas = {l["configuracao"]: l for l in r["linhas"]}
    assert linhas["fixo"]["variacao_face_ao_tempo_fixo_pct"] is None
    assert linhas["local"]["variacao_face_ao_tempo_fixo_pct"] == -25.0
    assert linhas["coordenado+vias"]["variacao_face_ao_tempo_fixo_pct"] == -50.0
    assert "assumida" in r["aviso"]


def test_comparar_com_cenario_invalido_devolve_erro_com_as_opcoes(com_dados):
    r = ferramentas.executar(com_dados, "comparar_configuracoes", {"cenario": "inventado"})

    assert "erro" in r and "hora_normal" in r["cenarios_validos"]


def test_comparar_sem_dados_nao_rebenta(ligacao):
    assert ferramentas.executar(ligacao, "comparar_configuracoes", {})["linhas"] == []


def test_ferramenta_desconhecida_devolve_erro(ligacao):
    assert "erro" in ferramentas.executar(ligacao, "apagar_tudo", {})


def test_precisao_da_previsao_sem_modelo_e_com_modelo(ligacao, tmp_path, monkeypatch):
    monkeypatch.setattr(ferramentas, "CAMINHO_DAS_METRICAS", tmp_path / "nao_existe.json")
    assert ferramentas.executar(ligacao, "precisao_da_previsao", {})["disponivel"] is False

    metricas = tmp_path / "metricas.json"
    metricas.write_text(json.dumps({
        "fila_media_do_teste_veiculos": 53.0,
        "por_horizonte": [{"horizonte_s": 60, "mae_lstm_veiculos": 13.2, "mae_persistencia_veiculos": 21.5, "melhoria_percentual": 38.7}],
        "por_configuracao": {"fixo": [{"horizonte_s": 60, "mae_lstm_veiculos": 11.1, "mae_persistencia_veiculos": 34.9}]},
    }), encoding="utf-8")
    monkeypatch.setattr(ferramentas, "CAMINHO_DAS_METRICAS", metricas)

    r = ferramentas.executar(ligacao, "precisao_da_previsao", {})
    assert r["disponivel"] and r["por_horizonte"][0] == {"horizonte_min": 1, "erro_lstm": 13.2, "erro_persistencia": 21.5, "melhoria_pct": 39}


def test_indicadores_de_risco_soma_por_configuracao_e_avisa_que_nao_ha_acidentes(com_dados):
    r = ferramentas.executar(com_dados, "indicadores_de_risco", {})

    fixo = next(l for l in r["por_configuracao"] if l["configuracao"] == "fixo")
    assert fixo == {"configuracao": "fixo", "colisoes_simuladas": 2, "bloqueios_teleportes": 6, "corridas": 2}
    assert "NÃO há dados de acidentes reais" in r["aviso"]


def test_contagens_da_visao_resume_por_processamento(ligacao):
    janelas = [
        {"via": "v", "inicio_s": 0, "fim_s": 10, "por_tipo": {"carro": 9}, "total": 9, "fluxo_veiculos_por_hora": 3240, "fila_media_veiculos": 1.0},
        {"via": "v", "inicio_s": 10, "fim_s": 20, "por_tipo": {"carro": 11, "camiao": 1}, "total": 12, "fluxo_veiculos_por_hora": 4320, "fila_media_veiculos": 2.0},
    ]
    assert ferramentas.executar(ligacao, "contagens_da_visao", {})["disponivel"] is False
    repositorio.guardar_contagens(ligacao, "visao_x", janelas)
    ligacao.commit()

    p = ferramentas.executar(ligacao, "contagens_da_visao", {})["processamentos"][0]
    assert p["total_contado"] == 21 and p["por_tipo"] == {"carro": 20, "camiao": 1}
    assert p["janela_de_maior_fluxo"]["veiculos"] == 12 and p["fila_media_veiculos"] == 1.5


def test_momentos_de_pico_encontra_o_intervalo_mais_congestionado(com_dados):
    r = ferramentas.executar(com_dados, "momentos_de_pico", {"configuracao": "fixo"})

    assert r["intervalo_de_maior_congestionamento"]["minuto_inicial"] == 10  # tempo_s 700 cai no intervalo 600-1200 s
    assert ferramentas.executar(com_dados, "momentos_de_pico", {"configuracao": "local+vias"})["disponivel"] is False


def test_procura_por_via_avisa_que_os_valores_sao_assumidos(ligacao):
    r = ferramentas.executar(ligacao, "procura_por_via", {})

    assert r["vias_por_procura"][0]["veiculos_por_hora"] >= r["vias_por_procura"][-1]["veiculos_por_hora"]
    assert "ASSUMIDOS" in r["aviso"]


# --- modo de segurança ----------------------------------------------------------------------------

@pytest.mark.parametrize(
    "pergunta, ferramenta",
    [
        ("Como se comparam os resultados?", "comparar_configuracoes"),
        ("Qual a precisão da PREVISÃO?", "precisao_da_previsao"),
        ("Há dados de acidentes?", "indicadores_de_risco"),
        ("Quais as vias mais movimentadas?", "procura_por_via"),
        ("Em que hora de ponta há mais congestionamento?", "momentos_de_pico"),
        ("Quantos veículos contou a câmara?", "contagens_da_visao"),
    ],
)
def test_modo_de_seguranca_escolhe_a_ferramenta_pela_pergunta(com_dados, pergunta, ferramenta):
    _, usadas = seguranca.responder(com_dados, pergunta)

    assert ferramenta in usadas


def test_modo_de_seguranca_com_pergunta_desconhecida_sugere_perguntas(com_dados):
    texto, usadas = seguranca.responder(com_dados, "qual é a capital de França?")

    assert usadas == [] and "Como se comparam" in texto


def test_modo_de_seguranca_diz_os_numeros_reais(com_dados):
    texto, _ = seguranca.responder(com_dados, "compara as configurações")

    assert "100 s" in texto and "-50 %" in texto


# --- cliente do Gemini ----------------------------------------------------------------------------

def resposta_com_texto(texto: str) -> httpx.Response:
    return httpx.Response(200, json={"candidates": [{"content": {"role": "model", "parts": [{"text": texto}]}}]})


def resposta_com_chamada(nome: str, args: dict) -> httpx.Response:
    return httpx.Response(200, json={"candidates": [{"content": {"role": "model", "parts": [{"functionCall": {"name": nome, "args": args}}]}}]})


def cliente_com(manipulador) -> ClienteGemini:
    return ClienteGemini("CHAVE-SECRETA", "modelo-de-teste", httpx.MockTransport(manipulador))


def test_gemini_executa_a_ferramenta_pedida_e_devolve_o_texto_final():
    pedidos = []

    def manipulador(pedido: httpx.Request) -> httpx.Response:
        pedidos.append(pedido)
        return resposta_com_chamada("comparar_configuracoes", {"cenario": "hora_normal"}) if len(pedidos) == 1 else resposta_com_texto("O sistema reduz a espera.")

    chamadas = []
    r = cliente_com(manipulador).conversar("compara", [{"name": "comparar_configuracoes"}], lambda n, a: chamadas.append((n, a)) or {"ok": 1})

    assert r.texto == "O sistema reduz a espera." and r.ferramentas_usadas == ["comparar_configuracoes"]
    assert chamadas == [("comparar_configuracoes", {"cenario": "hora_normal"})]
    segundo = json.loads(pedidos[1].content)["contents"]
    assert segundo[-1]["parts"][0]["functionResponse"]["response"] == {"resultado": {"ok": 1}}


def test_gemini_envia_a_chave_no_cabecalho_e_nunca_no_url():
    vistos = []

    def manipulador(pedido: httpx.Request) -> httpx.Response:
        vistos.append(pedido)
        return resposta_com_texto("olá")

    cliente_com(manipulador).conversar("olá", [], lambda n, a: {})

    assert vistos[0].headers["x-goog-api-key"] == "CHAVE-SECRETA"
    assert "CHAVE-SECRETA" not in str(vistos[0].url)


def test_gemini_com_erro_http_da_erro_legivel_sem_expor_a_chave():
    cliente = cliente_com(lambda p: httpx.Response(403, json={"error": {"message": "chave inválida"}}))

    with pytest.raises(ErroDoAssistente) as erro:
        cliente.conversar("olá", [], lambda n, a: {})

    assert "403" in str(erro.value) and "chave inválida" in str(erro.value) and "CHAVE-SECRETA" not in str(erro.value)


def test_gemini_com_falha_de_rede_da_erro_legivel():
    def manipulador(pedido):
        raise httpx.ConnectError("sem rede")

    with pytest.raises(ErroDoAssistente, match="ConnectError"):
        cliente_com(manipulador).conversar("olá", [], lambda n, a: {})


def test_gemini_com_resposta_vazia_da_erro():
    cliente = cliente_com(lambda p: httpx.Response(200, json={"candidates": []}))

    with pytest.raises(ErroDoAssistente, match="vazia"):
        cliente.conversar("olá", [], lambda n, a: {})


def test_gemini_que_pede_ferramentas_sem_parar_e_interrompido():
    chamadas = []
    cliente = cliente_com(lambda p: resposta_com_chamada("comparar_configuracoes", {}))

    with pytest.raises(ErroDoAssistente, match="demasiadas vezes"):
        cliente.conversar("olá", [], lambda n, a: chamadas.append(n) or {})

    assert len(chamadas) == MAXIMO_DE_VOLTAS


# --- serviço --------------------------------------------------------------------------------------

def test_servico_sem_gemini_configurado_responde_em_modo_de_seguranca(com_dados):
    r = ServicoDoAssistente().perguntar(com_dados, "compara os resultados")

    assert r.modo == "seguranca" and "não está configurado" in r.aviso and r.ferramentas_usadas == ["comparar_configuracoes"]


def test_servico_com_gemini_a_funcionar_usa_o_gemini(com_dados):
    servico = ServicoDoAssistente(cliente_com(lambda p: resposta_com_texto("resposta do modelo")))

    r = servico.perguntar(com_dados, "olá")

    assert r.modo == "gemini" and r.texto == "resposta do modelo" and r.aviso is None


def test_servico_cai_para_o_modo_de_seguranca_quando_o_gemini_falha(com_dados):
    servico = ServicoDoAssistente(cliente_com(lambda p: httpx.Response(500, json={})))

    r = servico.perguntar(com_dados, "compara os resultados")

    assert r.modo == "seguranca" and "500" in r.aviso and "50 s" in r.texto


def test_servico_envia_o_historico_convertido_e_limitado(com_dados):
    corpos = []

    def manipulador(pedido):
        corpos.append(json.loads(pedido.content))
        return resposta_com_texto("ok")

    historico = [{"papel": "utilizador" if i % 2 == 0 else "assistente", "texto": f"mensagem {i}"} for i in range(30)]
    ServicoDoAssistente(cliente_com(manipulador)).perguntar(com_dados, "e agora?", historico)

    conteudos = corpos[0]["contents"]
    assert len(conteudos) == 11  # as 10 últimas mensagens + a pergunta
    assert conteudos[0]["role"] in ("user", "model") and conteudos[-1]["parts"][0]["text"] == "e agora?"


def test_servico_gera_o_relatorio_pelo_gemini_ou_pelo_modo_de_seguranca(com_dados):
    assert ServicoDoAssistente(cliente_com(lambda p: resposta_com_texto("relatório"))).relatorio(com_dados).modo == "gemini"

    r = ServicoDoAssistente().relatorio(com_dados)
    assert r.modo == "seguranca" and "Comparação das configurações" in r.texto and len(r.ferramentas_usadas) == 4


# --- voz ------------------------------------------------------------------------------------------

def test_preparar_texto_tira_o_markdown_e_corta_no_ultimo_ponto():
    assert voz.preparar_texto("**Resultado**\n- espera de `50 s`") == "Resultado espera de 50 s"
    longo = ("Uma frase curta. " * 200).strip()
    cortado = voz.preparar_texto(longo)
    assert len(cortado) <= voz.LIMITE_DE_CARACTERES and cortado.endswith(".")


def test_sintetizar_usa_o_google_quando_ha_chave(monkeypatch):
    monkeypatch.setattr(voz, "ler", lambda nome, por_omissao=None: "chave" if nome == "GOOGLE_TTS_API_KEY" else None)
    audio = base64.b64encode(b"MP3-GOOGLE").decode()

    r = voz.sintetizar("olá", httpx.MockTransport(lambda p: httpx.Response(200, json={"audioContent": audio})))

    assert r == (b"MP3-GOOGLE", "audio/mpeg")


def test_sintetizar_passa_ao_elevenlabs_quando_o_google_falha(monkeypatch):
    valores = {"GOOGLE_TTS_API_KEY": "g", "ELEVEN_LABS_API_KEY": "e", "ELEVEN_LABS_VOICE_ID": "voz1"}
    monkeypatch.setattr(voz, "ler", lambda nome, por_omissao=None: valores.get(nome))

    def manipulador(pedido: httpx.Request) -> httpx.Response:
        return httpx.Response(500) if "googleapis" in str(pedido.url) else httpx.Response(200, content=b"MP3-ELEVEN")

    assert voz.sintetizar("olá", httpx.MockTransport(manipulador)) == (b"MP3-ELEVEN", "audio/mpeg")


def test_sintetizar_sem_chaves_devolve_none_para_o_browser_falar():
    assert voz.sintetizar("olá") is None
    assert voz.sintetizar("   ") is None
