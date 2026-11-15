"""Testes da API REST: casos IN-07 a IN-11 da tabela congelada e comportamentos de apoio."""

from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.motor import calcular_cpc, calcular_ctr
from app.servicos.regras import criar_regras_padrao

from ..tabela_congelada import carregar_cenarios

CENARIOS = {c.id: c for c in carregar_cenarios()}
VALIDOS = [c for c in CENARIOS.values() if c.aceito_esperado]
REJEITADOS = [c for c in CENARIOS.values() if not c.aceito_esperado]
DIA = date(2026, 11, 1)


def json_registro(registro, dia: date) -> dict:
    texto = lambda v: None if v is None else str(v)  # noqa: E731
    return {
        "data": dia.isoformat(),
        "impressoes": registro.impressoes,
        "cliques": registro.cliques,
        "custo": texto(registro.custo),
        "conversoes": texto(registro.conversoes),
    }


def dec(valor) -> Decimal | None:
    return None if valor is None else Decimal(str(valor))


def ingerir(cliente, campanha_id, cenarios, dia_inicial=DIA, lote="tabela-v1.0"):
    corpo = {
        "lote": lote,
        "registros": [
            json_registro(c.registro, dia_inicial + timedelta(days=n)) for n, c in enumerate(cenarios)
        ],
    }
    return cliente.post(f"/campanhas/{campanha_id}/metricas", json=corpo)


# --- IN-07: ingestão de métricas sintéticas --------------------------------

def test_in07_ingestao_persiste_e_ctr_cpc_batem_com_o_motor(cliente, campanhas_teste):
    campanha = campanhas_teste["A"]
    resposta = ingerir(cliente, campanha, VALIDOS)
    assert resposta.status_code == 201, resposta.text
    assert resposta.json()["inseridos"] == len(VALIDOS)

    metricas = cliente.get(f"/campanhas/{campanha}/metricas").json()
    assert len(metricas) == len(VALIDOS)
    for cenario, linha in zip(VALIDOS, metricas):
        assert linha["origem"] == "sintetica" and linha["lote"] == "tabela-v1.0"
        assert dec(linha["ctr"]) == calcular_ctr(cenario.registro), cenario.id
        assert dec(linha["cpc"]) == calcular_cpc(cenario.registro), cenario.id


@pytest.mark.parametrize("cenario", REJEITADOS, ids=[c.id for c in REJEITADOS])
def test_ingestao_recusa_registro_invalido_sem_gravar_nada(cliente, campanhas_teste, cenario):
    campanha = campanhas_teste["A"]
    # Um registro válido junto do inválido: o lote inteiro deve ser recusado.
    resposta = ingerir(cliente, campanha, [VALIDOS[0], cenario])
    assert resposta.status_code == 400
    assert cliente.get(f"/campanhas/{campanha}/metricas").json() == []


def test_ingestao_de_dia_repetido_e_conflito(cliente, campanhas_teste):
    campanha = campanhas_teste["A"]
    assert ingerir(cliente, campanha, [VALIDOS[0]]).status_code == 201
    resposta = ingerir(cliente, campanha, [VALIDOS[1]])  # mesmo dia
    assert resposta.status_code == 409
    assert len(cliente.get(f"/campanhas/{campanha}/metricas").json()) == 1


# --- IN-08 e IN-09: regras --------------------------------------------------

def test_in08_regra_criada_e_usada_na_proxima_avaliacao(cliente, campanhas_teste):
    resposta = cliente.post(
        "/regras",
        json={
            "codigo": "R9",
            "nome": "CPC acima de R$ 7",
            "condicoes": [{"metrica": "cpc", "operador": ">", "limiar": "7"}],
        },
    )
    assert resposta.status_code == 201, resposta.text
    regra = resposta.json()
    assert regra["codigo"] == "R9" and len(regra["condicoes"]) == 1

    campanha = campanhas_teste["A"]
    # RA-03 tem CPC de R$ 8,00 (dispara); RA-01 tem CPC de R$ 2,00 (não dispara)
    ingerir(cliente, campanha, [CENARIOS["RA-03"], CENARIOS["RA-01"]])
    assert cliente.post("/avaliacoes", json={}).status_code == 201

    alertas = cliente.get("/alertas").json()
    assert [(a["regra_codigo"], a["data"]) for a in alertas] == [("R9", DIA.isoformat())]


@pytest.mark.parametrize(
    "limiar", ["-1", None, ""], ids=["negativo", "nulo", "vazio"]
)
def test_in09_regra_com_limiar_invalido_e_recusada(cliente, limiar):
    resposta = cliente.post(
        "/regras",
        json={
            "codigo": "RX",
            "nome": "inválida",
            "condicoes": [{"metrica": "ctr", "operador": "<", "limiar": limiar}],
        },
    )
    assert resposta.status_code == 400
    assert cliente.get("/regras").json() == []


def test_codigo_de_regra_repetido_e_conflito(cliente):
    corpo = {"codigo": "R9", "nome": "a", "condicoes": [{"metrica": "cpc", "operador": ">", "limiar": "7"}]}
    assert cliente.post("/regras", json=corpo).status_code == 201
    assert cliente.post("/regras", json=corpo).status_code == 409


def test_regra_desativada_nao_gera_alerta(cliente, campanhas_teste):
    # Fase 3: R1 a R3 não podem ser desativadas (409 regra_referencia). Uma regra do
    # usuário com a mesma condição da R1 (CTR < 1%) faz o papel que a R1 fazia aqui.
    r9 = cliente.post(
        "/regras",
        json={"codigo": "R9", "nome": "CTR baixo", "condicoes": [{"metrica": "ctr", "operador": "<", "limiar": "1"}]},
    ).json()
    assert cliente.delete(f"/regras/{r9['id']}").status_code == 204

    ingerir(cliente, campanhas_teste["A"], [CENARIOS["RA-02"]])  # só viola R1
    avaliacao = cliente.post("/avaliacoes", json={}).json()
    assert avaliacao["alertas_gerados"] == 0


def test_atualizar_regra_troca_as_condicoes(cliente):
    criada = cliente.post(
        "/regras",
        json={"codigo": "R9", "nome": "a", "condicoes": [{"metrica": "cpc", "operador": ">", "limiar": "7"}]},
    ).json()
    resposta = cliente.put(
        f"/regras/{criada['id']}",
        json={
            "codigo": "R9",
            "nome": "CPC alto e CTR baixo",
            "condicoes": [
                {"metrica": "cpc", "operador": ">", "limiar": "6"},
                {"metrica": "ctr", "operador": "<", "limiar": "2"},
            ],
        },
    )
    assert resposta.status_code == 200, resposta.text
    condicoes = resposta.json()["condicoes"]
    assert [(c["ordem"], c["metrica"]) for c in condicoes] == [(1, "cpc"), (2, "ctr")]


# --- IN-10 e IN-11: alertas -------------------------------------------------

def test_in10_alerta_traz_campanha_regra_valor_e_data(cliente, sessao_teste, usuario_teste, campanhas_teste):
    criar_regras_padrao(sessao_teste, usuario_teste)
    ingerir(cliente, campanhas_teste["A"], [CENARIOS["RA-02"]])  # CTR 0,50%
    cliente.post("/avaliacoes", json={})

    alertas = cliente.get("/alertas").json()
    assert len(alertas) == 1
    alerta = alertas[0]
    assert alerta["campanha_nome"] == "Limen A - Pesquisa"
    assert alerta["regra_codigo"] == "R1"
    assert dec(alerta["valores_medidos"]["ctr"]) == Decimal("0.5")
    assert alerta["data"] == DIA.isoformat()
    assert alerta["origem"] == "sintetica"
    assert alerta["condicoes"][0]["operador"] == "<"


def test_in11_reavaliar_sem_mudanca_nao_duplica_alertas(cliente, sessao_teste, usuario_teste, campanhas_teste):
    criar_regras_padrao(sessao_teste, usuario_teste)
    ingerir(cliente, campanhas_teste["A"], [CENARIOS["RA-02"], CENARIOS["RA-05"]])

    primeira = cliente.post("/avaliacoes", json={}).json()
    segunda = cliente.post("/avaliacoes", json={}).json()

    assert primeira["alertas_gerados"] == 4  # RA-02: R1; RA-05: R1, R2 e R3
    assert segunda["alertas_gerados"] == 0
    assert segunda["alertas_ja_existentes"] == 4
    assert len(cliente.get("/alertas").json()) == 4


# --- Escopo da avaliação e acesso ------------------------------------------

def test_campanha_pausada_so_e_avaliada_quando_pedido(cliente, sessao_teste, usuario_teste, campanhas_teste):
    criar_regras_padrao(sessao_teste, usuario_teste)
    ingerir(cliente, campanhas_teste["C"], [CENARIOS["RA-02"]])

    padrao = cliente.post("/avaliacoes", json={}).json()
    assert padrao["registros_avaliados"] == 0

    com_pausadas = cliente.post("/avaliacoes", json={"incluir_pausadas": True}).json()
    assert com_pausadas["registros_avaliados"] == 1
    assert com_pausadas["alertas_gerados"] == 1


def test_avaliacao_registra_contagens_e_tempo(cliente, sessao_teste, usuario_teste, campanhas_teste):
    criar_regras_padrao(sessao_teste, usuario_teste)
    ingerir(cliente, campanhas_teste["A"], VALIDOS)
    avaliacao = cliente.post("/avaliacoes", json={}).json()
    assert avaliacao["registros_avaliados"] == len(VALIDOS)
    assert avaliacao["registros_rejeitados"] == 0
    assert dec(avaliacao["duracao_motor_ms"]) >= 0
    assert cliente.get(f"/avaliacoes/{avaliacao['id']}").json()["id"] == avaliacao["id"]


def test_rotas_exigem_login(cliente_sem_login):
    for rota in ("/campanhas", "/regras", "/alertas"):
        assert cliente_sem_login.get(rota).status_code == 401
    assert cliente_sem_login.post("/avaliacoes", json={}).status_code == 401


def test_campanha_inexistente_ou_de_outro_usuario_e_404(cliente):
    assert cliente.get("/campanhas/999999/metricas").status_code == 404


def test_saude(cliente):
    assert cliente.get("/saude").json() == {"status": "ok"}
