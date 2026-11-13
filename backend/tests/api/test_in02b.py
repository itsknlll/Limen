"""Caso IN-02b: métricas sintéticas nas campanhas reais sincronizadas, pela API.

Cada teste monta a própria aplicação com `criar_app()` e o AMBIENTE desejado,
para que o teste de 404 seja real (roteador /dev não registrado) e nada dependa
do backend/.env. A sincronização usa o dublê PortaFalsa da sub-etapa 4, com os
IDs reais das campanhas da conta de teste.
"""

from collections import Counter

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from openpyxl import load_workbook

from app import motor
from app.api.deps import (
    obter_porta_google_ads,
    obter_sessao,
    obter_usuario_atual,
    obter_usuario_logado,
)
from app.config import configuracoes
from app.main import criar_app
from app.modelos import Usuario
from app.servicos.regras import criar_regras_padrao
from app.servicos.sinteticas.gerador import gerar_metricas

from ..tabela_congelada import CAMINHO_TABELA, carregar_regras
from ..test_sincronizacao import _CAMPANHAS_PADRAO, CUSTOMER_ID, LOGIN_CUSTOMER_ID, PortaFalsa

A, B, C = 24444020070, 24464752468, 24458906837  # C está PAUSED
ROTA = "/dev/metricas-sinteticas"


# --- Fixtures ---------------------------------------------------------------------

@pytest.fixture
def usuario_google(sessao_teste, monkeypatch) -> Usuario:
    """Usuário que concluiu o IN-01: refresh token cifrado e regras padrão."""
    from app.servicos.cifra import cifrar

    monkeypatch.setattr(configuracoes, "chave_cifragem", Fernet.generate_key().decode())
    monkeypatch.setattr(configuracoes, "google_customer_id", CUSTOMER_ID)
    monkeypatch.setattr(configuracoes, "google_login_customer_id", LOGIN_CUSTOMER_ID)

    usuario = Usuario(email="in02b@limen.dev", refresh_token_cifrado=cifrar("tok_refresh_fake"))
    sessao_teste.add(usuario)
    sessao_teste.flush()
    criar_regras_padrao(sessao_teste, usuario.id)
    sessao_teste.commit()
    return usuario


@pytest.fixture
def fabrica_cliente(sessao_teste, monkeypatch):
    abertos = []

    def fabricar(usuario: Usuario | None = None, ambiente: str = "desenvolvimento") -> TestClient:
        monkeypatch.setattr(configuracoes, "ambiente", ambiente)
        app = criar_app()
        app.dependency_overrides[obter_sessao] = lambda: sessao_teste
        app.dependency_overrides[obter_porta_google_ads] = lambda: PortaFalsa(_CAMPANHAS_PADRAO)
        if usuario is not None:
            app.dependency_overrides[obter_usuario_atual] = lambda: usuario.id
            app.dependency_overrides[obter_usuario_logado] = lambda: usuario
        cliente = TestClient(app)
        cliente.__enter__()
        abertos.append(cliente)
        return cliente

    yield fabricar
    for cliente in abertos:
        cliente.__exit__(None, None, None)


# --- Auxiliares -------------------------------------------------------------------

def _linha_in02b() -> tuple:
    planilha = load_workbook(CAMINHO_TABELA, read_only=True)["Integração"]
    for linha in planilha.iter_rows(values_only=True):
        if linha[0] == "IN-02b":
            return linha[1:5]
    raise AssertionError("IN-02b não encontrado na aba Integração")


def _campanhas(cliente) -> dict[int, dict]:
    return {c["google_campaign_id"]: c for c in cliente.get("/campanhas").json()}


def _alertas_observados(cliente, campanhas) -> set[tuple[int, str, str]]:
    google_por_id = {c["id"]: g for g, c in campanhas.items()}
    return {
        (google_por_id[a["campanha_id"]], a["data"], a["regra_codigo"])
        for a in cliente.get("/alertas", params={"limite": 5000}).json()
    }


def _alertas_esperados_pelo_motor(google_ids) -> set[tuple[int, str, str]]:
    """Oráculo: o motor puro, com os limiares lidos da tabela congelada."""
    regras = carregar_regras()
    esperado = set()
    for g in google_ids:
        for m in gerar_metricas(g):
            registro = motor.RegistroMetricas(m.impressoes, m.cliques, m.custo, m.conversoes)
            esperado |= {(g, m.data.isoformat(), r) for r in motor.avaliar(registro, regras).disparadas}
    return esperado


def _por_campanha(observados) -> dict[int, Counter]:
    contagem = {A: Counter(), B: Counter(), C: Counter()}
    for g, _, regra in observados:
        contagem[g][regra] += 1
    return contagem


TRES_DE_CADA = Counter({"R1": 3, "R2": 3, "R3": 3})


# --- Resultado literal da tabela ---------------------------------------------------

def test_in02b_resultado_da_tabela(fabrica_cliente, usuario_google):
    assert _linha_in02b() == (
        "Real + sintética",
        "Associação de métricas sintéticas às campanhas reais sincronizadas",
        "IN-02 concluído",
        "Métricas sintéticas gravadas com o ID real da campanha e marcadas como sintéticas; "
        "motor avalia normalmente",
    )
    cliente = fabrica_cliente(usuario_google)

    # Pré-condição: IN-02 concluído
    assert cliente.post("/campanhas/sincronizar").json() == {"campanhas_sincronizadas": 3}
    assert cliente.post(ROTA).status_code == 200

    # (a) gravadas com o ID real da campanha
    campanhas = _campanhas(cliente)
    assert set(campanhas) == {A, B, C}
    for camp in campanhas.values():
        metricas = cliente.get(f"/campanhas/{camp['id']}/metricas").json()
        assert len(metricas) == 30
        # (b) marcadas como sintéticas
        assert {(m["origem"], m["lote"]) for m in metricas} == {("sintetica", "in02b-s20261112")}

    # (c) motor avalia normalmente: só ativas por padrão (A e B)
    avaliacao = cliente.post("/avaliacoes", json={}).json()
    assert avaliacao["registros_avaliados"] == 60
    assert avaliacao["registros_rejeitados"] == 0
    assert avaliacao["alertas_gerados"] == 18
    observados = _alertas_observados(cliente, campanhas)
    assert _por_campanha(observados) == {A: TRES_DE_CADA, B: TRES_DE_CADA, C: Counter()}
    assert observados == _alertas_esperados_pelo_motor({A, B})

    # (c) com incluir_pausadas, C também é avaliada
    avaliacao = cliente.post("/avaliacoes", json={"incluir_pausadas": True}).json()
    assert avaliacao["registros_avaliados"] == 90
    assert avaliacao["registros_rejeitados"] == 0
    assert avaliacao["alertas_gerados"] == 9
    assert avaliacao["alertas_ja_existentes"] == 18
    observados = _alertas_observados(cliente, campanhas)
    assert _por_campanha(observados) == {A: TRES_DE_CADA, B: TRES_DE_CADA, C: TRES_DE_CADA}
    assert observados == _alertas_esperados_pelo_motor({A, B, C})


def test_in02b_reavaliar_nao_duplica_alertas(fabrica_cliente, usuario_google):
    cliente = fabrica_cliente(usuario_google)
    cliente.post("/campanhas/sincronizar")
    cliente.post(ROTA)
    cliente.post("/avaliacoes", json={})

    segunda = cliente.post("/avaliacoes", json={}).json()
    assert segunda["alertas_gerados"] == 0
    assert segunda["alertas_ja_existentes"] == 18
    assert len(cliente.get("/alertas", params={"limite": 5000}).json()) == 18


# --- Rota /dev/metricas-sinteticas -------------------------------------------------

def test_rota_so_existe_em_desenvolvimento(fabrica_cliente, usuario_google):
    assert fabrica_cliente(usuario_google, ambiente="producao").post(ROTA).status_code == 404
    # controle: a mesma chamada em desenvolvimento encontra a rota
    assert fabrica_cliente(usuario_google, ambiente="desenvolvimento").post(ROTA).status_code != 404


def test_rota_exige_login(fabrica_cliente, sessao_teste):
    resposta = fabrica_cliente(usuario=None).post(ROTA)
    assert resposta.status_code == 401
    assert resposta.json()["detail"] == "Faça login para continuar"


def test_rota_grava_e_e_idempotente(fabrica_cliente, usuario_google):
    cliente = fabrica_cliente(usuario_google)
    cliente.post("/campanhas/sincronizar")

    primeira = cliente.post(ROTA).json()
    assert primeira["lote"] == "in02b-s20261112"
    assert (primeira["inicio"], primeira["fim"]) == ("2026-10-13", "2026-11-11")
    assert [c["inseridos"] for c in primeira["campanhas"]] == [30, 30, 30]

    segunda = cliente.post(ROTA).json()
    assert [c["inseridos"] for c in segunda["campanhas"]] == [0, 0, 0]
    assert [c["ja_existentes"] for c in segunda["campanhas"]] == [30, 30, 30]


def test_rota_sem_campanha_sincronizada_e_409(fabrica_cliente, usuario_google):
    resposta = fabrica_cliente(usuario_google).post(ROTA)
    assert resposta.status_code == 409
    assert "Nenhuma campanha sincronizada" in resposta.json()["detail"]


@pytest.mark.parametrize("dias", [8, 3661, "abc"])
def test_rota_parametro_invalido_e_400(fabrica_cliente, usuario_google, dias):
    resposta = fabrica_cliente(usuario_google).post(ROTA, params={"dias": dias})
    assert resposta.status_code == 400  # IN-09: validação devolve 400, não 422
