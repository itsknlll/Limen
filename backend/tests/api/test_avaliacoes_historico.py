"""Parâmetros gravados em cada avaliação (migração 0003) e GET /avaliacoes."""

from datetime import date

import pytest
from sqlalchemy.exc import IntegrityError

from app.modelos import Avaliacao, Usuario
from app.servicos.regras import criar_regras_padrao


@pytest.fixture
def com_regras(sessao_teste, usuario_teste, campanhas_teste):
    criar_regras_padrao(sessao_teste, usuario_teste)
    sessao_teste.commit()
    return campanhas_teste


def test_post_grava_os_parametros_da_execucao(cliente, com_regras):
    entrada = {
        "incluir_pausadas": True,
        "campanha_id": com_regras["C"],
        "inicio": "2026-10-13",
        "fim": "2026-11-11",
    }
    criada = cliente.post("/avaliacoes", json=entrada).json()
    for chave, valor in entrada.items():
        assert criada[chave] == valor

    lida = cliente.get(f"/avaliacoes/{criada['id']}").json()
    assert {k: lida[k] for k in entrada} == entrada


def test_post_sem_corpo_grava_padrao_false_e_filtros_nulos(cliente, com_regras):
    criada = cliente.post("/avaliacoes", json={}).json()
    assert criada["incluir_pausadas"] is False  # foi registrado: o padrão é não incluir
    assert (criada["campanha_id"], criada["inicio"], criada["fim"]) == (None, None, None)


def test_avaliacao_anterior_a_0003_tem_parametros_nulos(cliente, sessao_teste, usuario_teste):
    """Como as duas avaliações reais do IN-02b: NULL = não registrado, e não false."""
    antiga = Avaliacao(usuario_id=usuario_teste)
    sessao_teste.add(antiga)
    sessao_teste.commit()

    lida = cliente.get(f"/avaliacoes/{antiga.id}").json()
    assert lida["incluir_pausadas"] is None
    assert (lida["campanha_id"], lida["inicio"], lida["fim"]) == (None, None, None)


def test_historico_da_mais_recente_para_a_mais_antiga(cliente, com_regras):
    ids = [cliente.post("/avaliacoes", json={}).json()["id"] for _ in range(3)]
    historico = cliente.get("/avaliacoes").json()
    assert [a["id"] for a in historico] == list(reversed(ids))


def test_historico_respeita_o_limite(cliente, com_regras):
    ids = [cliente.post("/avaliacoes", json={}).json()["id"] for _ in range(3)]
    historico = cliente.get("/avaliacoes", params={"limite": 2}).json()
    assert [a["id"] for a in historico] == [ids[2], ids[1]]


@pytest.mark.parametrize("limite", [0, 501, "abc"])
def test_limite_invalido_e_400(cliente, limite):
    resposta = cliente.get("/avaliacoes", params={"limite": limite})
    assert resposta.status_code == 400
    assert resposta.json()["tipo"] == "validacao"


def test_historico_so_do_usuario(cliente, sessao_teste, com_regras):
    outro = Usuario(email="outro@limen.dev")
    sessao_teste.add(outro)
    sessao_teste.flush()
    sessao_teste.add(Avaliacao(usuario_id=outro.id))
    sessao_teste.commit()

    minha = cliente.post("/avaliacoes", json={}).json()
    assert [a["id"] for a in cliente.get("/avaliacoes").json()] == [minha["id"]]


def test_historico_vazio(cliente):
    assert cliente.get("/avaliacoes").json() == []


def test_historico_exige_login(cliente_sem_login):
    resposta = cliente_sem_login.get("/avaliacoes")
    assert resposta.status_code == 401


def test_banco_recusa_periodo_invertido(sessao_teste, usuario_teste):
    """CHECK ck_avaliacao_periodo: a última barreira, sem passar pela API."""
    sessao_teste.add(
        Avaliacao(usuario_id=usuario_teste, inicio=date(2026, 11, 11), fim=date(2026, 10, 13))
    )
    with pytest.raises(IntegrityError, match="ck_avaliacao_periodo"):
        sessao_teste.flush()
    sessao_teste.rollback()
