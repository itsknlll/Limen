from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ...servicos.resumo import obter_resumo
from ..deps import obter_sessao, obter_usuario_atual
from ..esquemas import ResumoSaida

roteador = APIRouter(prefix="/resumo", tags=["resumo"])


@roteador.get("", response_model=ResumoSaida)
def resumo(
    inicio: date | None = None,
    fim: date | None = None,
    sessao: Session = Depends(obter_sessao),
    usuario_id: int = Depends(obter_usuario_atual),
):
    """Números da visão geral: campanhas, regras, métricas, alertas e última avaliação."""
    if inicio and fim and inicio > fim:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "inicio deve ser anterior ou igual a fim")
    return obter_resumo(sessao, usuario_id, inicio, fim)
