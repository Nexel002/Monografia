import time
from pathlib import Path

import cv2
import numpy as np
import pytest

from gestao_trafego.visao.contagem import Caixa, Deteccao
from gestao_trafego.visao.sessao_ao_vivo import SessaoDeVisaoAoVivo

LARGURA, ALTURA, FPS, FOTOGRAMAS = 160, 90, 30, 60  # 2 s de vídeo


@pytest.fixture(scope="module")
def video(tmp_path_factory) -> Path:
    caminho = tmp_path_factory.mktemp("video") / "teste.mp4"
    escritor = cv2.VideoWriter(str(caminho), cv2.VideoWriter_fourcc(*"mp4v"), FPS, (LARGURA, ALTURA))
    for i in range(FOTOGRAMAS):
        escritor.write(np.full((ALTURA, LARGURA, 3), i * 4 % 255, dtype=np.uint8))
    escritor.release()
    return caminho


class SeguidorFalso:
    """Um veículo que desce 12 px por análise: cruza a linha a meio da imagem uma só vez."""

    def __init__(self):
        self.chamadas = 0

    def seguir(self, imagem) -> list[Deteccao]:
        self.chamadas += 1
        base = 10 + 12 * self.chamadas
        return [Deteccao(1, Caixa(60, base - 20, 100, base), "carro")]


def esperar(condicao, limite_s=8.0) -> bool:
    fim = time.perf_counter() + limite_s
    while time.perf_counter() < fim:
        if condicao():
            return True
        time.sleep(0.02)
    return False


def correr(video, **kwargs):
    mensagens: list[dict] = []
    sessao = SessaoDeVisaoAoVivo(video, mensagens.append, linha=(0, 0.5, 1, 0.5), seguidor=SeguidorFalso(), **kwargs)
    info = sessao.abrir()
    return sessao, mensagens, info


def test_abrir_devolve_a_informacao_para_o_cliente(video):
    sessao, _, info = correr(video)
    try:
        assert (info["largura"], info["altura"]) == (LARGURA, ALTURA)
        assert info["fps"] == FPS and info["duracao_s"] == pytest.approx(2.0, abs=0.1)
        assert info["linha"] == [0, ALTURA * 0.5, LARGURA, ALTURA * 0.5]
    finally:
        sessao.parar()


def test_corre_o_video_conta_uma_vez_e_termina_com_o_resumo(video):
    sessao, mensagens, _ = correr(video)
    try:
        sessao.iniciar(0)
        assert esperar(lambda: any(m["tipo"] == "fim" for m in mensagens))
    finally:
        sessao.parar()

    fim = next(m for m in mensagens if m["tipo"] == "fim")
    assert fim["resumo"]["total"] == 1 and fim["resumo"]["por_tipo"] == {"carro": 1}
    assert fim["resumo"]["analises"] > 5
    deteccoes = [m for m in mensagens if m["tipo"] == "deteccoes"]
    assert deteccoes, "não houve nenhuma mensagem de deteções"
    id_, x1, y1, x2, y2, tipo, contado = deteccoes[0]["veiculos"][0]
    assert (id_, tipo) == (1, "carro") and x2 > x1 and y2 > y1 and contado in (0, 1)
    assert deteccoes[0]["t_video"] == pytest.approx(deteccoes[0]["indice"] / FPS)
    # o veículo passa de «por contar» (0) a «contado» (1) e fica contado
    estados = [m["veiculos"][0][6] for m in deteccoes if m["veiculos"]]
    assert estados[0] == 0 and estados[-1] == 1 and estados == sorted(estados)


def test_pausar_para_de_ler_e_retomar_continua(video):
    sessao, mensagens, _ = correr(video)
    try:
        sessao.iniciar(0)
        assert esperar(lambda: sessao.fotogramas_lidos > 3)
        sessao.pausar()
        time.sleep(0.15)
        lidos = sessao.fotogramas_lidos
        time.sleep(0.3)
        assert sessao.fotogramas_lidos == lidos  # parado
        sessao.retomar(lidos / FPS)
        assert esperar(lambda: sessao.fotogramas_lidos > lidos)
    finally:
        sessao.parar()


def test_limite_de_segundos_termina_o_vídeo_mais_cedo(video):
    sessao, mensagens, info = correr(video, max_segundos=0.5)
    try:
        assert info["ate_s"] == 0.5
        sessao.iniciar(0)
        assert esperar(lambda: any(m["tipo"] == "fim" for m in mensagens))
    finally:
        sessao.parar()
    assert sessao.fotogramas_lidos <= int(0.5 * FPS) + 1


def test_video_inexistente_falha_alto(tmp_path):
    with pytest.raises(FileNotFoundError):
        SessaoDeVisaoAoVivo(tmp_path / "nao_existe.mp4", lambda m: None, seguidor=SeguidorFalso()).abrir()


def test_erro_do_analisador_chega_ao_cliente(video):
    class Avariado:
        def seguir(self, imagem):
            raise RuntimeError("modelo avariado")

    mensagens: list[dict] = []
    sessao = SessaoDeVisaoAoVivo(video, mensagens.append, seguidor=Avariado())
    sessao.abrir()
    try:
        sessao.iniciar(0)
        assert esperar(lambda: any(m["tipo"] == "erro" for m in mensagens))
    finally:
        sessao.parar()
    assert "modelo avariado" in next(m for m in mensagens if m["tipo"] == "erro")["mensagem"]
