"""Fixtures dos testes que usam o PostgreSQL de teste (banco limen_teste).

A cada execução, o esquema é apagado (downgrade) e recriado (upgrade) pelas
próprias migrações. Isso testa também se a migração funciona nos dois sentidos.
Cada teste roda dentro de uma transação desfeita no final, então um teste não
interfere no outro.

Se o banco não estiver no ar, estes testes são pulados (os do motor continuam).
"""

from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError

from app.config import configuracoes

RAIZ_BACKEND = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="session")
def engine_teste():
    url = configuracoes.database_url_teste
    if not url:
        pytest.skip("DATABASE_URL_TESTE não configurada em backend/.env")

    engine = create_engine(url)
    try:
        with engine.connect():
            pass
    except OperationalError:
        pytest.skip("Banco de teste fora do ar: rode 'docker compose up -d' na raiz do projeto")

    cfg = Config(str(RAIZ_BACKEND / "alembic.ini"))
    cfg.set_main_option("script_location", str(RAIZ_BACKEND / "alembic"))
    cfg.set_main_option("sqlalchemy.url", url)
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")

    yield engine
    engine.dispose()


@pytest.fixture
def conexao(engine_teste):
    with engine_teste.connect() as con:
        transacao = con.begin()
        yield con
        transacao.rollback()
