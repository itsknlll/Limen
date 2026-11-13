"""Campo `tipo` nos erros da API (Fase 0 do dashboard).

Formato único: {"detail": ..., "tipo": ...}. O `detail` continua o mesmo de antes;
o `tipo` deixa o frontend escolher a ação sem depender do texto da mensagem.

Erros que dá para provocar pela própria API usam o caminho real. Os erros do
Google Ads (que não dá para forçar de verdade) usam uma aplicação montada só
para o teste, com uma rota que levanta cada exceção; o `app` global não é tocado.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import criar_app
from app.servicos.erros import (
    ApiIndisponivel,
    ConflitoDados,
    CotaExcedida,
    ErroGoogleAds,
    NaoEncontrado,
    TokenExpirado,
    TokenGoogleAusente,
    TokenRevogado,
)

# --- Caminhos reais -------------------------------------------------------------


def test_validacao_400(cliente):
    regra = {"codigo": "R9", "nome": "Inválida", "condicoes": [
        {"metrica": "ctr", "operador": "<", "limiar": "-1"}
    ]}
    resposta = cliente.post("/regras", json=regra)
    corpo = resposta.json()
    assert resposta.status_code == 400
    assert corpo["tipo"] == "validacao"
    assert isinstance(corpo["detail"], list)  # lista {local, mensagem, tipo} de sempre
    assert {"local", "mensagem", "tipo"} <= set(corpo["detail"][0])


def test_requisicao_invalida_400_no_callback_oauth(cliente_sem_login):
    resposta = cliente_sem_login.get("/api/oauth/google/callback")
    assert resposta.status_code == 400
    assert resposta.json() == {
        "detail": "Parâmetros de callback ausentes",
        "tipo": "requisicao_invalida",
    }


def test_nao_autenticado_401(cliente_sem_login):
    resposta = cliente_sem_login.get("/campanhas")
    assert resposta.status_code == 401
    assert resposta.json() == {"detail": "Faça login para continuar", "tipo": "nao_autenticado"}


def test_nao_encontrado_404_de_recurso(cliente):
    resposta = cliente.get("/campanhas/999999/metricas")
    assert resposta.status_code == 404
    assert resposta.json() == {"detail": "Campanha não encontrada", "tipo": "nao_encontrado"}


def test_nao_encontrado_404_de_rota_inexistente(cliente):
    resposta = cliente.get("/rota-que-nao-existe")
    assert resposta.status_code == 404
    assert resposta.json()["tipo"] == "nao_encontrado"


def test_metodo_nao_permitido_405_vira_erro_http_e_mantem_cabecalho(cliente):
    resposta = cliente.delete("/saude")
    assert resposta.status_code == 405
    assert resposta.json()["tipo"] == "erro_http"
    assert "GET" in resposta.headers["allow"]  # cabeçalhos da HTTPException preservados


def test_conflito_409_de_regra_duplicada(cliente):
    regra = {"codigo": "R9", "nome": "CTR baixo bis", "condicoes": [
        {"metrica": "ctr", "operador": "<", "limiar": "1"}
    ]}
    assert cliente.post("/regras", json=regra).status_code == 201
    resposta = cliente.post("/regras", json=regra)
    assert resposta.status_code == 409
    assert resposta.json() == {
        "detail": "Já existe uma regra com o código R9",
        "tipo": "conflito",
    }


# --- Exceções levantadas por uma rota só de teste --------------------------------

EXCECOES = {
    "nao_encontrado": NaoEncontrado("Regra não encontrada"),
    "conflito": ConflitoDados("Conflito de teste"),
    "token_ausente": TokenGoogleAusente("Token Google Ads ausente"),
    "token_revogado": TokenRevogado("invalid_grant", codigo="invalid_grant"),
    "token_expirado": TokenExpirado("refresh temporário"),
    "indisponivel": ApiIndisponivel("Google Ads indisponível após 4 tentativas"),
    "cota": CotaExcedida("cota", codigo="quota_error=RESOURCE_EXHAUSTED"),
    "google_generico": ErroGoogleAds("permissão", codigo="PERMISSION_DENIED"),
}


@pytest.fixture
def cliente_excecoes():
    app = criar_app()

    @app.get("/_teste/erro/{nome}")
    def levantar(nome: str):
        raise EXCECOES[nome]

    with TestClient(app) as cliente:
        yield cliente


@pytest.mark.parametrize(
    ("nome", "status", "tipo", "detail"),
    [
        ("nao_encontrado", 404, "nao_encontrado", "Regra não encontrada"),
        ("conflito", 409, "conflito", "Conflito de teste"),
        ("token_ausente", 409, "token_google_ausente", "Token Google Ads ausente"),
        (
            "token_revogado",
            409,
            "token_google_revogado",
            "Token Google revogado; faça login com o Google novamente.",
        ),
        (
            "token_expirado",
            503,
            "google_autenticacao_temporaria",
            "Falha temporária de autenticação com o Google; tente novamente.",
        ),
        (
            "indisponivel",
            503,
            "google_ads_indisponivel",
            "Google Ads indisponível após 4 tentativas",
        ),
        (
            "cota",
            503,
            "cota_excedida",
            "Cota excedida [quota_error=RESOURCE_EXHAUSTED]; tente novamente em 1 hora.",
        ),
        (
            "google_generico",
            502,
            "erro_google_ads",
            "Erro na comunicação com o Google Ads [PERMISSION_DENIED].",
        ),
    ],
)
def test_tipo_de_cada_excecao(cliente_excecoes, nome, status, tipo, detail):
    resposta = cliente_excecoes.get(f"/_teste/erro/{nome}")
    assert resposta.status_code == status
    assert resposta.json() == {"detail": detail, "tipo": tipo}


def test_cota_excedida_mantem_retry_after(cliente_excecoes):
    resposta = cliente_excecoes.get("/_teste/erro/cota")
    assert resposta.headers["retry-after"] == "3600"
