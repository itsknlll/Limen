"""Dependências comuns das rotas."""

from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from ..db import obter_sessao  # noqa: F401  (reexportado para as rotas)


def obter_usuario_atual(request: Request) -> int:
    """Usuário da sessão (cookie assinado). A entrada vem do login com Google (etapa de integração)."""
    usuario_id = request.session.get("usuario_id")
    if usuario_id is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Faça login para continuar")
    return int(usuario_id)


def obter_usuario_logado(
    usuario_id: int = Depends(obter_usuario_atual),
    sessao: Session = Depends(obter_sessao),
) -> "Usuario":
    """Retorna o objeto Usuario completo (necessário para operações que leem campos do modelo)."""
    from sqlalchemy import select
    from ..modelos import Usuario

    usuario = sessao.scalar(select(Usuario).where(Usuario.id == usuario_id))
    if usuario is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Usuário não encontrado")
    return usuario


def obter_porta_google_ads() -> "PortaGoogleAds":
    """Instancia o cliente real da Google Ads API com as credenciais do projeto."""
    from ..servicos.sincronizacao.cliente_real import ClienteRealGoogleAds
    from ..config import configuracoes

    client_id, client_secret = configuracoes.credenciais_google
    return ClienteRealGoogleAds(client_id, client_secret)
