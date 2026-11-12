"""Eixos 'Regras e alertas' e 'Fronteiras e métricas' do plano de avaliação.

Cada caso da tabela congelada vira um teste. O teste passa quando o motor
produz exatamente o registro (aceito/rejeitado) e o resultado de cada regra
registrados como esperados.
"""

import pytest

from app.motor import avaliar, regras_padrao

from .tabela_congelada import carregar_cenarios, carregar_regras

CENARIOS = carregar_cenarios()
REGRAS_DA_TABELA = carregar_regras()


def test_tabela_tem_os_23_casos_registrados():
    assert len(CENARIOS) == 23
    assert len({c.id for c in CENARIOS}) == 23, "IDs de caso repetidos na tabela"


def test_regras_padrao_do_codigo_usam_os_limiares_da_tabela():
    """Garante que o código não divergiu dos limiares congelados."""
    assert regras_padrao() == REGRAS_DA_TABELA


@pytest.mark.parametrize("cenario", CENARIOS, ids=[c.id for c in CENARIOS])
def test_cenario_da_tabela(cenario):
    resultado = avaliar(cenario.registro, REGRAS_DA_TABELA)

    assert resultado.aceito == cenario.aceito_esperado, cenario.descricao
    observados = {regra_id: r.resultado for regra_id, r in resultado.regras.items()}
    assert observados == cenario.esperados, cenario.descricao
