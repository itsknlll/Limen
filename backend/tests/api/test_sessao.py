"""GET /eu e POST /sessao/sair (Fase 0 do dashboard)."""

import pytest
from fastapi.testclient import TestClient

from app.api.deps import obter_sessao
from app.config import configuracoes
from app.main import criar_app
from app.modelos import Usuario

TOKEN_CIFRADO_FALSO = "gAAAA-token-cifrado-que-nao-pode-vazar"


def test_eu_sem_login_e_401(cliente_sem_login):
    resposta = cliente_sem_login.get("/eu")
    assert resposta.status_code == 401
    assert resposta.json()["tipo"] == "nao_autenticado"


def test_eu_antes_de_conectar_e_sincronizar(cliente, usuario_teste):
    corpo = cliente.get("/eu").json()
    assert corpo == {
        "id": usuario_teste,
        "nome": "Usuário de teste",
        "email": "teste@limen.dev",
        "google_conectado": False,
        "conta_google_ads": None,
    }


def test_eu_conectado_com_conta_e_sem_vazar_token(
    cliente, sessao_teste, usuario_teste, campanhas_teste
):
    sessao_teste.get(Usuario, usuario_teste).refresh_token_cifrado = TOKEN_CIFRADO_FALSO
    sessao_teste.commit()

    resposta = cliente.get("/eu")
    corpo = resposta.json()
    assert corpo["google_conectado"] is True
    assert corpo["conta_google_ads"] == {
        "customer_id": "4327030343",
        "login_customer_id": "1137051091",
    }
    assert TOKEN_CIFRADO_FALSO not in resposta.text
    assert "token" not in " ".join(corpo).lower()  # nenhuma chave com "token"


def test_eu_depois_de_token_revogado(cliente, sessao_teste, usuario_teste, campanhas_teste):
    """O sincronizador apaga o token ao receber TokenRevogado; /eu passa a pedir reconexão."""
    usuario = sessao_teste.get(Usuario, usuario_teste)
    usuario.refresh_token_cifrado = TOKEN_CIFRADO_FALSO
    sessao_teste.commit()
    usuario.refresh_token_cifrado = None
    sessao_teste.commit()

    corpo = cliente.get("/eu").json()
    assert corpo["google_conectado"] is False
    assert corpo["conta_google_ads"] is not None  # a conta continua; só falta autorização


@pytest.fixture
def cliente_com_sessao_real(sessao_teste, monkeypatch):
    """Sessão de verdade (cookie), aberta por /dev/login; usuário não é sobrescrito."""
    monkeypatch.setattr(configuracoes, "ambiente", "desenvolvimento")
    app = criar_app()
    app.dependency_overrides[obter_sessao] = lambda: sessao_teste
    with TestClient(app) as cliente:
        yield cliente


def test_sair_encerra_a_sessao(cliente_com_sessao_real):
    c = cliente_com_sessao_real
    assert c.post("/dev/login").status_code == 200
    assert c.get("/eu").status_code == 200

    resposta = c.post("/sessao/sair")
    assert resposta.status_code == 204
    assert resposta.content == b""
    assert c.get("/eu").status_code == 401


def test_sair_sem_estar_logado_tambem_e_204(cliente_com_sessao_real):
    assert cliente_com_sessao_real.post("/sessao/sair").status_code == 204
