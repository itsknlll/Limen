"""Testes de unidade do motor, complementares aos casos da tabela.

Cobrem comportamentos que a tabela não exercita diretamente: precisão
decimal, operadores não usados pelas regras padrão, regras inválidas e
independência da ordem das condições.
"""

from decimal import Decimal

import pytest

from app.motor import (
    Condicao,
    Metrica,
    Operador,
    Regra,
    RegistroMetricas,
    Resultado,
    avaliar,
    avaliar_regra,
    calcular_cpc,
    calcular_ctr,
)


def registro(impressoes=1000, cliques=10, custo="20.00", conversoes="1"):
    return RegistroMetricas(
        impressoes=impressoes,
        cliques=cliques,
        custo=None if custo is None else Decimal(custo),
        conversoes=None if conversoes is None else Decimal(conversoes),
    )


# --- Métricas -------------------------------------------------------------

def test_ctr_em_porcentagem_e_exato():
    assert calcular_ctr(registro(impressoes=10000, cliques=99)) == Decimal("0.99")


def test_ctr_indefinido_com_zero_impressoes():
    assert calcular_ctr(registro(impressoes=0, cliques=0)) is None


def test_cpc_sem_erro_de_ponto_flutuante():
    # Em float, 0.1 + 0.2 != 0.3; com Decimal o CPC fica exato.
    assert calcular_cpc(registro(cliques=3, custo="0.30")) == Decimal("0.1")


def test_cpc_indefinido_com_zero_cliques():
    assert calcular_cpc(registro(cliques=0)) is None


def test_ausente_e_diferente_de_zero():
    zero = registro(conversoes="0")
    ausente = registro(conversoes=None)
    regra = Regra("X", "conv zero", (Condicao(Metrica.CONVERSOES, Operador.IGUAL, Decimal("0")),))
    assert avaliar_regra(zero, regra).resultado is Resultado.DISPARA
    assert avaliar_regra(ausente, regra).resultado is Resultado.NAO_AVALIAVEL


# --- Operadores -----------------------------------------------------------

@pytest.mark.parametrize(
    "operador, valor, esperado",
    [
        (Operador.MENOR, "4.99", True),
        (Operador.MENOR, "5.00", False),
        (Operador.MENOR_OU_IGUAL, "5.00", True),
        (Operador.MAIOR, "5.00", False),
        (Operador.MAIOR_OU_IGUAL, "5.00", True),
        (Operador.IGUAL, "5.00", True),
        (Operador.IGUAL, "5.0", True),  # Decimal compara valor, não representação
    ],
)
def test_operadores(operador, valor, esperado):
    assert operador.aplicar(Decimal(valor), Decimal("5.00")) is esperado


# --- Regras ---------------------------------------------------------------

def test_regra_sem_condicoes_e_invalida():
    with pytest.raises(ValueError):
        Regra("X", "vazia", ())


def test_limiar_negativo_e_invalido():
    with pytest.raises(ValueError):
        Condicao(Metrica.CPC, Operador.MAIOR, Decimal("-1"))


def test_limiar_float_e_recusado():
    with pytest.raises(TypeError):
        Condicao(Metrica.CPC, Operador.MAIOR, 5.0)  # type: ignore[arg-type]


def test_ids_de_regra_repetidos_sao_recusados():
    c = (Condicao(Metrica.CPC, Operador.MAIOR, Decimal("5")),)
    with pytest.raises(ValueError):
        avaliar(registro(), [Regra("R1", "a", c), Regra("R1", "b", c)])


def test_resultado_nao_depende_da_ordem_das_condicoes():
    # custo baixo (condição falsa) + conversões ausentes: N/A nas duas ordens
    r = registro(custo="50.00", conversoes=None)
    custo = Condicao(Metrica.CUSTO, Operador.MAIOR, Decimal("100"))
    conv = Condicao(Metrica.CONVERSOES, Operador.IGUAL, Decimal("0"))
    a = avaliar_regra(r, Regra("A", "a", (custo, conv)))
    b = avaliar_regra(r, Regra("B", "b", (conv, custo)))
    assert a.resultado is b.resultado is Resultado.NAO_AVALIAVEL


def test_regra_configurada_sem_alterar_codigo():
    """Uma regra nova (CTR <= 2%) funciona só por configuração."""
    nova = Regra("R9", "CTR até 2%", (Condicao(Metrica.CTR, Operador.MENOR_OU_IGUAL, Decimal("2")),))
    assert avaliar_regra(registro(impressoes=1000, cliques=20), nova).resultado is Resultado.DISPARA


def test_alerta_traz_o_valor_medido():
    r1 = Regra("R1", "CTR baixo", (Condicao(Metrica.CTR, Operador.MENOR, Decimal("1")),))
    res = avaliar_regra(registro(impressoes=10000, cliques=50), r1)
    assert res.resultado is Resultado.DISPARA
    assert res.valores[Metrica.CTR] == Decimal("0.5")


def test_registro_rejeitado_traz_mensagens_de_erro():
    res = avaliar(registro(impressoes=100, cliques=150), [])
    assert res.aceito is False
    assert any("cliques" in e for e in res.erros)
