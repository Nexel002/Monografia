"""Rotas de leitura: resultados guardados na base de dados. Só leem; nada aqui corre simulações."""

import json
from collections.abc import Iterator

import psycopg
from fastapi import APIRouter, Depends, HTTPException

from gestao_trafego.dados import repositorio
from gestao_trafego.dados.ligacao import ligar
from gestao_trafego.previsao.treinar import CAMINHO_DAS_METRICAS
from gestao_trafego.simulacao.geometria import geometria_da_rede

router = APIRouter(prefix="/api")


def base_de_dados() -> Iterator[psycopg.Connection]:
    with ligar() as ligacao:
        yield ligacao


@router.get("/saude")
def saude() -> dict:
    return {"estado": "ok"}


@router.get("/rede")
def rede() -> dict:
    """Ruas e sinais de semáforo, para desenhar o mapa. Não muda: o cliente pode guardá-la em cache."""
    return geometria_da_rede()


@router.get("/execucoes")
def execucoes(ligacao: psycopg.Connection = Depends(base_de_dados)) -> list[dict]:
    return repositorio.listar_execucoes(ligacao)


@router.get("/execucoes/{execucao_id}/serie")
def serie(execucao_id: int, ligacao: psycopg.Connection = Depends(base_de_dados)) -> list[dict]:
    pontos = repositorio.serie_da_execucao(ligacao, execucao_id)
    if not pontos:
        raise HTTPException(404, f"Não há série para a execução {execucao_id}.")
    return pontos


@router.get("/comparacao")
def comparacao(incidente: bool = True, escala: float = 1.0, ligacao: psycopg.Connection = Depends(base_de_dados)) -> list[dict]:
    """Média e dispersão por configuração, só nas sementes comuns a todas."""
    return repositorio.comparar_configuracoes(ligacao, incidente, escala)


@router.get("/previsao/metricas")
def metricas_da_previsao() -> dict:
    if not CAMINHO_DAS_METRICAS.exists():
        raise HTTPException(404, "O modelo ainda não foi treinado (python -m gestao_trafego.previsao.treinar).")
    return json.loads(CAMINHO_DAS_METRICAS.read_text(encoding="utf-8"))


@router.get("/previsao/{execucao_id}")
def previsao(execucao_id: int, horizonte_s: int = 60, ligacao: psycopg.Connection = Depends(base_de_dados)) -> list[dict]:
    """Previsto contra real, para as execuções que ficaram no conjunto de teste."""
    pontos = repositorio.listar_previsoes(ligacao, execucao_id, horizonte_s)
    if not pontos:
        raise HTTPException(404, "Não há previsões para essa execução e horizonte (só existem para as de teste).")
    return pontos


@router.get("/contagens")
def contagens(origem: str | None = None, ligacao: psycopg.Connection = Depends(base_de_dados)) -> list[dict]:
    return repositorio.listar_contagens(ligacao, origem)
