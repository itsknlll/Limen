"""GET /resumo (visão geral do dashboard).

Os dados vêm do mesmo fluxo do IN-02b (campanhas sincronizadas + semeador +
POST /avaliacoes), então os números esperados são os da execução real:
18 alertas (6/6/6) só com ativas e 27 (9/9/9) incluindo a pausada. Como
oráculo independente, os totais por dia e por regra são comparados com a
contagem feita sobre GET /alertas (endpoint fixo).
"""

from collections import Counter
from datetime import datetime, timezone

import pytest

from app.modelos import Alerta, Campanha, ContaGoogleAds, Regra, Usuario
from app.servicos.avaliacao import executar_avaliacao
from app.servicos.regras import criar_regras_padrao
from app.servicos.sinteticas.semeador import semear_metricas_sinteticas

VAZIO_STATUS = {"ENABLED": 0, "PAUSED": 0, "REMOVED": 0, "UNKNOWN": 0}


@pytest.fixture
def dados_in02b(sessao_teste, usuario_teste, campanhas_teste):
    agora = datetime(2026, 11, 12, 19, 29, 24, tzinfo=timezone.utc)
    for campanha_id in campanhas_teste.values():
        sessao_teste.get(Campanha, campanha_id).sincronizada_em = agora
    sessao_teste.commit()
    criar_regras_padrao(sessao_teste, usuario_teste)
    sessao_teste.commit()
    semear_metricas_sinteticas(sessao_teste, usuario_teste)
    return campanhas_teste


def _oraculo_alertas(cliente, **filtros) -> tuple[Counter, dict[str, Counter]]:
    """Contagem por regra e por dia feita sobre GET /alertas."""
    por_regra, por_dia = Counter(), {}
    for a in cliente.get("/alertas", params={"limite": 5000, **filtros}).json():
        por_regra[a["regra_codigo"]] += 1
        por_dia.setdefault(a["data"], Counter())[a["regra_codigo"]] += 1
    return por_regra, por_dia


def _avaliacoes_dos_alertas(cliente, **filtros) -> int:
    """Avaliações distintas que geraram alertas, contadas sobre GET /alertas."""
    alertas = cliente.get("/alertas", params={"limite": 5000, **filtros}).json()
    return len({a["avaliacao_id"] for a in alertas})


def _por_regra(resumo) -> dict[str, int]:
    return {r["codigo"]: r["total"] for r in resumo["alertas"]["por_regra"]}


def _por_dia(resumo) -> dict[str, Counter]:
    return {d["data"]: Counter(d["por_regra"]) for d in resumo["alertas"]["por_dia"]}


def test_resumo_vazio(cliente):
    assert cliente.get("/resumo").json() == {
        "campanhas": {"total": 0, "por_status": VAZIO_STATUS},
        "regras": {"total": 0, "ativas": 0},
        "metricas": {
            "registros": 0,
            "inicio": None,
            "fim": None,
            "por_origem": {"sintetica": 0, "google_ads": 0},
        },
        "alertas": {"total": 0, "avaliacoes": 0, "por_regra": [], "por_dia": []},
        "ultima_avaliacao": None,
    }


def test_resumo_depois_da_avaliacao_so_com_ativas(cliente, dados_in02b):
    avaliacao = cliente.post("/avaliacoes", json={}).json()
    resumo = cliente.get("/resumo").json()

    assert resumo["campanhas"] == {
        "total": 3,
        "por_status": {**VAZIO_STATUS, "ENABLED": 2, "PAUSED": 1},
    }
    assert resumo["regras"] == {"total": 3, "ativas": 3}
    assert resumo["metricas"] == {
        "registros": 90,
        "inicio": "2026-10-13",
        "fim": "2026-11-11",
        "por_origem": {"sintetica": 90, "google_ads": 0},
    }
    assert resumo["alertas"]["total"] == 18
    assert resumo["alertas"]["avaliacoes"] == 1
    assert _por_regra(resumo) == {"R1": 6, "R2": 6, "R3": 6}
    assert resumo["ultima_avaliacao"]["id"] == avaliacao["id"]

    por_regra, por_dia = _oraculo_alertas(cliente)
    assert _por_regra(resumo) == dict(por_regra)
    assert _por_dia(resumo) == por_dia


def test_resumo_incluindo_pausadas(cliente, dados_in02b):
    cliente.post("/avaliacoes", json={})
    segunda = cliente.post("/avaliacoes", json={"incluir_pausadas": True}).json()
    resumo = cliente.get("/resumo").json()

    assert resumo["alertas"]["total"] == 27
    # o 27 soma alertas das duas execuções (18 da primeira + 9 da segunda)
    assert resumo["alertas"]["avaliacoes"] == 2 == _avaliacoes_dos_alertas(cliente)
    assert _por_regra(resumo) == {"R1": 9, "R2": 9, "R3": 9}
    assert resumo["ultima_avaliacao"]["id"] == segunda["id"]
    assert resumo["ultima_avaliacao"]["incluir_pausadas"] is True
    _, por_dia = _oraculo_alertas(cliente)
    assert _por_dia(resumo) == por_dia


def test_avaliacao_sem_alerta_novo_nao_conta(cliente, dados_in02b):
    cliente.post("/avaliacoes", json={})
    cliente.post("/avaliacoes", json={"incluir_pausadas": True})
    terceira = cliente.post("/avaliacoes", json={"incluir_pausadas": True}).json()
    assert terceira["alertas_gerados"] == 0 and terceira["alertas_ja_existentes"] == 27

    resumo = cliente.get("/resumo").json()
    assert len(cliente.get("/avaliacoes").json()) == 3
    assert resumo["alertas"]["total"] == 27
    assert resumo["alertas"]["avaliacoes"] == 2  # a terceira não gerou nenhum alerta


def test_por_dia_traz_so_dias_com_alerta_em_ordem(cliente, dados_in02b):
    cliente.post("/avaliacoes", json={})
    dias = [d["data"] for d in cliente.get("/resumo").json()["alertas"]["por_dia"]]
    assert dias == sorted(dias)
    assert all(d for d in dias)
    assert sum(
        sum(d["por_regra"].values()) for d in cliente.get("/resumo").json()["alertas"]["por_dia"]
    ) == 18


def test_filtro_de_periodo_bate_com_get_alertas(cliente, dados_in02b):
    cliente.post("/avaliacoes", json={"incluir_pausadas": True})
    filtros = {"inicio": "2026-10-20", "fim": "2026-10-31"}
    resumo = cliente.get("/resumo", params=filtros).json()

    assert resumo["metricas"]["registros"] == 3 * 12  # 3 campanhas x 12 dias
    assert (resumo["metricas"]["inicio"], resumo["metricas"]["fim"]) == ("2026-10-20", "2026-10-31")
    por_regra, por_dia = _oraculo_alertas(cliente, **filtros)
    assert resumo["alertas"]["total"] == sum(por_regra.values())
    assert resumo["alertas"]["avaliacoes"] == _avaliacoes_dos_alertas(cliente, **filtros)
    assert _por_dia(resumo) == por_dia
    # campanhas e regras não dependem do período
    assert resumo["campanhas"]["total"] == 3 and resumo["regras"]["total"] == 3


def test_regra_sem_alerta_aparece_com_zero(cliente, sessao_teste, usuario_teste, dados_in02b):
    cliente.post("/regras", json={
        "codigo": "R4",
        "nome": "Nunca dispara",
        "condicoes": [{"metrica": "impressoes", "operador": ">", "limiar": "1000000000"}],
    })
    cliente.post("/avaliacoes", json={})
    assert _por_regra(cliente.get("/resumo").json())["R4"] == 0

    # período sem nenhum alerta: todas as regras continuam presentes, com 0
    vazio = cliente.get("/resumo", params={"inicio": "2025-01-01", "fim": "2025-01-31"}).json()
    assert _por_regra(vazio) == {"R1": 0, "R2": 0, "R3": 0, "R4": 0}
    assert vazio["alertas"]["por_dia"] == []


def test_regra_desativada_conta_como_inativa(cliente, sessao_teste, usuario_teste, dados_in02b):
    regra = sessao_teste.query(Regra).filter_by(usuario_id=usuario_teste, codigo="R2").one()
    cliente.delete(f"/regras/{regra.id}")
    resumo = cliente.get("/resumo").json()
    assert resumo["regras"] == {"total": 3, "ativas": 2}
    assert {r["codigo"]: r["ativa"] for r in resumo["alertas"]["por_regra"]}["R2"] is False


def test_resumo_so_do_usuario(cliente, sessao_teste, dados_in02b):
    outro = Usuario(email="outro@limen.dev")
    sessao_teste.add(outro)
    sessao_teste.flush()
    criar_regras_padrao(sessao_teste, outro.id)
    sessao_teste.commit()

    resumo = cliente.get("/resumo").json()
    assert resumo["regras"]["total"] == 3  # as 3 do outro usuário não entram
    assert {r["codigo"] for r in resumo["alertas"]["por_regra"]} == {"R1", "R2", "R3"}


def test_avaliacoes_de_outro_usuario_nao_contam(cliente, sessao_teste, dados_in02b):
    cliente.post("/avaliacoes", json={})
    cliente.post("/avaliacoes", json={"incluir_pausadas": True})
    antes = cliente.get("/resumo").json()["alertas"]
    assert (antes["total"], antes["avaliacoes"]) == (27, 2)

    # Segundo usuário com a própria conta e a campanha A (mesmo ID do Google: a
    # unicidade é por conta), métricas sintéticas e uma avaliação que gera alertas.
    outro = Usuario(email="outro@limen.dev")
    sessao_teste.add(outro)
    sessao_teste.flush()
    conta = ContaGoogleAds(usuario_id=outro.id, customer_id="4327030343", nome="Outra conta")
    sessao_teste.add(conta)
    sessao_teste.flush()
    sessao_teste.add(Campanha(
        conta_id=conta.id,
        google_campaign_id=24444020070,
        nome="Outra A",
        status="ENABLED",
        orcamento_micros=50_000_000,
        sincronizada_em=datetime(2026, 11, 12, 19, 29, 24, tzinfo=timezone.utc),
    ))
    criar_regras_padrao(sessao_teste, outro.id)
    sessao_teste.commit()
    semear_metricas_sinteticas(sessao_teste, outro.id)
    avaliacao_do_outro = executar_avaliacao(sessao_teste, outro.id)

    # Pré-condição: há o que vazar (o banco tem mais alertas e avaliações que o primeiro vê)
    assert avaliacao_do_outro.alertas_gerados == 9
    assert sessao_teste.query(Alerta).count() == 27 + 9
    assert sessao_teste.query(Alerta.avaliacao_id).distinct().count() == 3

    depois = cliente.get("/resumo").json()["alertas"]
    assert (depois["total"], depois["avaliacoes"]) == (antes["total"], antes["avaliacoes"])


def test_periodo_invertido_e_400(cliente):
    resposta = cliente.get("/resumo", params={"inicio": "2026-11-11", "fim": "2026-10-13"})
    assert resposta.status_code == 400
    assert resposta.json() == {
        "detail": "inicio deve ser anterior ou igual a fim",
        "tipo": "requisicao_invalida",
    }


def test_resumo_exige_login(cliente_sem_login):
    assert cliente_sem_login.get("/resumo").status_code == 401
