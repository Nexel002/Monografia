"""Ligação ao PostgreSQL.

`DATABASE_URL` aponta para um PostgreSQL já existente. Se não estiver definida, arranca-se um
PostgreSQL embebido em `dados/postgres/` (pacote `pgserver`): assim o protótipo corre numa máquina
sem servidor instalado e a defesa não depende de internet nem de privilégios de administrador.
"""

from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

import psycopg
from psycopg.rows import dict_row

from gestao_trafego.comum.configuracao import RAIZ, ler

PASTA_POSTGRES_EMBEBIDO = RAIZ / "dados" / "postgres"
_ESQUEMA = Path(__file__).with_name("esquema.sql")
_servidor_embebido = None  # guardado para o servidor não ser parado pelo recolector de lixo


def obter_url() -> str:
    global _servidor_embebido
    url = ler("DATABASE_URL")
    if url:
        return url
    if _servidor_embebido is None:
        import pgserver

        PASTA_POSTGRES_EMBEBIDO.mkdir(parents=True, exist_ok=True)
        _servidor_embebido = pgserver.get_server(PASTA_POSTGRES_EMBEBIDO, cleanup_mode="stop")
    return _servidor_embebido.get_uri()


@contextmanager
def ligar(url: str | None = None) -> Iterator[psycopg.Connection]:
    """Liga, garante o esquema e devolve linhas como dicionários. Faz commit no fim, rollback se falhar."""
    with psycopg.connect(url or obter_url(), row_factory=dict_row) as ligacao:
        ligacao.execute(_ESQUEMA.read_text(encoding="utf-8"))
        # Confirmar já: o DDL (sobretudo o CREATE INDEX) pede bloqueios que travam as outras ligações
        # enquanto esta transacção estiver aberta. Sem isto, duas ligações simultâneas ficavam presas
        # uma à espera da outra.
        ligacao.commit()
        yield ligacao
