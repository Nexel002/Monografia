import pytest


@pytest.fixture(scope="session")
def url(tmp_path_factory):
    """Um PostgreSQL embebido para todos os testes que precisam de base de dados (o `initdb` custa ~20 s)."""
    pgserver = pytest.importorskip("pgserver")
    servidor = pgserver.get_server(tmp_path_factory.mktemp("pg"), cleanup_mode="stop")
    yield servidor.get_uri()
    servidor.cleanup()
