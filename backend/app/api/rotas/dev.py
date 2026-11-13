"""Rotas de apoio ao desenvolvimento (só existem com AMBIENTE=desenvolvimento).

Permitem testar a API pelo /docs antes do login com Google estar pronto.
"""

from datetime import date

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from ...modelos import Usuario
from ...servicos.regras import criar_regras_padrao
from ...servicos.sinteticas import gerador
from ...servicos.sinteticas.semeador import semear_metricas_sinteticas
from ..deps import obter_sessao, obter_usuario_atual

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


@roteador.post(
    "/metricas-sinteticas",
    summary="Gera métricas sintéticas nas campanhas sincronizadas (IN-02b)",
)
def metricas_sinteticas(
    semente: int = Query(gerador.SEMENTE_PADRAO),
    inicio: date = Query(gerador.INICIO_PADRAO),
    dias: int = Query(gerador.DIAS_PADRAO, ge=9, le=3660),
    sessao: Session = Depends(obter_sessao),
    usuario_id: int = Depends(obter_usuario_atual),
):
    """Grava métricas sintéticas (origem='sintetica') com semente fixa. Rodar de novo não duplica.

    Usa a mesma dependência de login das rotas autenticadas (401 sem sessão).
    Como todo o roteador /dev, só existe com AMBIENTE=desenvolvimento.
    """
    return semear_metricas_sinteticas(sessao, usuario_id, semente, inicio, dias)
