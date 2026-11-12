from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ...servicos import alertas as servico
from ..deps import obter_sessao, obter_usuario_atual
from ..esquemas import AlertaSaida

roteador = APIRouter(prefix="/alertas", tags=["alertas"])


@roteador.get("", response_model=list[AlertaSaida])
def listar(
    campanha_id: int | None = None,
    regra_id: int | None = None,
    inicio: date | None = None,
    fim: date | None = None,
    limite: int = Query(default=500, ge=1, le=5000),
    sessao: Session = Depends(obter_sessao),
    usuario_id: int = Depends(obter_usuario_atual),
):
    """Alertas com a campanha, a regra, o valor medido e a data do registro (caso IN-10)."""
    return servico.listar_alertas(sessao, usuario_id, campanha_id, regra_id, inicio, fim, limite)
