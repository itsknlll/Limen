"""Consulta de alertas, já com campanha, regra e data do registro avaliado."""

from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..modelos import Alerta, Campanha, MetricaDiaria, Regra


def listar_alertas(
    sessao: Session,
    usuario_id: int,
    campanha_id: int | None = None,
    regra_id: int | None = None,
    inicio: date | None = None,
    fim: date | None = None,
    limite: int = 500,
) -> list[dict]:
    consulta = (
        select(
            Alerta.id,
            Alerta.criado_em,
            Alerta.avaliacao_id,
            Alerta.valores_medidos,
            Alerta.condicoes,
            MetricaDiaria.data,
            MetricaDiaria.origem,
            Campanha.id.label("campanha_id"),
            Campanha.nome.label("campanha_nome"),
            Regra.id.label("regra_id"),
            Regra.codigo.label("regra_codigo"),
            Regra.nome.label("regra_nome"),
        )
        .join(MetricaDiaria, Alerta.metrica_diaria_id == MetricaDiaria.id)
        .join(Campanha, MetricaDiaria.campanha_id == Campanha.id)
        .join(Regra, Alerta.regra_id == Regra.id)
        .where(Regra.usuario_id == usuario_id)
    )
    if campanha_id is not None:
        consulta = consulta.where(Campanha.id == campanha_id)
    if regra_id is not None:
        consulta = consulta.where(Regra.id == regra_id)
    if inicio is not None:
        consulta = consulta.where(MetricaDiaria.data >= inicio)
    if fim is not None:
        consulta = consulta.where(MetricaDiaria.data <= fim)
    consulta = consulta.order_by(MetricaDiaria.data.desc(), Regra.codigo).limit(limite)
    return [dict(linha) for linha in sessao.execute(consulta).mappings()]
