"""Execução do motor sobre as métricas guardadas e registro dos alertas.

Fluxo: carrega regras ativas e métricas do banco -> converte para objetos do
motor -> avalia (tempo medido só aqui) -> grava alertas sem duplicar.

O tempo registrado em `duracao_motor_ms` cobre apenas a avaliação pelo motor,
sem consulta ao banco nem gravação. Assim o processamento local fica separado
de entrada/saída, como pede o plano de avaliação.
"""

from __future__ import annotations

import time
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from .. import motor
from ..modelos import Alerta, Avaliacao, Campanha, ContaGoogleAds, MetricaDiaria
from .regras import listar_regras, para_motor

TAMANHO_BLOCO = 1000  # alertas por INSERT, abaixo do limite de parâmetros do PostgreSQL


def _texto(valor: Decimal | None) -> str | None:
    return None if valor is None else str(valor)


def executar_avaliacao(
    sessao: Session,
    usuario_id: int,
    campanha_id: int | None = None,
    inicio: date | None = None,
    fim: date | None = None,
    incluir_pausadas: bool = False,
) -> Avaliacao:
    avaliacao = Avaliacao(usuario_id=usuario_id)
    sessao.add(avaliacao)
    sessao.flush()

    regras_banco = {r.codigo: r for r in listar_regras(sessao, usuario_id, apenas_ativas=True)}
    regras_motor = [para_motor(r) for r in regras_banco.values()]

    consulta = (
        select(MetricaDiaria)
        .join(MetricaDiaria.campanha)
        .join(Campanha.conta)
        .where(ContaGoogleAds.usuario_id == usuario_id)
    )
    # Decisão de projeto: campanha pausada não gasta, então por padrão não gera alerta.
    if not incluir_pausadas:
        consulta = consulta.where(Campanha.status == "ENABLED")
    if campanha_id is not None:
        consulta = consulta.where(MetricaDiaria.campanha_id == campanha_id)
    if inicio is not None:
        consulta = consulta.where(MetricaDiaria.data >= inicio)
    if fim is not None:
        consulta = consulta.where(MetricaDiaria.data <= fim)

    registros = [
        (m.id, motor.RegistroMetricas(m.impressoes, m.cliques, m.custo, m.conversoes))
        for m in sessao.scalars(consulta)
    ]

    inicio_motor = time.perf_counter()
    resultados = [(id_, motor.avaliar(registro, regras_motor)) for id_, registro in registros]
    duracao_ms = (time.perf_counter() - inicio_motor) * 1000

    rejeitados = 0
    linhas: list[dict] = []
    for metrica_id, resultado in resultados:
        if not resultado.aceito:
            rejeitados += 1
            continue
        for codigo in resultado.disparadas:
            regra = regras_banco[codigo]
            linhas.append(
                {
                    "avaliacao_id": avaliacao.id,
                    "regra_id": regra.id,
                    "metrica_diaria_id": metrica_id,
                    "valores_medidos": {
                        m.value: _texto(v) for m, v in resultado.regras[codigo].valores.items()
                    },
                    "condicoes": [
                        {"metrica": c.metrica, "operador": c.operador, "limiar": str(c.limiar)}
                        for c in regra.condicoes
                    ],
                }
            )

    # ON CONFLICT DO NOTHING: se o alerta (regra, registro) já existe, não duplica (IN-11).
    gerados = 0
    for i in range(0, len(linhas), TAMANHO_BLOCO):
        comando = (
            insert(Alerta)
            .values(linhas[i : i + TAMANHO_BLOCO])
            .on_conflict_do_nothing(constraint="uq_alerta_regra_metrica")
            .returning(Alerta.id)
        )
        gerados += len(sessao.execute(comando).all())

    avaliacao.registros_avaliados = len(registros)
    avaliacao.registros_rejeitados = rejeitados
    avaliacao.alertas_gerados = gerados
    avaliacao.alertas_ja_existentes = len(linhas) - gerados
    avaliacao.duracao_motor_ms = Decimal(f"{duracao_ms:.3f}")
    avaliacao.concluida_em = datetime.now(timezone.utc)
    sessao.commit()
    sessao.refresh(avaliacao)
    return avaliacao


def obter_avaliacao(sessao: Session, usuario_id: int, avaliacao_id: int) -> Avaliacao | None:
    return sessao.scalar(
        select(Avaliacao).where(Avaliacao.id == avaliacao_id, Avaliacao.usuario_id == usuario_id)
    )
