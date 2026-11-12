"""Dependências comuns das rotas."""

from fastapi import HTTPException, Request, status

from ..db import obter_sessao  # noqa: F401  (reexportado para as rotas)


def obter_usuario_atual(request: Request) -> int:
    """Usuário da sessão (cookie assinado). A entrada vem do login com Google (etapa de integração)."""
    usuario_id = request.session.get("usuario_id")
    if usuario_id is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Faça login para continuar")
    return int(usuario_id)
