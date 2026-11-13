"""Testes do fluxo OAuth 2.0 com Google (sub-etapas 1 e 2 da integração).

Nenhum teste chama o Google de verdade: as respostas HTTP são simuladas por mocks.
As credenciais (client_id/client_secret) são substituídas por uma propriedade mockada
para não exigir o arquivo client_secret.json durante o CI/CD.
A CHAVE_CIFRAGEM é injetada via fixture autouse para todos os testes do arquivo.
"""

import base64
import json
import secrets

import itsdangerous
import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, PropertyMock, patch
from urllib.parse import parse_qs, urlparse

from app.api.deps import obter_sessao
from app.main import app

_CHAVE_FERNET_TESTE = Fernet.generate_key().decode()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def configurar_chave_cifragem(monkeypatch):
    """Injeta uma chave Fernet válida em todos os testes deste arquivo."""
    from app import config
    monkeypatch.setattr(config.configuracoes, "chave_cifragem", _CHAVE_FERNET_TESTE)


@pytest.fixture
def cliente_oauth(sessao_teste):
    """Cliente HTTP sem usuário pré-autenticado, com sessão de teste isolada."""
    app.dependency_overrides[obter_sessao] = lambda: sessao_teste
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _patch_credenciais():
    """Substitui configuracoes.credenciais_google por valores de teste.

    Evita que os testes tentem ler o client_secret.json do disco.
    """
    return patch(
        "app.config.Configuracoes.credenciais_google",
        new_callable=PropertyMock,
        return_value=("fake_client_id", "fake_client_secret"),
    )


def _make_mock_httpx(
    email: str = "teste@exemplo.com",
    nome: str = "Usuário Teste",
    email_verified: bool = True,
) -> MagicMock:
    """Cria um mock de httpx.Client que simula as respostas do Google OAuth."""
    mock_resp_token = MagicMock()
    mock_resp_token.status_code = 200
    mock_resp_token.json.return_value = {
        "access_token": "tok_acesso_fake",
        "refresh_token": "tok_refresh_fake",
    }

    mock_resp_info = MagicMock()
    mock_resp_info.status_code = 200
    mock_resp_info.json.return_value = {
        "email": email,
        "name": nome,
        "email_verified": email_verified,
    }

    mock_cliente = MagicMock()
    mock_cliente.__enter__ = lambda s: s
    mock_cliente.__exit__ = MagicMock(return_value=False)
    mock_cliente.post.return_value = mock_resp_token
    mock_cliente.get.return_value = mock_resp_info

    return mock_cliente


def _iniciar_login_e_obter_state(cliente_oauth: TestClient) -> str:
    """Chama /login e extrai o state gerado para usar no callback."""
    with _patch_credenciais():
        resp = cliente_oauth.get("/api/oauth/google/login", follow_redirects=False)
    loc = resp.headers["location"]
    return parse_qs(urlparse(loc).query)["state"][0]


# ---------------------------------------------------------------------------
# Testes de /api/oauth/google/login
# ---------------------------------------------------------------------------


def test_login_redireciona_para_google(cliente_oauth):
    with _patch_credenciais():
        resp = cliente_oauth.get("/api/oauth/google/login", follow_redirects=False)

    assert resp.status_code in (302, 307)
    loc = resp.headers["location"]
    assert "accounts.google.com" in loc

    params = parse_qs(urlparse(loc).query)
    assert "openid" in params["scope"][0]
    assert "adwords" in params["scope"][0]
    assert params["access_type"][0] == "offline"
    assert params["response_type"][0] == "code"
    assert params["client_id"][0] == "fake_client_id"


def test_login_grava_state_na_sessao(cliente_oauth):
    """O state gerado em /login deve aparecer na URL de redirecionamento."""
    with _patch_credenciais():
        resp = cliente_oauth.get("/api/oauth/google/login", follow_redirects=False)

    loc = resp.headers["location"]
    params = parse_qs(urlparse(loc).query)
    assert "state" in params
    assert len(params["state"][0]) > 0


def test_login_inclui_pkce_no_url(cliente_oauth):
    """URL de autorização deve conter code_challenge e code_challenge_method=S256 (RFC 7636)."""
    with _patch_credenciais():
        resp = cliente_oauth.get("/api/oauth/google/login", follow_redirects=False)

    params = parse_qs(urlparse(resp.headers["location"]).query)
    assert "code_challenge" in params
    assert len(params["code_challenge"][0]) == 43  # SHA-256 em base64url sem padding = 43 chars
    assert params["code_challenge_method"][0] == "S256"


# ---------------------------------------------------------------------------
# Testes de /api/oauth/google/callback
# ---------------------------------------------------------------------------


def test_callback_state_invalido_retorna_400(cliente_oauth):
    """Sem estado na sessão (ou state errado) → 400 (proteção CSRF)."""
    resp = cliente_oauth.get("/api/oauth/google/callback?code=abc&state=estado-errado")
    assert resp.status_code == 400


def test_callback_error_do_google_retorna_400(cliente_oauth):
    """Usuário nega acesso → Google envia error=access_denied → 400."""
    resp = cliente_oauth.get("/api/oauth/google/callback?error=access_denied&state=qualquer")
    assert resp.status_code == 400


def test_callback_sem_parametros_retorna_400(cliente_oauth):
    resp = cliente_oauth.get("/api/oauth/google/callback")
    assert resp.status_code == 400


def test_callback_cria_usuario_novo(cliente_oauth, sessao_teste):
    """Primeiro login: cria usuário no banco e define usuario_id na sessão."""
    from sqlalchemy import select

    from app.modelos import Usuario

    state = _iniciar_login_e_obter_state(cliente_oauth)

    with _patch_credenciais(), patch(
        "app.api.rotas.oauth.httpx.Client",
        return_value=_make_mock_httpx("novo@exemplo.com", "Novo Usuário"),
    ):
        resp = cliente_oauth.get(
            f"/api/oauth/google/callback?code=cod_fake&state={state}",
            follow_redirects=False,
        )

    assert resp.status_code in (302, 307)

    usuario = sessao_teste.scalar(select(Usuario).where(Usuario.email == "novo@exemplo.com"))
    assert usuario is not None
    assert usuario.nome == "Novo Usuário"


def test_callback_redireciona_para_url_frontend_da_configuracao(cliente_oauth, monkeypatch):
    """O destino vem de configuracoes.url_frontend (valor diferente prova que não é fixo)."""
    from app import config

    monkeypatch.setattr(config.configuracoes, "url_frontend", "http://painel.teste:5999/")
    state = _iniciar_login_e_obter_state(cliente_oauth)

    with _patch_credenciais(), patch(
        "app.api.rotas.oauth.httpx.Client", return_value=_make_mock_httpx()
    ):
        resp = cliente_oauth.get(
            f"/api/oauth/google/callback?code=cod_fake&state={state}",
            follow_redirects=False,
        )

    assert resp.status_code in (302, 307)
    assert resp.headers["location"] == "http://painel.teste:5999/"


def test_url_frontend_padrao_e_o_vite():
    from app.config import Configuracoes

    assert Configuracoes.model_fields["url_frontend"].default == "http://localhost:5173/"


def test_callback_usuario_existente_atualiza_nome(cliente_oauth, sessao_teste):
    """Re-login: nome é atualizado, usuário não é duplicado."""
    from sqlalchemy import select

    from app.modelos import Usuario

    usuario = Usuario(email="existente@exemplo.com", nome="Nome Antigo")
    sessao_teste.add(usuario)
    sessao_teste.commit()

    state = _iniciar_login_e_obter_state(cliente_oauth)

    with _patch_credenciais(), patch(
        "app.api.rotas.oauth.httpx.Client",
        return_value=_make_mock_httpx("existente@exemplo.com", "Nome Novo"),
    ):
        resp = cliente_oauth.get(
            f"/api/oauth/google/callback?code=cod_fake&state={state}",
            follow_redirects=False,
        )

    assert resp.status_code in (302, 307)
    sessao_teste.refresh(usuario)
    assert usuario.nome == "Nome Novo"

    # Não criou duplicata
    total = sessao_teste.scalars(
        select(Usuario).where(Usuario.email == "existente@exemplo.com")
    ).all()
    assert len(total) == 1


def test_callback_sem_pkce_verifier_retorna_400(cliente_oauth):
    """Sessão com oauth_state mas sem pkce_verifier → 400 com mensagem específica.

    Monta manualmente o cookie no formato do Starlette SessionMiddleware:
    BASE64(JSON) assinado com itsdangerous.TimestampSigner(segredo_sessao).
    Assim o state passa pela checagem CSRF mas o verifier está ausente.
    """
    from app.config import configuracoes

    state = secrets.token_urlsafe(16)
    dados_sessao = {"oauth_state": state}   # deliberadamente sem pkce_verifier
    payload = base64.b64encode(json.dumps(dados_sessao).encode("utf-8"))
    cookie = itsdangerous.TimestampSigner(configuracoes.segredo_sessao).sign(payload).decode("utf-8")

    cliente_oauth.cookies.set("session", cookie)
    resp = cliente_oauth.get(
        f"/api/oauth/google/callback?code=cod_fake&state={state}",
        follow_redirects=False,
    )

    assert resp.status_code == 400
    assert resp.json()["detail"] == "PKCE verifier ausente na sessão"


def test_callback_envia_code_verifier_na_troca(cliente_oauth):
    """PKCE: code_verifier deve ser enviado no POST ao endpoint de token do Google."""
    state = _iniciar_login_e_obter_state(cliente_oauth)
    mock_httpx = _make_mock_httpx()

    with _patch_credenciais(), patch("app.api.rotas.oauth.httpx.Client", return_value=mock_httpx):
        cliente_oauth.get(
            f"/api/oauth/google/callback?code=cod_fake&state={state}",
            follow_redirects=False,
        )

    dados_post = mock_httpx.post.call_args.kwargs["data"]
    assert "code_verifier" in dados_post
    assert len(dados_post["code_verifier"]) >= 43  # mínimo exigido pela RFC 7636


def test_callback_email_nao_verificado_retorna_400(cliente_oauth):
    """E-mail não verificado pelo Google → 400."""
    state = _iniciar_login_e_obter_state(cliente_oauth)

    with _patch_credenciais(), patch(
        "app.api.rotas.oauth.httpx.Client",
        return_value=_make_mock_httpx(email_verified=False),
    ):
        resp = cliente_oauth.get(
            f"/api/oauth/google/callback?code=cod_fake&state={state}",
            follow_redirects=False,
        )

    assert resp.status_code == 400


def test_callback_state_so_pode_ser_usado_uma_vez(cliente_oauth):
    """State é removido da sessão no primeiro uso: replay attack → 400."""
    state = _iniciar_login_e_obter_state(cliente_oauth)

    with _patch_credenciais(), patch(
        "app.api.rotas.oauth.httpx.Client",
        return_value=_make_mock_httpx(),
    ):
        resp1 = cliente_oauth.get(
            f"/api/oauth/google/callback?code=cod1&state={state}",
            follow_redirects=False,
        )
        resp2 = cliente_oauth.get(
            f"/api/oauth/google/callback?code=cod2&state={state}",
            follow_redirects=False,
        )

    assert resp1.status_code in (302, 307)
    assert resp2.status_code == 400


# ---------------------------------------------------------------------------
# Sub-etapa 2: refresh token cifrado em Usuario
# ---------------------------------------------------------------------------


def test_callback_armazena_refresh_token_cifrado(cliente_oauth, sessao_teste):
    """Refresh token deve ser armazenado cifrado em Usuario.refresh_token_cifrado."""
    from sqlalchemy import select

    from app.modelos import Usuario
    from app.servicos.cifra import decifrar

    state = _iniciar_login_e_obter_state(cliente_oauth)

    with _patch_credenciais(), patch(
        "app.api.rotas.oauth.httpx.Client",
        return_value=_make_mock_httpx("token@exemplo.com"),
    ):
        cliente_oauth.get(
            f"/api/oauth/google/callback?code=cod_fake&state={state}",
            follow_redirects=False,
        )

    usuario = sessao_teste.scalar(select(Usuario).where(Usuario.email == "token@exemplo.com"))
    assert usuario.refresh_token_cifrado is not None
    assert usuario.refresh_token_cifrado != "tok_refresh_fake"   # não está em texto puro
    assert decifrar(usuario.refresh_token_cifrado) == "tok_refresh_fake"


def test_callback_sem_refresh_token_retorna_400(cliente_oauth, sessao_teste):
    """Google sem refresh_token → 400 com mensagem específica; nenhum usuário criado."""
    from sqlalchemy import func, select

    from app.modelos import Usuario

    contagem_antes = sessao_teste.scalar(select(func.count(Usuario.id)))

    state = _iniciar_login_e_obter_state(cliente_oauth)

    mock_sem_token = _make_mock_httpx()
    mock_sem_token.post.return_value.json.return_value = {"access_token": "tok_acesso_fake"}

    with _patch_credenciais(), patch(
        "app.api.rotas.oauth.httpx.Client", return_value=mock_sem_token
    ):
        resp = cliente_oauth.get(
            f"/api/oauth/google/callback?code=cod_fake&state={state}",
            follow_redirects=False,
        )

    assert resp.status_code == 400
    assert "refresh_token" in resp.json()["detail"]
    assert sessao_teste.scalar(select(func.count(Usuario.id))) == contagem_antes
