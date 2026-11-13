"""Fluxo OAuth 2.0 com Google (openid + email + adwords).

Decisões:
- state aleatório gerado em /login e verificado em /callback: protege contra CSRF.
- PKCE S256 (RFC 7636, recomendado pela RFC 9700 também para aplicações web):
  code_verifier guardado na sessão; code_challenge enviado ao Google na autorização;
  code_verifier enviado na troca do código, impedindo interceptação do authorization code.
- email_verified deve ser true: recusa contas Google com e-mail não confirmado.
- Sessão limpa antes de gravar usuario_id: descarta dados residuais de sessão anterior.
- Usuário identificado pelo e-mail (único no banco). Novo usuário recebe as regras padrão.
- refresh_token cifrado com Fernet (CHAVE_CIFRAGEM) e guardado em Usuario.refresh_token_cifrado
  (fonte única; ContaGoogleAds lê por FK na sincronização de campanhas).
  Google não devolve refresh_token sem prompt=consent; recusa-se a continuar se ausente.
- Credenciais lidas em tempo de execução via configuracoes.credenciais_google
  (nunca duplicadas no .env).
"""

import base64
import hashlib
import secrets
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ...config import configuracoes
from ...modelos import Usuario
from ...servicos.cifra import cifrar
from ...servicos.regras import criar_regras_padrao
from ..deps import obter_sessao

roteador = APIRouter(prefix="/api/oauth", tags=["oauth"])

_GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
_GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
_GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"


def _gerar_pkce() -> tuple[str, str]:
    """Gera (code_verifier, code_challenge) para PKCE S256 (RFC 7636).

    code_verifier: 64 chars URL-safe (acima do mínimo de 43 exigido pela RFC).
    code_challenge: BASE64URL(SHA-256(verifier)) sem padding '='.
    """
    verifier = secrets.token_urlsafe(48)  # 48 bytes → 64 chars base64url
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return verifier, challenge


@roteador.get("/google/login", summary="Inicia login com Google")
def login_google(request: Request) -> RedirectResponse:
    """Gera o URL de autorização do Google e redireciona o navegador."""
    client_id, _ = configuracoes.credenciais_google

    state = secrets.token_urlsafe(16)
    verifier, challenge = _gerar_pkce()

    request.session["oauth_state"] = state
    request.session["pkce_verifier"] = verifier

    params = urlencode({
        "client_id": client_id,
        "redirect_uri": configuracoes.google_redirect_uri,
        "response_type": "code",
        "scope": "openid email profile https://www.googleapis.com/auth/adwords",
        "state": state,
        "access_type": "offline",
        "prompt": "consent",          # garante que o Google sempre devolve refresh_token
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    })
    return RedirectResponse(f"{_GOOGLE_AUTH_URL}?{params}")


@roteador.get("/google/callback", summary="Callback OAuth do Google")
def callback_google(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    sessao: Session = Depends(obter_sessao),
) -> RedirectResponse:
    """
    Google redireciona aqui após a autorização.
    Troca o código por tokens, identifica o usuário pelo e-mail e abre a sessão.
    """
    # Usuário clicou em "Negar" no consentimento do Google
    if error:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Autorização negada: {error}")

    if not code or not state:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Parâmetros de callback ausentes")

    # Proteção CSRF: state deve bater com o valor gravado antes do redirect
    estado_esperado = request.session.pop("oauth_state", None)
    if not estado_esperado or state != estado_esperado:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Estado OAuth inválido ou expirado")

    # PKCE: recuperar o verifier gerado em /login
    verifier = request.session.pop("pkce_verifier", None)
    if not verifier:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "PKCE verifier ausente na sessão")

    client_id, client_secret = configuracoes.credenciais_google

    # Trocar código de autorização por access_token (+ refresh_token com prompt=consent).
    # code_verifier permite ao Google confirmar que quem iniciou o fluxo é quem o completa.
    with httpx.Client() as cliente_http:
        resposta_token = cliente_http.post(
            _GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": configuracoes.google_redirect_uri,
                "grant_type": "authorization_code",
                "code_verifier": verifier,
            },
        )
    if resposta_token.status_code != 200:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Falha ao obter token do Google")

    tokens = resposta_token.json()

    # Google só devolve refresh_token com prompt=consent; ausente indica problema no fluxo.
    refresh_token = tokens.get("refresh_token")
    if not refresh_token:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Google não devolveu refresh_token — verifique os parâmetros do fluxo OAuth",
        )

    # Obter e-mail e nome via endpoint de informações do usuário
    with httpx.Client() as cliente_http:
        resposta_info = cliente_http.get(
            _GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
    if resposta_info.status_code != 200:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Falha ao obter dados do usuário")

    info = resposta_info.json()

    # Rejeitar e-mails não verificados (proteção contra contas Google não confirmadas)
    if not info.get("email_verified"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "E-mail Google não verificado")

    email: str = info["email"]
    nome: str = info.get("name", email)

    # Criar usuário novo ou atualizar nome e token do já existente
    usuario = sessao.scalar(select(Usuario).where(Usuario.email == email))
    if usuario is None:
        usuario = Usuario(email=email, nome=nome, refresh_token_cifrado=cifrar(refresh_token))
        sessao.add(usuario)
        sessao.flush()
        criar_regras_padrao(sessao, usuario.id)
    else:
        usuario.nome = nome
        usuario.refresh_token_cifrado = cifrar(refresh_token)
    sessao.commit()

    # Limpar a sessão antes de gravar: descarta qualquer dado residual de sessão anterior
    request.session.clear()
    request.session["usuario_id"] = usuario.id

    # Volta para o dashboard. Destino fixo na configuração (não vem da URL).
    return RedirectResponse(configuracoes.url_frontend)
