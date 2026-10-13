"""Leitura da configuração: variáveis de ambiente, com o `backend/.env` como apoio em desenvolvimento.

O `.env` nunca vai para o Git (tem chaves). Uma variável já definida no ambiente tem prioridade sobre
o `.env`, o que permite sobrepor valores sem editar o ficheiro.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parents[3]
_ENV = RAIZ / "backend" / ".env"
load_dotenv(_ENV, override=False)


def ler(nome: str, por_omissao: str | None = None) -> str | None:
    valor = os.environ.get(nome, "").strip()
    return valor or por_omissao
