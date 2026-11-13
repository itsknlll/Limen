"""Grava as métricas sintéticas nas campanhas reais sincronizadas (caso IN-02b).

Decisões:
- Sem atalho: cada registro passa por `validar_registro` (a mesma função que o
  esquema da API usa) e é gravado por `adicionar_metricas_sinteticas`, o mesmo
  código do POST /campanhas/{id}/metricas (sem o commit). Ela fixa
  origem='sintetica', e os CHECKs do banco continuam valendo.
- Tudo ou nada entre campanhas, em duas camadas: (1) antes de gravar, gera,
  valida e confere conflitos em todas as campanhas; (2) todas as campanhas são
  gravadas numa única transação, com um commit no final e rollback se qualquer
  gravação falhar. A camada 2 cobre o que a 1 não prevê (ex.: CHECK do banco).
- Idempotente: campanha que já tem o período completo com o mesmo lote é pulada.
  Período parcial ou dias de outro lote é conflito (409), e não mistura lotes em
  silêncio, como faria um ON CONFLICT DO NOTHING.
- Só campanhas que vieram da sincronização (sincronizada_em preenchido) e não
  removidas. Campanha pausada recebe métricas; quem decide se ela é avaliada é
  o serviço de avaliação (incluir_pausadas).
"""

from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...motor import RegistroMetricas, validar_registro
from ...modelos import MetricaDiaria
from ..campanhas import adicionar_metricas_sinteticas, listar_campanhas
from ..erros import ConflitoDados
from .gerador import DIAS_PADRAO, INICIO_PADRAO, SEMENTE_PADRAO, gerar_metricas, nome_lote


def _validar(google_campaign_id: int, gerados) -> None:
    for m in gerados:
        erros = validar_registro(RegistroMetricas(m.impressoes, m.cliques, m.custo, m.conversoes))
        if erros:
            # Erro do gerador, não do usuário: nada é gravado.
            raise ValueError(
                f"Registro sintético inválido (campanha {google_campaign_id}, {m.data}): "
                + "; ".join(erros)
            )


def _situacao(sessao: Session, campanha_id: int, datas: list[date], lote: str) -> str:
    """'vazia', 'completa' (mesmo lote em todos os dias) ou 'conflito'."""
    existentes = sessao.execute(
        select(MetricaDiaria.data, MetricaDiaria.lote).where(
            MetricaDiaria.campanha_id == campanha_id, MetricaDiaria.data.in_(datas)
        )
    ).all()
    if not existentes:
        return "vazia"
    if len(existentes) == len(datas) and all(l == lote for _, l in existentes):
        return "completa"
    return "conflito"


def semear_metricas_sinteticas(
    sessao: Session,
    usuario_id: int,
    semente: int = SEMENTE_PADRAO,
    inicio: date = INICIO_PADRAO,
    dias: int = DIAS_PADRAO,
) -> dict:
    lote = nome_lote(semente)
    campanhas = [
        c
        for c in listar_campanhas(sessao, usuario_id)
        if c.sincronizada_em is not None and c.status != "REMOVED"
    ]
    if not campanhas:
        raise ConflitoDados(
            "Nenhuma campanha sincronizada. Rode POST /campanhas/sincronizar antes (IN-02)."
        )

    datas = [inicio + timedelta(days=n) for n in range(dias)]
    planos = []
    conflitos = []
    for c in campanhas:
        gerados = gerar_metricas(c.google_campaign_id, semente, inicio, dias)
        _validar(c.google_campaign_id, gerados)
        situacao = _situacao(sessao, c.id, datas, lote)
        if situacao == "conflito":
            conflitos.append(str(c.google_campaign_id))
        planos.append((c, situacao, gerados))

    if conflitos:
        raise ConflitoDados(
            f"Campanhas com métricas de outro lote ou período incompleto entre "
            f"{datas[0].isoformat()} e {datas[-1].isoformat()}: {', '.join(conflitos)}"
        )

    resultado = []
    try:
        for c, situacao, gerados in planos:
            inseridos = 0
            if situacao == "vazia":
                inseridos = adicionar_metricas_sinteticas(sessao, usuario_id, c.id, lote, gerados)
            resultado.append(
                {
                    "campanha_id": c.id,
                    "google_campaign_id": c.google_campaign_id,
                    "nome": c.nome,
                    "status": c.status,
                    "inseridos": inseridos,
                    "ja_existentes": len(gerados) - inseridos,
                }
            )
        sessao.commit()  # único commit: todas as campanhas ou nenhuma
    except Exception:
        sessao.rollback()
        raise
    return {
        "lote": lote,
        "semente": semente,
        "inicio": datas[0],
        "fim": datas[-1],
        "campanhas": resultado,
    }
