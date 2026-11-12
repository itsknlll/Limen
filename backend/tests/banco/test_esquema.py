"""Testes do esquema relacional.

- A view calcula CTR e CPC exatamente como o motor (caso IN-07: "CTR e CPC no
  banco iguais aos da aba Cenários de regras"), usando os casos da tabela.
- O banco recusa sozinho os registros que a tabela marca como rejeitados
  (defesa em profundidade, além da validação do backend).
- Restrições de unicidade: um registro por campanha e dia; um alerta por regra
  e registro (base da não duplicação, caso IN-11).
"""

from datetime import date, timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.motor import calcular_cpc, calcular_ctr

from ..tabela_congelada import carregar_cenarios

CENARIOS = carregar_cenarios()
VALIDOS = [c for c in CENARIOS if c.aceito_esperado]
REJEITADOS = [c for c in CENARIOS if not c.aceito_esperado]
DIA_INICIAL = date(2026, 11, 1)


def criar_campanha(con) -> int:
    usuario = con.execute(
        text("INSERT INTO usuario (email, nome) VALUES ('teste@limen.dev', 'Teste') RETURNING id")
    ).scalar_one()
    conta = con.execute(
        text(
            "INSERT INTO conta_google_ads (usuario_id, customer_id, nome) "
            "VALUES (:u, '4327030343', 'Limen Cliente Teste') RETURNING id"
        ),
        {"u": usuario},
    ).scalar_one()
    return con.execute(
        text(
            "INSERT INTO campanha (conta_id, google_campaign_id, nome, status) "
            "VALUES (:c, 24444020070, 'Limen A - Pesquisa', 'ENABLED') RETURNING id"
        ),
        {"c": conta},
    ).scalar_one()


def inserir_metrica(con, campanha_id: int, dia: date, registro) -> int:
    return con.execute(
        text(
            "INSERT INTO metrica_diaria "
            "(campanha_id, data, impressoes, cliques, custo, conversoes, origem, lote) "
            "VALUES (:c, :d, :i, :k, :custo, :conv, 'sintetica', 'tabela-v1.0') RETURNING id"
        ),
        {
            "c": campanha_id,
            "d": dia,
            "i": registro.impressoes,
            "k": registro.cliques,
            "custo": registro.custo,
            "conv": registro.conversoes,
        },
    ).scalar_one()


def test_view_calcula_ctr_e_cpc_igual_ao_motor(conexao):
    campanha = criar_campanha(conexao)
    for n, cenario in enumerate(VALIDOS):
        id_ = inserir_metrica(conexao, campanha, DIA_INICIAL + timedelta(days=n), cenario.registro)
        ctr, cpc = conexao.execute(
            text("SELECT ctr, cpc FROM vw_metrica_diaria WHERE id = :id"), {"id": id_}
        ).one()
        assert ctr == calcular_ctr(cenario.registro), f"{cenario.id}: CTR"
        assert cpc == calcular_cpc(cenario.registro), f"{cenario.id}: CPC"


@pytest.mark.parametrize("cenario", REJEITADOS, ids=[c.id for c in REJEITADOS])
def test_banco_recusa_registro_invalido(conexao, cenario):
    campanha = criar_campanha(conexao)
    with pytest.raises(IntegrityError):
        with conexao.begin_nested():
            inserir_metrica(conexao, campanha, DIA_INICIAL, cenario.registro)


def test_um_registro_por_campanha_e_dia(conexao):
    campanha = criar_campanha(conexao)
    inserir_metrica(conexao, campanha, DIA_INICIAL, VALIDOS[0].registro)
    with pytest.raises(IntegrityError):
        with conexao.begin_nested():
            inserir_metrica(conexao, campanha, DIA_INICIAL, VALIDOS[1].registro)


def test_um_alerta_por_regra_e_registro(conexao):
    campanha = criar_campanha(conexao)
    metrica = inserir_metrica(conexao, campanha, DIA_INICIAL, VALIDOS[0].registro)
    usuario = conexao.execute(text("SELECT id FROM usuario LIMIT 1")).scalar_one()
    regra = conexao.execute(
        text("INSERT INTO regra (usuario_id, codigo, nome) VALUES (:u, 'R1', 'CTR baixo') RETURNING id"),
        {"u": usuario},
    ).scalar_one()
    avaliacao = conexao.execute(
        text("INSERT INTO avaliacao (usuario_id) VALUES (:u) RETURNING id"), {"u": usuario}
    ).scalar_one()

    inserir_alerta = text(
        "INSERT INTO alerta (avaliacao_id, regra_id, metrica_diaria_id, valores_medidos, condicoes) "
        "VALUES (:a, :r, :m, '{}'::jsonb, '[]'::jsonb)"
    )
    parametros = {"a": avaliacao, "r": regra, "m": metrica}
    conexao.execute(inserir_alerta, parametros)
    with pytest.raises(IntegrityError):
        with conexao.begin_nested():
            conexao.execute(inserir_alerta, parametros)


@pytest.mark.parametrize(
    "metrica, operador, limiar",
    [("roi", "<", 1), ("ctr", "=", 1), ("ctr", "<", -1)],
    ids=["metrica_inexistente", "operador_invalido", "limiar_negativo"],
)
def test_banco_recusa_condicao_invalida(conexao, metrica, operador, limiar):
    criar_campanha(conexao)
    usuario = conexao.execute(text("SELECT id FROM usuario LIMIT 1")).scalar_one()
    regra = conexao.execute(
        text("INSERT INTO regra (usuario_id, codigo, nome) VALUES (:u, 'RX', 'teste') RETURNING id"),
        {"u": usuario},
    ).scalar_one()
    with pytest.raises(IntegrityError):
        with conexao.begin_nested():
            conexao.execute(
                text(
                    "INSERT INTO condicao (regra_id, ordem, metrica, operador, limiar) "
                    "VALUES (:r, 1, :m, :o, :l)"
                ),
                {"r": regra, "m": metrica, "o": operador, "l": limiar},
            )
