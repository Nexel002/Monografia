import os
from pathlib import Path

import cv2
import numpy as np
import pytest

from gestao_trafego.visao.video import exigir_webm, garantir_webm

FOTOGRAMAS = 30


def _escrever(caminho: Path, largura: int, altura: int, fourcc: str = "mp4v") -> Path:
    escritor = cv2.VideoWriter(str(caminho), cv2.VideoWriter_fourcc(*fourcc), 30, (largura, altura))
    for i in range(FOTOGRAMAS):
        escritor.write(np.full((altura, largura, 3), i * 8 % 255, dtype=np.uint8))
    escritor.release()
    return caminho


def test_converte_para_webm_mantendo_os_fotogramas(tmp_path):
    origem = _escrever(tmp_path / "entrada.mp4", 160, 90)

    destino = garantir_webm(origem, tmp_path / "webm")

    assert destino == tmp_path / "webm" / "entrada.webm"
    captura = cv2.VideoCapture(str(destino))
    lidos = 0
    while captura.read()[0]:
        lidos += 1
    assert lidos == FOTOGRAMAS  # sem fotogramas duplicados nem perdidos: os tempos da contagem dependem disto


def test_reduz_a_largura_acima_de_960_e_nao_amplia_o_que_e_pequeno(tmp_path):
    grande = garantir_webm(_escrever(tmp_path / "grande.mp4", 1280, 720), tmp_path / "webm")
    pequeno = garantir_webm(_escrever(tmp_path / "pequeno.mp4", 320, 180), tmp_path / "webm")

    c = cv2.VideoCapture(str(grande))
    assert (int(c.get(cv2.CAP_PROP_FRAME_WIDTH)), int(c.get(cv2.CAP_PROP_FRAME_HEIGHT))) == (960, 540)
    c = cv2.VideoCapture(str(pequeno))
    assert int(c.get(cv2.CAP_PROP_FRAME_WIDTH)) == 320


def test_reaproveita_o_webm_ja_convertido(tmp_path):
    origem = _escrever(tmp_path / "v.mp4", 160, 90)
    primeiro = garantir_webm(origem, tmp_path / "webm")
    hora = primeiro.stat().st_mtime_ns

    segundo = garantir_webm(origem, tmp_path / "webm")

    assert segundo.stat().st_mtime_ns == hora  # não voltou a converter


def test_converte_de_novo_se_a_origem_for_mais_recente(tmp_path):
    origem = _escrever(tmp_path / "v.mp4", 160, 90)
    primeiro = garantir_webm(origem, tmp_path / "webm")
    futuro = primeiro.stat().st_mtime + 100
    os.utime(origem, (futuro, futuro))

    segundo = garantir_webm(origem, tmp_path / "webm")

    assert segundo.stat().st_mtime > primeiro.stat().st_mtime - 1 and segundo.stat().st_size > 0


def test_um_webm_que_ja_esta_na_pasta_devolve_se_tal_como_esta(tmp_path):
    convertido = garantir_webm(_escrever(tmp_path / "v.mp4", 160, 90), tmp_path / "webm")

    assert garantir_webm(convertido, tmp_path / "webm") == convertido


def test_nao_deixa_ficheiros_parciais_quando_a_conversao_falha(tmp_path):
    lixo = tmp_path / "corrompido.mp4"
    lixo.write_bytes(b"isto nao e um video")

    with pytest.raises(RuntimeError):
        garantir_webm(lixo, tmp_path / "webm")

    assert list((tmp_path / "webm").glob("*")) == []


def test_video_inexistente_falha_alto(tmp_path):
    with pytest.raises(FileNotFoundError):
        garantir_webm(tmp_path / "nao_existe.mp4", tmp_path / "webm")


def test_exigir_webm_recusa_outros_formatos():
    assert exigir_webm(Path("a.webm")) == Path("a.webm")
    with pytest.raises(ValueError):
        exigir_webm(Path("a.mp4"))
