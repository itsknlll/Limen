"""Semeador de métricas sintéticas (IN-02b) contra o banco de teste."""

from dataclasses import replace
from datetime import datetime, timezone

import pytest
from sqlalchemy import func, select

from app.modelos import Campanha, MetricaDiaria, Usuario
from app.servicos import campanhas as servico_campanhas
from app.servicos.erros import ConflitoDados
from app.servicos.sinteticas import semeador
from app.servicos.sinteticas.semeador import semear_metricas_sinteticas

IDS_REAIS = {24444020070, 24464752468, 24458906837}


@pytest.fixture
def campanhas_sincronizadas(sessao_teste, campanhas_teste) -> dict[str, int]:
    """As campanhas de teste marcadas como vindas da sincronização (pré-condição: IN-02)."""
    agora = datetime(2026, 11, 12, 19, 29, 24, tzinfo=timezone.utc)
    for campanha_id in campanhas_teste.values():
        sessao_teste.get(Campanha, campanha_id).sincronizada_em = agora
    sessao_teste.commit()
    return campanhas_teste


def _contar(sessao, campanha_id=None) -> int:
    consulta = select(func.count()).select_from(MetricaDiaria)
    if campanha_id is not None:
        consulta = consulta.where(MetricaDiaria.campanha_id == campanha_id)
    return sessao.scalar(consulta)


# --- Tudo ou nada entre campanhas ----------------------------------------------

def test_falha_na_segunda_campanha_nao_deixa_a_primeira_no_banco(
    sessao_teste, usuario_teste, campanhas_sincronizadas, monkeypatch
):
    """A segunda campanha viola um CHECK do banco; a primeira, já gravada, é desfeita."""
    gerar_real = semeador.gerar_metricas
    chamadas = []

    def gerar_com_defeito_na_segunda(google_id, *args):
        gerados = gerar_real(google_id, *args)
        chamadas.append(google_id)
        if len(chamadas) == 2:
            primeiro = gerados[0]
            gerados[0] = replace(primeiro, cliques=primeiro.impressoes + 1)
        return gerados

    gravadas = []
    adicionar_real = semeador.adicionar_metricas_sinteticas

    def adicionar_espiao(sessao, usuario_id, campanha_id, lote, registros):
        n = adicionar_real(sessao, usuario_id, campanha_id, lote, registros)
        gravadas.append(campanha_id)  # só chega aqui se o flush deu certo
        return n

    monkeypatch.setattr(semeador, "gerar_metricas", gerar_com_defeito_na_segunda)
    monkeypatch.setattr(semeador, "adicionar_metricas_sinteticas", adicionar_espiao)
    # Desliga a validação em Python só aqui: quem recusa é o CHECK do banco.
    monkeypatch.setattr(semeador, "_validar", lambda *args: None)

    with pytest.raises(ConflitoDados) as erro:
        semear_metricas_sinteticas(sessao_teste, usuario_teste)

    # Campanhas em ordem de nome: A, B, C. A foi gravada (flush) e B falhou.
    assert gravadas == [campanhas_sincronizadas["A"]]
    assert "ck_metrica_cliques_ate_impressoes" in str(erro.value.__cause__)
    assert _contar(sessao_teste) == 0


def test_registro_invalido_do_gerador_e_barrado_antes_de_gravar(
    sessao_teste, usuario_teste, campanhas_sincronizadas, monkeypatch
):
    """Sem atalho: a mesma validar_registro da API roda sobre os dados gerados."""
    gerar_real = semeador.gerar_metricas

    def gerar_negativo(google_id, *args):
        gerados = gerar_real(google_id, *args)
        gerados[-1] = replace(gerados[-1], impressoes=-1)
        return gerados

    monkeypatch.setattr(semeador, "gerar_metricas", gerar_negativo)
    with pytest.raises(ValueError, match="impressoes não pode ser negativo"):
        semear_metricas_sinteticas(sessao_teste, usuario_teste)
    assert _contar(sessao_teste) == 0


# --- Gravação, marcação e idempotência ------------------------------------------

def test_grava_90_registros_sinteticos_com_ids_reais(
    sessao_teste, usuario_teste, campanhas_sincronizadas
):
    resultado = semear_metricas_sinteticas(sessao_teste, usuario_teste)

    assert resultado["lote"] == "in02b-s20261112"
    assert [c["inseridos"] for c in resultado["campanhas"]] == [30, 30, 30]
    linhas = sessao_teste.execute(
        select(Campanha.google_campaign_id, MetricaDiaria.origem, MetricaDiaria.lote).join(
            MetricaDiaria.campanha
        )
    ).all()
    assert len(linhas) == 90
    assert {g for g, _, _ in linhas} == IDS_REAIS
    assert {(o, l) for _, o, l in linhas} == {("sintetica", "in02b-s20261112")}


def test_rodar_duas_vezes_nao_duplica(sessao_teste, usuario_teste, campanhas_sincronizadas):
    semear_metricas_sinteticas(sessao_teste, usuario_teste)
    segunda = semear_metricas_sinteticas(sessao_teste, usuario_teste)

    assert [c["inseridos"] for c in segunda["campanhas"]] == [0, 0, 0]
    assert [c["ja_existentes"] for c in segunda["campanhas"]] == [30, 30, 30]
    assert _contar(sessao_teste) == 90


def test_dia_de_outro_lote_e_conflito_e_nada_e_gravado(
    sessao_teste, usuario_teste, campanhas_sincronizadas
):
    primeiro_dia = semeador.INICIO_PADRAO
    registro = semeador.gerar_metricas(24464752468)[0]
    servico_campanhas.ingerir_metricas_sinteticas(
        sessao_teste, usuario_teste, campanhas_sincronizadas["B"], "outro-lote", [registro]
    )
    assert registro.data == primeiro_dia

    with pytest.raises(ConflitoDados, match="24464752468"):
        semear_metricas_sinteticas(sessao_teste, usuario_teste)
    assert _contar(sessao_teste) == 1  # só o registro que já existia
    assert _contar(sessao_teste, campanhas_sincronizadas["A"]) == 0


def test_periodo_incompleto_do_mesmo_lote_e_conflito(
    sessao_teste, usuario_teste, campanhas_sincronizadas
):
    semear_metricas_sinteticas(sessao_teste, usuario_teste, dias=10)
    with pytest.raises(ConflitoDados, match="período incompleto"):
        semear_metricas_sinteticas(sessao_teste, usuario_teste, dias=30)
    assert _contar(sessao_teste) == 30  # 3 campanhas x 10 dias, nada a mais


# --- Quais campanhas recebem métricas -------------------------------------------

def test_sem_campanha_sincronizada_e_conflito(sessao_teste, usuario_teste, campanhas_teste):
    """Pré-condição IN-02 não cumprida: campanhas existem, mas não vieram da sincronização."""
    with pytest.raises(ConflitoDados, match="Nenhuma campanha sincronizada"):
        semear_metricas_sinteticas(sessao_teste, usuario_teste)
    assert _contar(sessao_teste) == 0


def test_campanha_removida_nao_recebe_metricas(
    sessao_teste, usuario_teste, campanhas_sincronizadas
):
    sessao_teste.get(Campanha, campanhas_sincronizadas["C"]).status = "REMOVED"
    sessao_teste.commit()

    resultado = semear_metricas_sinteticas(sessao_teste, usuario_teste)
    assert {c["google_campaign_id"] for c in resultado["campanhas"]} == {24444020070, 24464752468}
    assert _contar(sessao_teste, campanhas_sincronizadas["C"]) == 0


def test_campanhas_de_outro_usuario_nao_sao_tocadas(
    sessao_teste, usuario_teste, campanhas_sincronizadas
):
    outro = Usuario(email="outro@limen.dev")
    sessao_teste.add(outro)
    sessao_teste.flush()
    with pytest.raises(ConflitoDados, match="Nenhuma campanha sincronizada"):
        semear_metricas_sinteticas(sessao_teste, outro.id)
    assert _contar(sessao_teste) == 0
