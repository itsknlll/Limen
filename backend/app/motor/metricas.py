"""Métricas de campanha e seus cálculos.

Decisões registradas na tabela congelada (commit 29de91d):
- Precisão: valores monetários e razões usam Decimal, nunca ponto flutuante.
  A comparação usa o valor calculado sem arredondamento.
- Ausência vs. zero: métrica ausente (None) é diferente de zero. Uma razão
  com denominador ausente ou igual a zero é indefinida (None), e nunca é
  interpretada como zero.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum

CEM = Decimal(100)


class Metrica(str, Enum):
    """Métricas que uma condição de regra pode usar."""

    IMPRESSOES = "impressoes"
    CLIQUES = "cliques"
    CUSTO = "custo"
    CONVERSOES = "conversoes"
    CTR = "ctr"  # em porcentagem: cliques ÷ impressões × 100
    CPC = "cpc"  # em reais: custo ÷ cliques


@dataclass(frozen=True)
class RegistroMetricas:
    """Métricas de uma campanha em um dia (unidade de avaliação do motor).

    Qualquer campo pode ser None, o que representa dado ausente.
    Conversões são Decimal porque o Google Ads admite conversões fracionárias.
    """

    impressoes: int | None
    cliques: int | None
    custo: Decimal | None
    conversoes: Decimal | None


def calcular_ctr(registro: RegistroMetricas) -> Decimal | None:
    """CTR em porcentagem. Indefinido sem impressões ou cliques, ou com 0 impressões."""
    if registro.impressoes is None or registro.cliques is None:
        return None
    if registro.impressoes == 0:
        return None
    return Decimal(registro.cliques) * CEM / Decimal(registro.impressoes)


def calcular_cpc(registro: RegistroMetricas) -> Decimal | None:
    """CPC em reais. Indefinido sem custo ou cliques, ou com 0 cliques."""
    if registro.custo is None or registro.cliques is None:
        return None
    if registro.cliques == 0:
        return None
    return registro.custo / Decimal(registro.cliques)


def valor_da_metrica(registro: RegistroMetricas, metrica: Metrica) -> Decimal | None:
    """Valor de uma métrica no registro, ou None quando ausente ou indefinida."""
    if metrica is Metrica.CTR:
        return calcular_ctr(registro)
    if metrica is Metrica.CPC:
        return calcular_cpc(registro)
    bruto = {
        Metrica.IMPRESSOES: registro.impressoes,
        Metrica.CLIQUES: registro.cliques,
        Metrica.CUSTO: registro.custo,
        Metrica.CONVERSOES: registro.conversoes,
    }[metrica]
    return None if bruto is None else Decimal(bruto)
