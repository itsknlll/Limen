"""POST e PUT /regras devolvem a regra igual ao GET seguinte (limiar no formato do banco).

Os demais testes de API usam uma sessão só para todos os pedidos: POST e GET leem o
mesmo objeto em memória e a diferença não apareceria. Aqui cada pedido abre a própria
sessão, com as configurações do SessaoLocal de produção (como o obter_sessao), dentro
da transação do teste, que a fixture `conexao` desfaz no fim.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app import db
from app.api.deps import obter_sessao, obter_usuario_atual
from app.main import app
from app.modelos import Usuario

CORPO = {"codigo": "R9", "nome": "CPC muito alto", "condicoes": [{"metrica": "cpc", "operador": ">", "limiar": "7.5"}]}


@pytest.fixture
def cliente_por_pedido(conexao):
    fabrica = sessionmaker(**(db.SessaoLocal.kw | {"bind": conexao, "join_transaction_mode": "create_savepoint"}))
    with fabrica() as s:
        usuario = Usuario(email="formato@limen.dev")
        s.add(usuario)
        s.commit()
        usuario_id = usuario.id

    def sessao_por_pedido():
        with fabrica() as s:
            yield s

    # Guarda as substituições que já existiam (ex.: do conftest) e as devolve no fim.
    antigos = dict(app.dependency_overrides)
    app.dependency_overrides[obter_sessao] = sessao_por_pedido
    app.dependency_overrides[obter_usuario_atual] = lambda: usuario_id
    try:
        with TestClient(app) as c:
            yield c
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(antigos)


def test_post_responde_igual_ao_get_seguinte(cliente_por_pedido):
    post = cliente_por_pedido.post("/regras", json=CORPO)
    assert post.status_code == 201, post.text
    get = cliente_por_pedido.get(f"/regras/{post.json()['id']}")
    assert post.json() == get.json()
    assert post.json()["condicoes"][0]["limiar"] == "7.500000"


def test_put_responde_igual_ao_get_seguinte(cliente_por_pedido):
    rid = cliente_por_pedido.post("/regras", json=CORPO).json()["id"]
    put = cliente_por_pedido.put(f"/regras/{rid}", json=CORPO | {
        "condicoes": [{"metrica": "cpc", "operador": ">", "limiar": "8"}, {"metrica": "ctr", "operador": "<", "limiar": "0.5"}],
    })
    assert put.status_code == 200, put.text
    get = cliente_por_pedido.get(f"/regras/{rid}")
    assert put.json() == get.json()
    assert [c["limiar"] for c in put.json()["condicoes"]] == ["8.000000", "0.500000"]
