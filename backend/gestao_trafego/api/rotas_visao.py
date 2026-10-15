"""Rotas da visão computacional: vídeos anotados e resumos de contagem produzidos por `visao.contar`."""

import json
import re
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from gestao_trafego.comum.configuracao import RAIZ
from gestao_trafego.visao.video import PASTA_WEBM

router = APIRouter(prefix="/api/visao")

PASTA_RESULTADOS = RAIZ / "dados" / "resultados"
_NOME_VALIDO = re.compile(r"^visao_[A-Za-z0-9_\-]+$")
_VIDEO_VALIDO = re.compile(r"^[A-Za-z0-9_\-]+\.webm$")


def resolver_video(nome: str) -> Path | None:
    """Caminho de um WebM de `dados/videos_webm/` (os únicos que o backend lê), ou None. O nome vem do cliente: só se aceita um nome simples
    de ficheiro que exista nessa pasta, nunca um caminho."""
    if not _VIDEO_VALIDO.match(nome):
        return None
    ficheiro = PASTA_WEBM / nome
    return ficheiro if ficheiro.is_file() else None


def _pasta(nome: str) -> Path:
    # O nome vem do URL: só se aceita o padrão das pastas da visão, nunca um caminho arbitrário.
    if not _NOME_VALIDO.match(nome) or not (PASTA_RESULTADOS / nome).is_dir():
        raise HTTPException(404, f"Não existe a pasta de visão {nome!r}.")
    return PASTA_RESULTADOS / nome


@router.get("/videos")
def listar_videos() -> list[dict]:
    """Os vídeos (já convertidos para WebM), para o modo ao vivo (o algoritmo corre sobre eles enquanto passam no browser)."""
    return [
        {"nome": f.name, "tamanho_mb": round(f.stat().st_size / 1_000_000, 1)}
        for f in sorted(PASTA_WEBM.glob("*.webm"))
    ]


@router.get("/videos/{nome}")
def video_original(nome: str) -> FileResponse:
    ficheiro = resolver_video(nome)
    if ficheiro is None:
        raise HTTPException(404, f"Não existe o vídeo {nome!r}.")
    return FileResponse(ficheiro, media_type="video/webm")


@router.get("")
def listar() -> list[dict]:
    resultado = []
    for pasta in sorted(PASTA_RESULTADOS.glob("visao_*")):
        contagem = pasta / "contagem.json"
        dados = json.loads(contagem.read_text(encoding="utf-8")) if contagem.exists() else {}
        resultado.append(
            {
                "pasta": pasta.name,
                "tem_video": (pasta / "anotado.mp4").exists(),
                "total": dados.get("total"),
                "modelo": dados.get("modelo"),
                "tamanho_imagem": dados.get("tamanho_imagem"),
                "fps_de_processamento": dados.get("fps_de_processamento"),
            }
        )
    return resultado


@router.get("/{pasta}/resumo")
def resumo(pasta: str) -> dict:
    ficheiro = _pasta(pasta) / "contagem.json"
    if not ficheiro.exists():
        raise HTTPException(404, "Esta pasta não tem contagem.json.")
    dados = json.loads(ficheiro.read_text(encoding="utf-8"))
    dados.pop("passagens", None)  # centenas de linhas que o dashboard não usa
    return dados


@router.get("/{pasta}/video")
def video(pasta: str) -> FileResponse:
    ficheiro = _pasta(pasta) / "anotado.mp4"
    if not ficheiro.exists():
        raise HTTPException(404, "Esta pasta não tem vídeo anotado.")
    return FileResponse(ficheiro, media_type="video/mp4")
