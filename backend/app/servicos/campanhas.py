"""Campanhas e métricas diárias."""

from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..modelos import Campanha, ContaGoogleAds, MetricaDiaria, vw_metrica_diaria
from .erros import ConflitoDados, NaoEncontrado


def listar_campanhas(sessao: Session, usuario_id: int) -> list[Campanha]:
    return list(
        sessao.scalars(
            select(Campanha)
            .join(Campanha.conta)
            .where(ContaGoogleAds.usuario_id == usuario_id)
            .order_by(Campanha.nome)
        )
    )


def obter_campanha(sessao: Session, usuario_id: int, campanha_id: int) -> Campanha:
    campanha = sessao.scalar(
        select(Campanha)
        .join(Campanha.conta)
        .where(Campanha.id == campanha_id, ContaGoogleAds.usuario_id == usuario_id)
    )
    if campanha is None:
        raise NaoEncontrado("Campanha não encontrada")
    return campanha


def listar_metricas(
    sessao: Session, usuario_id: int, campanha_id: int, inicio: date | None, fim: date | None
) -> list[dict]:
    """Métricas lidas da view, que já traz CTR e CPC calculados."""
    obter_campanha(sessao, usuario_id, campanha_id)
    v = vw_metrica_diaria
    consulta = select(v).where(v.c.campanha_id == campanha_id)
    if inicio:
        consulta = consulta.where(v.c.data >= inicio)
    if fim:
        consulta = consulta.where(v.c.data <= fim)
    return [dict(linha) for linha in sessao.execute(consulta.order_by(v.c.data)).mappings()]


def ingerir_metricas_sinteticas(
    sessao: Session, usuario_id: int, campanha_id: int, lote: str | None, registros
) -> int:
    """Grava um lote de métricas sintéticas. Tudo ou nada: se um dia já existe, nada é gravado."""
    obter_campanha(sessao, usuario_id, campanha_id)
    datas = [r.data for r in registros]
    existentes = sorted(
        sessao.scalars(
            select(MetricaDiaria.data).where(
                MetricaDiaria.campanha_id == campanha_id, MetricaDiaria.data.in_(datas)
            )
        )
    )
    if existentes:
        lista = ", ".join(d.isoformat() for d in existentes)
        raise ConflitoDados(f"Já existem métricas desta campanha para: {lista}")

    sessao.add_all(
        MetricaDiaria(
            campanha_id=campanha_id,
            data=r.data,
            impressoes=r.impressoes,
            cliques=r.cliques,
            custo=r.custo,
            conversoes=r.conversoes,
            origem="sintetica",
            lote=lote,
        )
        for r in registros
    )
    try:
        sessao.commit()
    except IntegrityError as erro:
        sessao.rollback()
        raise ConflitoDados("Métricas conflitam com registros existentes") from erro
    return len(registros)
