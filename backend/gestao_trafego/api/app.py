"""Aplicação FastAPI.

Arranque (a partir de backend/):
    uv run uvicorn gestao_trafego.api.app:criar_app --factory --port 8000

A API só traduz HTTP e WebSocket: a lógica está em `dados/`, `simulacao/` e `controlo/`.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from gestao_trafego.api import ao_vivo, rotas_assistente, rotas_historico, rotas_visao, visao_ao_vivo
from gestao_trafego.comum.configuracao import ler

# O Vite (dashboard em desenvolvimento) serve a partir de outra porta, por isso o browser pede CORS.
ORIGENS_POR_OMISSAO = "http://localhost:5174,http://127.0.0.1:5174"


@asynccontextmanager
async def _ciclo_de_vida(_: FastAPI):
    # Arrancar já o PostgreSQL embebido: o primeiro pedido não tem de esperar pelo `initdb`.
    import asyncio

    from gestao_trafego.dados.ligacao import obter_url

    await asyncio.to_thread(obter_url)
    yield


def criar_app() -> FastAPI:
    app = FastAPI(title="Gestão de tráfego com IA — Maputo", lifespan=_ciclo_de_vida)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=ler("ORIGENS_PERMITIDAS", ORIGENS_POR_OMISSAO).split(","),
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )
    app.include_router(rotas_historico.router)
    app.include_router(rotas_visao.router)
    app.include_router(rotas_assistente.router)
    app.include_router(ao_vivo.router)
    app.include_router(visao_ao_vivo.router)
    return app
