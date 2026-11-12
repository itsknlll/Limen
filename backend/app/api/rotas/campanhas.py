from datetime import date

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from ...servicos import campanhas as servico
from ..deps import obter_sessao, obter_usuario_atual
from ..esquemas import CampanhaSaida, IngestaoSaida, LoteMetricasEntrada, MetricaSaida

roteador = APIRouter(prefix="/campanhas", tags=["campanhas"])


@roteador.get("", response_model=list[CampanhaSaida])
def listar(
    sessao: Session = Depends(obter_sessao),
    usuario_id: int = Depends(obter_usuario_atual),
):
    return servico.listar_campanhas(sessao, usuario_id)


@roteador.get("/{campanha_id}/metricas", response_model=list[MetricaSaida])
def listar_metricas(
    campanha_id: int,
    inicio: date | None = None,
    fim: date | None = None,
    sessao: Session = Depends(obter_sessao),
    usuario_id: int = Depends(obter_usuario_atual),
):
    """Métricas diárias da campanha, com CTR (%) e CPC (R$) calculados pela view do banco."""
    return servico.listar_metricas(sessao, usuario_id, campanha_id, inicio, fim)


@roteador.post(
    "/{campanha_id}/metricas",
    response_model=IngestaoSaida,
    status_code=status.HTTP_201_CREATED,
)
def ingerir_metricas(
    campanha_id: int,
    entrada: LoteMetricasEntrada,
    sessao: Session = Depends(obter_sessao),
    usuario_id: int = Depends(obter_usuario_atual),
):
    """Grava métricas sintéticas (origem = 'sintetica'). O lote inteiro é aceito ou recusado."""
    inseridos = servico.ingerir_metricas_sinteticas(
        sessao, usuario_id, campanha_id, entrada.lote, entrada.registros
    )
    return IngestaoSaida(campanha_id=campanha_id, lote=entrada.lote, inseridos=inseridos)
