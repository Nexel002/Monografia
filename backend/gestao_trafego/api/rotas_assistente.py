"""Rotas do assistente: perguntas, relatório e voz. Só consultam resultados; nada aqui altera o sistema."""

from typing import Literal

import psycopg
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field

from gestao_trafego.api.rotas_historico import base_de_dados
from gestao_trafego.assistente import seguranca, voz
from gestao_trafego.assistente.servico import ServicoDoAssistente

router = APIRouter(prefix="/api/assistente")

_servico = ServicoDoAssistente()


def obter_servico() -> ServicoDoAssistente:
    return _servico


class Mensagem(BaseModel):
    papel: Literal["utilizador", "assistente"]
    texto: str = Field(max_length=4000)


class Pergunta(BaseModel):
    # Limites para uma pergunta não custar uma fortuna em tokens nem servir para despejar texto no modelo.
    pergunta: str = Field(min_length=1, max_length=1000)
    historico: list[Mensagem] = Field(default_factory=list, max_length=20)


class PedidoDeVoz(BaseModel):
    texto: str = Field(min_length=1, max_length=6000)


def _como_json(r) -> dict:
    return {"texto": r.texto, "modo": r.modo, "ferramentas_usadas": r.ferramentas_usadas, "aviso": r.aviso}


@router.get("/estado")
def estado(servico: ServicoDoAssistente = Depends(obter_servico)) -> dict:
    from gestao_trafego.comum.configuracao import ler

    return {
        "gemini_configurado": servico.gemini_configurado,
        "voz_do_servidor": bool(ler("GOOGLE_TTS_API_KEY") or (ler("ELEVEN_LABS_API_KEY") and ler("ELEVEN_LABS_VOICE_ID"))),
        "perguntas_sugeridas": seguranca.PERGUNTAS_SUGERIDAS,
    }


@router.post("/perguntar")
def perguntar(corpo: Pergunta, ligacao: psycopg.Connection = Depends(base_de_dados), servico: ServicoDoAssistente = Depends(obter_servico)) -> dict:
    return _como_json(servico.perguntar(ligacao, corpo.pergunta, [m.model_dump() for m in corpo.historico]))


@router.get("/relatorio")
def relatorio(ligacao: psycopg.Connection = Depends(base_de_dados), servico: ServicoDoAssistente = Depends(obter_servico)) -> dict:
    return _como_json(servico.relatorio(ligacao))


@router.post("/voz")
def sintetizar_voz(corpo: PedidoDeVoz) -> Response:
    resultado = voz.sintetizar(corpo.texto)
    if resultado is None:
        # 503 e não 200 vazio: o cliente tem de saber que deve usar a voz do browser
        raise HTTPException(503, "Sem voz de servidor disponível (sem chaves ou serviço indisponível).")
    audio, tipo = resultado
    return Response(content=audio, media_type=tipo)
