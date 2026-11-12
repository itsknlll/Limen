"""Conexão com o PostgreSQL e sessão do SQLAlchemy."""

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import configuracoes


class Base(DeclarativeBase):
    pass


engine = create_engine(configuracoes.database_url, pool_pre_ping=True)
SessaoLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def obter_sessao() -> Iterator[Session]:
    """Dependência do FastAPI: uma sessão por requisição."""
    with SessaoLocal() as sessao:
        yield sessao
