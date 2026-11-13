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


def adicionar_metricas_sinteticas(
    sessao: Session, usuario_id: int, campanha_id: int, lote: str | None, registros
) -> int:
    """Adiciona métricas sintéticas à transação corrente, SEM commit.

    Quem chama decide a transação: a ingestão pela API grava um lote por vez;
    o semeador do IN-02b grava várias campanhas e faz um único commit no final.
    O flush aciona os CHECKs e UNIQUEs do banco aqui mesmo, então uma violação
    aparece nesta chamada (como ConflitoDados) e não só no commit.
    """
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
        sessao.flush()
    except IntegrityError as erro:
        raise ConflitoDados("Métricas conflitam com registros existentes") from erro
    return len(registros)


def ingerir_metricas_sinteticas(
    sessao: Session, usuario_id: int, campanha_id: int, lote: str | None, registros
) -> int:
    """Grava um lote de métricas sintéticas. Tudo ou nada: se um dia já existe, nada é gravado."""
    try:
        inseridos = adicionar_metricas_sinteticas(sessao, usuario_id, campanha_id, lote, registros)
        sessao.commit()
    except IntegrityError as erro:
        sessao.rollback()
        raise ConflitoDados("Métricas conflitam com registros existentes") from erro
    except Exception:
        sessao.rollback()
        raise
    return inseridos
