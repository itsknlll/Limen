"""Gerador de métricas sintéticas (IN-02b), sem banco e sem rede."""

import hashlib
from collections import Counter
from datetime import date, timedelta
from decimal import Decimal

import pytest

from app import motor
from app.servicos.sinteticas.gerador import (
    DIAS_PADRAO,
    INICIO_PADRAO,
    Perfil,
    gerar_metricas,
    nome_lote,
)

from .tabela_congelada import carregar_regras

# IDs reais das campanhas da conta de teste (sincronizadas no IN-02)
IDS_REAIS = (24444020070, 24464752468, 24458906837)

# Impressão digital do conjunto padrão (semente 20261112, 13/10 a 11/11/2026).
# Se mudar, os dados do IN-02b deixaram de ser os mesmos: gerar nova versão do lote.
HASH_CONJUNTO_PADRAO = "4359c3340978161a5a8e9123d37b68b24d7ac463894a8227ac8dfbf1bed780e4"

DISPARO_POR_PERFIL = {
    Perfil.NORMAL: set(),
    Perfil.CTR_BAIXO: {"R1"},
    Perfil.CPC_ALTO: {"R2"},
    Perfil.CUSTO_SEM_CONVERSAO: {"R3"},
}


def _registro(m) -> motor.RegistroMetricas:
    return motor.RegistroMetricas(m.impressoes, m.cliques, m.custo, m.conversoes)


def test_mesma_semente_gera_os_mesmos_dados():
    assert gerar_metricas(IDS_REAIS[0], semente=7) == gerar_metricas(IDS_REAIS[0], semente=7)


def test_semente_diferente_gera_dados_diferentes():
    assert gerar_metricas(IDS_REAIS[0], semente=7) != gerar_metricas(IDS_REAIS[0], semente=8)


def test_campanhas_diferentes_tem_dados_diferentes():
    assert gerar_metricas(IDS_REAIS[0]) != gerar_metricas(IDS_REAIS[1])


def test_hash_do_conjunto_padrao_nao_mudou():
    h = hashlib.sha256()
    for g in IDS_REAIS:
        for m in gerar_metricas(g):
            linha = (
                f"{g}|{m.data}|{m.impressoes}|{m.cliques}|{m.custo}|{m.conversoes}|{m.perfil.value}\n"
            )
            h.update(linha.encode())
    assert h.hexdigest() == HASH_CONJUNTO_PADRAO


def test_periodo_fixo_e_dias_seguidos():
    datas = [m.data for m in gerar_metricas(IDS_REAIS[0])]
    assert len(datas) == DIAS_PADRAO == 30
    assert datas[0] == INICIO_PADRAO == date(2026, 10, 13)
    assert datas[-1] == date(2026, 11, 11)
    assert datas == [INICIO_PADRAO + timedelta(days=n) for n in range(30)]


@pytest.mark.parametrize("google_id", IDS_REAIS)
def test_registros_validos_e_decimais(google_id):
    for m in gerar_metricas(google_id):
        assert motor.validar_registro(_registro(m)) == []
        assert type(m.impressoes) is int and type(m.cliques) is int
        assert type(m.custo) is Decimal and type(m.conversoes) is Decimal
        assert m.custo.as_tuple().exponent == -2  # exatamente 2 casas


@pytest.mark.parametrize("google_id", IDS_REAIS)
def test_quantidade_fixa_de_cada_perfil(google_id):
    contagem = Counter(m.perfil for m in gerar_metricas(google_id))
    assert contagem == {
        Perfil.NORMAL: 21,
        Perfil.CTR_BAIXO: 3,
        Perfil.CPC_ALTO: 3,
        Perfil.CUSTO_SEM_CONVERSAO: 3,
    }


@pytest.mark.parametrize("google_id", IDS_REAIS)
def test_cada_perfil_dispara_so_a_sua_regra(google_id):
    """Regras com os limiares lidos da tabela congelada, não do código."""
    regras = carregar_regras()
    for m in gerar_metricas(google_id):
        resultado = motor.avaliar(_registro(m), regras)
        assert resultado.aceito
        assert set(resultado.disparadas) == DISPARO_POR_PERFIL[m.perfil], (m.data, m.perfil)


def test_dias_insuficientes_para_as_anomalias():
    with pytest.raises(ValueError, match="pelo menos 9"):
        gerar_metricas(IDS_REAIS[0], dias=8)


def test_nome_do_lote_registra_a_semente():
    assert nome_lote() == "in02b-s20261112"
    assert nome_lote(7) == "in02b-s7"
