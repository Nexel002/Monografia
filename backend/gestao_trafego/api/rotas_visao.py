"""Rotas da visão computacional: vídeos anotados e resumos de contagem produzidos por `visao.contar`."""

import json
import re
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from gestao_trafego.comum.configuracao import RAIZ

router = APIRouter(prefix="/api/visao")

PASTA_RESULTADOS = RAIZ / "dados" / "resultados"
_NOME_VALIDO = re.compile(r"^visao_[A-Za-z0-9_\-]+$")


def _pasta(nome: str) -> Path:
    # O nome vem do URL: só se aceita o padrão das pastas da visão, nunca um caminho arbitrário.
    if not _NOME_VALIDO.match(nome) or not (PASTA_RESULTADOS / nome).is_dir():
        raise HTTPException(404, f"Não existe a pasta de visão {nome!r}.")
    return PASTA_RESULTADOS / nome


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
