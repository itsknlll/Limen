"""Rotas de apoio ao desenvolvimento (só existem com AMBIENTE=desenvolvimento).

Permitem testar a API pelo /docs antes do login com Google estar pronto.
"""

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from ...modelos import Usuario
from ...servicos.regras import criar_regras_padrao
from ..deps import obter_sessao

roteador = APIRouter(prefix="/dev", tags=["desenvolvimento"])

EMAIL_DEV = "dev@limen.local"


@roteador.post("/login")
def login_dev(request: Request, sessao: Session = Depends(obter_sessao)):
    usuario = sessao.scalar(select(Usuario).where(Usuario.email == EMAIL_DEV))
    if usuario is None:
        usuario = Usuario(email=EMAIL_DEV, nome="Usuário de desenvolvimento")
        sessao.add(usuario)
        sessao.commit()
    criar_regras_padrao(sessao, usuario.id)
    request.session["usuario_id"] = usuario.id
    return {"usuario_id": usuario.id, "email": usuario.email}


@roteador.post("/logout")
def logout_dev(request: Request):
    request.session.clear()
    return {"ok": True}
