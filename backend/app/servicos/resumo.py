"""Números da visão geral do dashboard, agregados no banco.

Decisão: agregar com GROUP BY em vez de devolver os alertas para o navegador
contar. A listagem de alertas tem limite (5.000) e a avaliação de desempenho
usa base de 10.000 registros; contar no cliente truncaria os números.

O período (inicio/fim) filtra métricas e alertas pela data do registro avaliado.
Campanhas, regras e última avaliação não dependem do período.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..modelos import (
    ORIGENS_METRICA,
    STATUS_CAMPANHA,
    Alerta,
    Campanha,
    ContaGoogleAds,
    MetricaDiaria,
    Regra,
)
from .avaliacao import listar_avaliacoes


def _no_periodo(consulta, inicio: date | None, fim: date | None):
    if inicio is not None:
        consulta = consulta.where(MetricaDiaria.data >= inicio)
    if fim is not None:
        consulta = consulta.where(MetricaDiaria.data <= fim)
    return consulta


def obter_resumo(
    sessao: Session, usuario_id: int, inicio: date | None = None, fim: date | None = None
) -> dict:
    # --- Campanhas por status (todos os status aparecem, mesmo com 0)
    por_status = dict.fromkeys(STATUS_CAMPANHA, 0)
    por_status.update(
        sessao.execute(
            select(Campanha.status, func.count())
            .join(Campanha.conta)
            .where(ContaGoogleAds.usuario_id == usuario_id)
            .group_by(Campanha.status)
        ).all()
    )

    # --- Regras
    total_regras, regras_ativas = sessao.execute(
        select(func.count(), func.count().filter(Regra.ativa)).where(Regra.usuario_id == usuario_id)
    ).one()

    # --- Métricas no período
    metricas_do_usuario = (
        select(MetricaDiaria)
        .join(MetricaDiaria.campanha)
        .join(Campanha.conta)
        .where(ContaGoogleAds.usuario_id == usuario_id)
    )
    base = _no_periodo(metricas_do_usuario, inicio, fim).subquery()
    registros, data_min, data_max = sessao.execute(
        select(func.count(), func.min(base.c.data), func.max(base.c.data))
    ).one()
    por_origem = dict.fromkeys(ORIGENS_METRICA, 0)
    por_origem.update(
        sessao.execute(select(base.c.origem, func.count()).group_by(base.c.origem)).all()
    )

    # --- Alertas por regra: LEFT JOIN para regras sem alerta aparecerem com 0.
    # O filtro de período fica dentro da subconsulta; no WHERE externo, ele
    # descartaria justamente as regras sem alerta.
    alertas_no_periodo = _no_periodo(
        select(Alerta.regra_id, func.count().label("total"))
        .join(MetricaDiaria, Alerta.metrica_diaria_id == MetricaDiaria.id)
        .group_by(Alerta.regra_id),
        inicio,
        fim,
    ).subquery()
    por_regra = [
        {"regra_id": id_, "codigo": codigo, "nome": nome, "ativa": ativa, "total": total}
        for id_, codigo, nome, ativa, total in sessao.execute(
            select(
                Regra.id,
                Regra.codigo,
                Regra.nome,
                Regra.ativa,
                func.coalesce(alertas_no_periodo.c.total, 0),
            )
            .outerjoin(alertas_no_periodo, alertas_no_periodo.c.regra_id == Regra.id)
            .where(Regra.usuario_id == usuario_id)
            .order_by(Regra.codigo)
        ).all()
    ]

    # --- Alertas por dia e regra (só os dias com alerta; o frontend preenche os vazios)
    por_dia: dict[date, dict[str, int]] = {}
    linhas = sessao.execute(
        _no_periodo(
            select(MetricaDiaria.data, Regra.codigo, func.count())
            .select_from(Alerta)
            .join(MetricaDiaria, Alerta.metrica_diaria_id == MetricaDiaria.id)
            .join(Regra, Alerta.regra_id == Regra.id)
            .where(Regra.usuario_id == usuario_id)
            .group_by(MetricaDiaria.data, Regra.codigo),
            inicio,
            fim,
        ).order_by(MetricaDiaria.data, Regra.codigo)
    ).all()
    for dia, codigo, total in linhas:
        por_dia.setdefault(dia, {})[codigo] = total

    ultimas = listar_avaliacoes(sessao, usuario_id, limite=1)

    return {
        "campanhas": {"total": sum(por_status.values()), "por_status": por_status},
        "regras": {"total": total_regras, "ativas": regras_ativas},
        "metricas": {
            "registros": registros,
            "inicio": data_min,
            "fim": data_max,
            "por_origem": por_origem,
        },
        "alertas": {
            "total": sum(r["total"] for r in por_regra),
            "por_regra": por_regra,
            "por_dia": [{"data": d, "por_regra": c} for d, c in por_dia.items()],
        },
        "ultima_avaliacao": ultimas[0] if ultimas else None,
    }
