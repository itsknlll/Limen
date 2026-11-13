"""Gerador reproduzível de métricas sintéticas (caso IN-02b).

Contas de teste do Google Ads não veiculam anúncios, então as métricas são
sintéticas, associadas às campanhas reais sincronizadas e marcadas como tal.

Decisões:
- Função pura: sem banco, sem rede, sem relógio. Mesmos argumentos, mesma saída.
- Um gerador por campanha, semeado com "semente:google_campaign_id". Incluir ou
  remover uma campanha não altera os dados das outras.
- Só `rng.random()` é usado. A documentação do Python garante que essa sequência
  não muda entre versões; `randint`, `choice` e `shuffle` não têm essa garantia.
  Por isso o sorteio de inteiros e o embaralhamento estão implementados aqui.
- Nenhum float chega aos dados: sorteiam-se inteiros (impressões, pontos-base de
  CTR, centavos de CPC) e o custo vira Decimal com exatamente 2 casas.
- Cada dia recebe um perfil. A quantidade de cada perfil é fixa (o sorteio só
  decide em que dias caem), então o número de alertas esperado é conhecido.
  As faixas de cada perfil ficam longe dos limiares da tabela congelada
  (R1: CTR < 1%; R2: CPC > R$ 5,00; R3: custo > R$ 100,00 com 0 conversões),
  de modo que cada perfil dispara só a sua regra.
- O orçamento diário da campanha é ignorado (decisão registrada): os dados são
  declaradamente sintéticos e o teto de gasto não faz parte da tabela.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from enum import Enum

SEMENTE_PADRAO = 20261112  # data do congelamento da tabela
INICIO_PADRAO = date(2026, 10, 13)
DIAS_PADRAO = 30  # 13/10/2026 a 11/11/2026, véspera da sincronização real
DIAS_POR_ANOMALIA = 3


class Perfil(str, Enum):
    NORMAL = "normal"
    CTR_BAIXO = "ctr_baixo"  # dispara R1
    CPC_ALTO = "cpc_alto"  # dispara R2
    CUSTO_SEM_CONVERSAO = "custo_sem_conversao"  # dispara R3


@dataclass(frozen=True)
class _Faixas:
    impressoes: tuple[int, int]
    ctr_pontos_base: tuple[int, int]  # 100 pontos-base = 1%
    cpc_centavos: tuple[int, int]
    conversoes: tuple[int, int]


_FAIXAS: dict[Perfil, _Faixas] = {
    # CTR >= ~2%, CPC <= R$ 3,00, conversões >= 1: nenhuma regra
    Perfil.NORMAL: _Faixas((3000, 10000), (200, 600), (50, 300), (1, 10)),
    # CTR <= 0,8% (< 1%): só R1. Cliques >= 3000 x 0,2% = 6, então CPC é definido.
    Perfil.CTR_BAIXO: _Faixas((3000, 10000), (20, 80), (50, 300), (1, 10)),
    # CPC >= R$ 6,00 (> R$ 5,00): só R2
    Perfil.CPC_ALTO: _Faixas((3000, 10000), (200, 600), (600, 1200), (1, 10)),
    # Cliques >= 5000 x 2% = 100 e CPC >= R$ 1,50: custo >= R$ 150,00, 0 conversões: só R3
    Perfil.CUSTO_SEM_CONVERSAO: _Faixas((5000, 10000), (200, 600), (150, 300), (0, 0)),
}


@dataclass(frozen=True)
class MetricaGerada:
    data: date
    impressoes: int
    cliques: int
    custo: Decimal
    conversoes: Decimal
    perfil: Perfil


def nome_lote(semente: int = SEMENTE_PADRAO) -> str:
    return f"in02b-s{semente}"


def _inteiro(rng: random.Random, minimo: int, maximo: int) -> int:
    """Inteiro uniforme em [minimo, maximo], usando só rng.random()."""
    return minimo + int(rng.random() * (maximo - minimo + 1))


def _embaralhar(rng: random.Random, itens: list) -> None:
    """Fisher-Yates usando só rng.random()."""
    for i in range(len(itens) - 1, 0, -1):
        j = _inteiro(rng, 0, i)
        itens[i], itens[j] = itens[j], itens[i]


def _sortear_dia(rng: random.Random, dia: date, perfil: Perfil) -> MetricaGerada:
    faixas = _FAIXAS[perfil]
    impressoes = _inteiro(rng, *faixas.impressoes)
    cliques = impressoes * _inteiro(rng, *faixas.ctr_pontos_base) // 10000
    custo_centavos = cliques * _inteiro(rng, *faixas.cpc_centavos)
    return MetricaGerada(
        data=dia,
        impressoes=impressoes,
        cliques=cliques,
        custo=Decimal(custo_centavos).scaleb(-2),  # exatamente 2 casas, sem float
        conversoes=Decimal(_inteiro(rng, *faixas.conversoes)),
        perfil=perfil,
    )


def gerar_metricas(
    google_campaign_id: int,
    semente: int = SEMENTE_PADRAO,
    inicio: date = INICIO_PADRAO,
    dias: int = DIAS_PADRAO,
) -> list[MetricaGerada]:
    """Métricas diárias de uma campanha, de `inicio` em diante, por `dias` dias seguidos."""
    anomalias = [Perfil.CTR_BAIXO, Perfil.CPC_ALTO, Perfil.CUSTO_SEM_CONVERSAO]
    minimo = DIAS_POR_ANOMALIA * len(anomalias)
    if dias < minimo:
        raise ValueError(f"dias deve ser pelo menos {minimo} (recebido: {dias})")

    rng = random.Random(f"{semente}:{google_campaign_id}")
    perfis = [p for p in anomalias for _ in range(DIAS_POR_ANOMALIA)]
    perfis += [Perfil.NORMAL] * (dias - minimo)
    _embaralhar(rng, perfis)

    return [_sortear_dia(rng, inicio + timedelta(days=n), p) for n, p in enumerate(perfis)]
