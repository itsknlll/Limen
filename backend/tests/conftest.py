"""Fixtures compartilhadas pelos testes de banco e de API.

Banco de teste: limen_teste. A cada execução, o esquema é apagado (downgrade)
e recriado (upgrade) pelas próprias migrações, o que também testa a migração
nos dois sentidos. Cada teste roda numa transação desfeita ao final, então um
teste não interfere no outro. Se o banco não estiver no ar, os testes que
dependem dele são pulados (os do motor continuam rodando).
"""

from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.config import configuracoes

RAIZ_BACKEND = Path(__file__).resolve().parents[1]


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


@pytest.fixture
def sessao_teste(conexao):
    # "create_savepoint": o commit() do código vira um SAVEPOINT, e a transação
    # externa é desfeita no fim do teste.
    sessao = Session(bind=conexao, join_transaction_mode="create_savepoint", expire_on_commit=False)
    yield sessao
    sessao.close()


@pytest.fixture
def usuario_teste(sessao_teste) -> int:
    from app.modelos import Usuario

    usuario = Usuario(email="teste@limen.dev", nome="Usuário de teste")
    sessao_teste.add(usuario)
    sessao_teste.flush()
    return usuario.id


@pytest.fixture
def campanhas_teste(sessao_teste, usuario_teste) -> dict[str, int]:
    """Espelha a conta de teste real: A e B ativas, C pausada (IDs reais do Google Ads)."""
    from app.modelos import Campanha, ContaGoogleAds

    conta = ContaGoogleAds(
        usuario_id=usuario_teste,
        customer_id="4327030343",
        login_customer_id="1137051091",
        nome="Limen Cliente Teste",
    )
    sessao_teste.add(conta)
    sessao_teste.flush()
    dados = {
        "A": (24444020070, "Limen A - Pesquisa", "ENABLED", 50_000_000),
        "B": (24464752468, "Limen B - Pesquisa", "ENABLED", 80_000_000),
        "C": (24458906837, "Limen C - Pesquisa", "PAUSED", 40_000_000),
    }
    ids = {}
    for chave, (google_id, nome, status, orcamento) in dados.items():
        campanha = Campanha(
            conta_id=conta.id,
            google_campaign_id=google_id,
            nome=nome,
            status=status,
            orcamento_micros=orcamento,
        )
        sessao_teste.add(campanha)
        sessao_teste.flush()
        ids[chave] = campanha.id
    sessao_teste.commit()
    return ids


@pytest.fixture
def cliente(sessao_teste, usuario_teste):
    """Cliente HTTP da API usando a sessão de teste e um usuário já autenticado."""
    from app.api.deps import obter_sessao, obter_usuario_atual
    from app.main import app

    app.dependency_overrides[obter_sessao] = lambda: sessao_teste
    app.dependency_overrides[obter_usuario_atual] = lambda: usuario_teste
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def cliente_sem_login(sessao_teste):
    from app.api.deps import obter_sessao
    from app.main import app

    app.dependency_overrides[obter_sessao] = lambda: sessao_teste
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
