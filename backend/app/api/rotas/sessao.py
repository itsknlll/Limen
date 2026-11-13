"""Sessão do usuário no dashboard: quem está logado e sair.

`/eu` diz ao frontend se mostra "Google Ads conectado" ou "Reconectar"
(`google_conectado` = existe refresh token). O token nunca sai na resposta.
"""

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ...modelos import ContaGoogleAds, Usuario
from ..deps import obter_sessao, obter_usuario_logado
from ..esquemas import EuSaida

roteador = APIRouter(tags=["sessão"])


@roteador.get("/eu", response_model=EuSaida)
def eu(
    usuario: Usuario = Depends(obter_usuario_logado),
    sessao: Session = Depends(obter_sessao),
):
    # A conta é criada na primeira sincronização; antes disso, null.
    conta = sessao.scalar(
        select(ContaGoogleAds)
        .where(ContaGoogleAds.usuario_id == usuario.id)
        .order_by(ContaGoogleAds.id.desc())
        .limit(1)
    )
    return EuSaida(
        id=usuario.id,
        nome=usuario.nome,
        email=usuario.email,
        google_conectado=usuario.refresh_token_cifrado is not None,
        conta_google_ads=conta,
    )


@roteador.post("/sessao/sair", status_code=status.HTTP_204_NO_CONTENT)
def sair(request: Request):
    """Encerra a sessão. Idempotente: sair sem estar logado também devolve 204."""
    request.session.clear()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
