"""Testes de unidade/integração da sincronização de campanhas (sub-etapa 3).

Nenhum teste chama o Google de verdade: a PortaFalsa retorna dados fixos.
A fixture chave_cifragem injeta uma chave Fernet válida via monkeypatch
para que cifrar/decifrar funcionem sem depender do .env.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

import grpc
import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.modelos import Campanha, ContaGoogleAds, Usuario
from app.servicos.erros import (
    ApiIndisponivel,
    CotaExcedida,
    ErroGoogleAds,
    TokenExpirado,
    TokenRevogado,
)
from app.servicos.sincronizacao.cliente_real import (
    _classificar_status_grpc,
    _extrair_codigo_falha,
)
from app.servicos.sincronizacao.interface import CampanhaGoogle
from app.servicos.sincronizacao.sincronizador import sincronizar

CUSTOMER_ID = "4327030343"
LOGIN_CUSTOMER_ID = "1137051091"

_CAMPANHAS_PADRAO = [
    CampanhaGoogle(24444020070, "Camp A", "ENABLED", 50_000_000),
    CampanhaGoogle(24464752468, "Camp B", "ENABLED", 80_000_000),
    CampanhaGoogle(24458906837, "Camp C", "PAUSED", 40_000_000),
]


# ---------------------------------------------------------------------------
# Dublê da porta Google Ads
# ---------------------------------------------------------------------------


@dataclass
class PortaFalsa:
    """Dublê que retorna campanhas fixas sem chamar o Google."""

    campanhas: list[CampanhaGoogle]
    chamadas: list[tuple[str, str]] = field(default_factory=list)

    def listar_campanhas(
        self, login_customer_id: str, customer_id: str, refresh_token: str
    ) -> list[CampanhaGoogle]:
        # Registra chamada para verificação; não armazena o token (privacidade)
        self.chamadas.append((login_customer_id, customer_id))
        return list(self.campanhas)


@dataclass
class PortaFalsaComFalhas:
    """Porta que lança exceções em sequência (uma por chamada) antes de retornar campanhas."""

    campanhas: list[CampanhaGoogle]
    falhas: list[Exception] = field(default_factory=list)
    chamadas: int = field(default=0, init=False)

    def listar_campanhas(
        self, login_customer_id: str, customer_id: str, refresh_token: str
    ) -> list[CampanhaGoogle]:
        self.chamadas += 1
        if self.falhas:
            raise self.falhas.pop(0)
        return list(self.campanhas)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def chave_cifragem(monkeypatch):
    chave = Fernet.generate_key().decode()
    from app import config
    monkeypatch.setattr(config.configuracoes, "chave_cifragem", chave)
    return chave


@pytest.fixture
def usuario_com_token(sessao_teste, chave_cifragem):
    """Usuário com refresh_token_cifrado já gravado, pronto para sincronizar."""
    from app.servicos.cifra import cifrar

    usuario = Usuario(
        email="sync@limen.dev",
        nome="Usuário Sync",
        refresh_token_cifrado=cifrar("tok_refresh_fake"),
    )
    sessao_teste.add(usuario)
    sessao_teste.flush()
    return usuario


# ---------------------------------------------------------------------------
# Testes do sincronizador
# ---------------------------------------------------------------------------


def test_sincronizar_cria_conta_google_ads(sessao_teste, usuario_com_token):
    """Primeira sincronização cria a ContaGoogleAds para o usuário."""
    porta = PortaFalsa(campanhas=[])
    sincronizar(usuario_com_token, CUSTOMER_ID, LOGIN_CUSTOMER_ID, sessao_teste, porta)

    conta = sessao_teste.scalar(
        select(ContaGoogleAds).where(ContaGoogleAds.usuario_id == usuario_com_token.id)
    )
    assert conta is not None
    assert conta.customer_id == CUSTOMER_ID
    assert conta.login_customer_id == LOGIN_CUSTOMER_ID


def test_sincronizar_reaproveita_conta_existente(sessao_teste, usuario_com_token):
    """Segunda sincronização com o mesmo customer_id não duplica a ContaGoogleAds."""
    porta = PortaFalsa(campanhas=[])
    sincronizar(usuario_com_token, CUSTOMER_ID, LOGIN_CUSTOMER_ID, sessao_teste, porta)
    sincronizar(usuario_com_token, CUSTOMER_ID, LOGIN_CUSTOMER_ID, sessao_teste, porta)

    total_contas = sessao_teste.scalar(
        select(func.count(ContaGoogleAds.id)).where(
            ContaGoogleAds.usuario_id == usuario_com_token.id
        )
    )
    assert total_contas == 1


def test_sincronizar_cria_campanhas(sessao_teste, usuario_com_token):
    """Sincronização cria Campanha para cada item retornado pela porta."""
    porta = PortaFalsa(campanhas=_CAMPANHAS_PADRAO)
    n = sincronizar(usuario_com_token, CUSTOMER_ID, LOGIN_CUSTOMER_ID, sessao_teste, porta)

    assert n == 3
    conta = sessao_teste.scalar(
        select(ContaGoogleAds).where(ContaGoogleAds.usuario_id == usuario_com_token.id)
    )
    campanhas = sessao_teste.scalars(
        select(Campanha).where(Campanha.conta_id == conta.id)
    ).all()
    assert len(campanhas) == 3


def test_sincronizar_idempotente(sessao_teste, usuario_com_token):
    """Duas sincronizações com as mesmas campanhas não duplicam registros."""
    porta = PortaFalsa(campanhas=_CAMPANHAS_PADRAO)
    sincronizar(usuario_com_token, CUSTOMER_ID, LOGIN_CUSTOMER_ID, sessao_teste, porta)
    sincronizar(usuario_com_token, CUSTOMER_ID, LOGIN_CUSTOMER_ID, sessao_teste, porta)

    conta = sessao_teste.scalar(
        select(ContaGoogleAds).where(ContaGoogleAds.usuario_id == usuario_com_token.id)
    )
    total = sessao_teste.scalar(
        select(func.count(Campanha.id)).where(Campanha.conta_id == conta.id)
    )
    assert total == 3


def test_sincronizar_atualiza_campos(sessao_teste, usuario_com_token):
    """Segunda sincronização com dados diferentes atualiza nome, status e orçamento."""
    porta1 = PortaFalsa(campanhas=[CampanhaGoogle(24444020070, "Camp A", "ENABLED", 50_000_000)])
    porta2 = PortaFalsa(campanhas=[CampanhaGoogle(24444020070, "Camp A Renomeada", "PAUSED", 60_000_000)])

    sincronizar(usuario_com_token, CUSTOMER_ID, LOGIN_CUSTOMER_ID, sessao_teste, porta1)
    sincronizar(usuario_com_token, CUSTOMER_ID, LOGIN_CUSTOMER_ID, sessao_teste, porta2)

    conta = sessao_teste.scalar(
        select(ContaGoogleAds).where(ContaGoogleAds.usuario_id == usuario_com_token.id)
    )
    campanha = sessao_teste.scalar(
        select(Campanha).where(
            Campanha.conta_id == conta.id,
            Campanha.google_campaign_id == 24444020070,
        )
    )
    assert campanha.nome == "Camp A Renomeada"
    assert campanha.status == "PAUSED"
    assert campanha.orcamento_micros == 60_000_000


def test_status_desconhecido_vira_unknown(sessao_teste, usuario_com_token):
    """Status fora de ENABLED/PAUSED/REMOVED é normalizado para UNKNOWN antes de gravar."""
    porta = PortaFalsa(campanhas=[CampanhaGoogle(99999999, "Camp Rara", "DRAFT", 10_000_000)])
    sincronizar(usuario_com_token, CUSTOMER_ID, LOGIN_CUSTOMER_ID, sessao_teste, porta)

    conta = sessao_teste.scalar(
        select(ContaGoogleAds).where(ContaGoogleAds.usuario_id == usuario_com_token.id)
    )
    campanha = sessao_teste.scalar(
        select(Campanha).where(Campanha.conta_id == conta.id)
    )
    assert campanha.status == "UNKNOWN"


def test_sincronizar_envia_parametros_corretos_para_porta(sessao_teste, usuario_com_token):
    """A porta recebe login_customer_id e customer_id na ordem correta."""
    porta = PortaFalsa(campanhas=[])
    sincronizar(usuario_com_token, CUSTOMER_ID, LOGIN_CUSTOMER_ID, sessao_teste, porta)

    assert len(porta.chamadas) == 1
    login_cid, cid = porta.chamadas[0]
    assert login_cid == LOGIN_CUSTOMER_ID
    assert cid == CUSTOMER_ID


# ---------------------------------------------------------------------------
# Teste do endpoint POST /campanhas/sincronizar
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Testes da função pura _orcamento (ajuste 2/5 — sem banco, sem Google)
# ---------------------------------------------------------------------------


def test_orcamento_zero_e_mantido():
    """Orçamento zero é valor válido; não deve virar None."""
    from app.servicos.sincronizacao.cliente_real import _orcamento

    assert _orcamento(0, "customers/1/campaignBudgets/99") == 0


def test_orcamento_positivo_e_mantido():
    from app.servicos.sincronizacao.cliente_real import _orcamento

    assert _orcamento(50_000_000, "customers/1/campaignBudgets/99") == 50_000_000


def test_orcamento_sem_vinculo_e_none():
    """resource_name vazio indica que não há orçamento vinculado → None."""
    from app.servicos.sincronizacao.cliente_real import _orcamento

    assert _orcamento(0, "") is None


# ---------------------------------------------------------------------------
# Testes de validação dos IDs Google Ads (ajuste 4 — sem banco)
# ---------------------------------------------------------------------------


def test_ids_google_ausentes_levantam_erro_claro(monkeypatch):
    from app import config

    monkeypatch.setattr(config.configuracoes, "google_customer_id", None)
    monkeypatch.setattr(config.configuracoes, "google_login_customer_id", None)
    with pytest.raises(ValueError, match="GOOGLE_CUSTOMER_ID"):
        _ = config.configuracoes.ids_google_ads


def test_ids_google_customer_invalido_levanta_erro_claro(monkeypatch):
    """customer_id com menos de 10 dígitos levanta ValueError identificando a variável."""
    from app import config

    monkeypatch.setattr(config.configuracoes, "google_customer_id", "123")
    monkeypatch.setattr(config.configuracoes, "google_login_customer_id", "1137051091")
    with pytest.raises(ValueError, match="GOOGLE_CUSTOMER_ID"):
        _ = config.configuracoes.ids_google_ads


def test_ids_google_login_invalido_levanta_erro_claro(monkeypatch):
    """login_customer_id inválido levanta ValueError identificando a variável correta."""
    from app import config

    monkeypatch.setattr(config.configuracoes, "google_customer_id", "4327030343")
    monkeypatch.setattr(config.configuracoes, "google_login_customer_id", "113")
    with pytest.raises(ValueError, match="GOOGLE_LOGIN_CUSTOMER_ID"):
        _ = config.configuracoes.ids_google_ads


def test_ids_google_com_tracas_levantam_erro_claro(monkeypatch):
    """ID com traços ('432-703-0343') não passa na validação de 10 dígitos."""
    from app import config

    monkeypatch.setattr(config.configuracoes, "google_customer_id", "432-703-0343")
    monkeypatch.setattr(config.configuracoes, "google_login_customer_id", "1137051091")
    with pytest.raises(ValueError, match="GOOGLE_CUSTOMER_ID"):
        _ = config.configuracoes.ids_google_ads


# ---------------------------------------------------------------------------
# Teste do endpoint: 409 quando usuário não tem token (ajuste 3)
# ---------------------------------------------------------------------------


def test_endpoint_sem_token_retorna_409(sessao_teste, monkeypatch):
    """TokenGoogleAusente do sincronizador deve chegar ao endpoint como 409."""
    from app import config
    from app.api.deps import obter_porta_google_ads, obter_sessao, obter_usuario_logado
    from app.main import app

    monkeypatch.setattr(config.configuracoes, "google_customer_id", CUSTOMER_ID)
    monkeypatch.setattr(config.configuracoes, "google_login_customer_id", LOGIN_CUSTOMER_ID)

    # Usuário em memória (sem token); não precisa estar no banco —
    # a exceção é levantada antes de qualquer consulta.
    usuario_sem_token = Usuario(email="notok@limen.dev", nome="Sem Token")

    app.dependency_overrides[obter_sessao] = lambda: sessao_teste
    app.dependency_overrides[obter_usuario_logado] = lambda: usuario_sem_token
    app.dependency_overrides[obter_porta_google_ads] = lambda: PortaFalsa(campanhas=[])

    try:
        with TestClient(app) as c:
            resp = c.post("/campanhas/sincronizar")
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 409
    assert resp.json()["detail"] == "Token Google Ads ausente; faça login com o Google para autorizar."


def test_endpoint_sincronizar_retorna_contagem(sessao_teste, usuario_com_token, monkeypatch):
    """POST /campanhas/sincronizar retorna 200 e campanhas_sincronizadas."""
    from app import config
    from app.api.deps import obter_porta_google_ads, obter_sessao, obter_usuario_logado
    from app.main import app

    monkeypatch.setattr(config.configuracoes, "google_customer_id", CUSTOMER_ID)
    monkeypatch.setattr(config.configuracoes, "google_login_customer_id", LOGIN_CUSTOMER_ID)

    porta = PortaFalsa(campanhas=_CAMPANHAS_PADRAO)

    app.dependency_overrides[obter_sessao] = lambda: sessao_teste
    app.dependency_overrides[obter_usuario_logado] = lambda: usuario_com_token
    app.dependency_overrides[obter_porta_google_ads] = lambda: porta

    try:
        with TestClient(app) as c:
            resp = c.post("/campanhas/sincronizar")
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 200
    assert resp.json()["campanhas_sincronizadas"] == 3


# ---------------------------------------------------------------------------
# Testes de funções puras do cliente_real.py (objetos falsos, sem banco)
# ---------------------------------------------------------------------------


def _exc_causa() -> Exception:
    return Exception("causa simulada")


# --- _classificar_status_grpc ---


def test_classificar_resource_exhausted_vira_cota_excedida():
    exc = _classificar_status_grpc(
        grpc.StatusCode.RESOURCE_EXHAUSTED, "", "RESOURCE_EXHAUSTED", None, _exc_causa()
    )
    assert isinstance(exc, CotaExcedida)
    assert exc.codigo == "RESOURCE_EXHAUSTED"


def test_classificar_unavailable_vira_api_indisponivel():
    exc = _classificar_status_grpc(
        grpc.StatusCode.UNAVAILABLE, "", "UNAVAILABLE", None, _exc_causa()
    )
    assert isinstance(exc, ApiIndisponivel)


def test_classificar_deadline_exceeded_vira_api_indisponivel():
    exc = _classificar_status_grpc(
        grpc.StatusCode.DEADLINE_EXCEEDED, "", "DEADLINE_EXCEEDED", None, _exc_causa()
    )
    assert isinstance(exc, ApiIndisponivel)


def test_classificar_unavailable_com_invalid_grant_vira_token_revogado():
    # invalid_grant verificado ANTES do status code — vale para qualquer status
    exc = _classificar_status_grpc(
        grpc.StatusCode.UNAVAILABLE, "token refresh error: invalid_grant", None, None, _exc_causa()
    )
    assert isinstance(exc, TokenRevogado)


def test_classificar_unauthenticated_com_invalid_grant_vira_token_revogado():
    exc = _classificar_status_grpc(
        grpc.StatusCode.UNAUTHENTICATED, "conta inválida: invalid_grant", None, None, _exc_causa()
    )
    assert isinstance(exc, TokenRevogado)


def test_classificar_permission_denied_vira_erro_google_ads_generico():
    exc = _classificar_status_grpc(
        grpc.StatusCode.PERMISSION_DENIED, "", "PERMISSION_DENIED", None, _exc_causa()
    )
    assert type(exc) is ErroGoogleAds
    assert exc.codigo == "PERMISSION_DENIED"


def test_classificar_code_none_vira_erro_google_ads_generico():
    exc = _classificar_status_grpc(None, "", None, None, _exc_causa())
    assert type(exc) is ErroGoogleAds


# --- _extrair_codigo_falha ---


def test_extrair_codigo_falha_retorna_none_none_se_tudo_falhar():
    class _Vazio:
        pass

    codigo, request_id = _extrair_codigo_falha(_Vazio())
    assert codigo is None
    assert request_id is None


def test_extrair_codigo_falha_retorna_grpc_nome_sem_failure_errors():
    class _FakeCode:
        name = "UNAVAILABLE"

    class _FakeError:
        def code(self):
            return _FakeCode()

    class _FakeFailure:
        errors: list = []

    class _FakeEx:
        error = _FakeError()
        request_id = None
        failure = _FakeFailure()

    codigo, request_id = _extrair_codigo_falha(_FakeEx())
    assert codigo == "UNAVAILABLE"
    assert request_id is None


# ---------------------------------------------------------------------------
# Testes do sincronizador com PortaFalsaComFalhas e espera injetável
# ---------------------------------------------------------------------------


def test_in03_token_expirado_renova_e_retorna_campanhas(
    sessao_teste, usuario_com_token, caplog
):
    esperas: list[int] = []
    porta = PortaFalsaComFalhas(
        campanhas=_CAMPANHAS_PADRAO,
        falhas=[TokenExpirado("tok expirado")],
    )
    with caplog.at_level(logging.WARNING):
        n = sincronizar(
            usuario_com_token, CUSTOMER_ID, LOGIN_CUSTOMER_ID, sessao_teste,
            porta, espera=esperas.append,
        )

    assert n == 3
    assert porta.chamadas == 2
    assert esperas == []  # TokenExpirado não dorme
    assert "IN-03" in caplog.text
    assert "retentando" in caplog.text
    # 3 campanhas persistidas, sem duplicata
    conta = sessao_teste.scalar(
        select(ContaGoogleAds).where(ContaGoogleAds.usuario_id == usuario_com_token.id)
    )
    total = sessao_teste.scalar(
        select(func.count(Campanha.id)).where(Campanha.conta_id == conta.id)
    )
    assert total == 3


def test_in03_token_expirado_duas_vezes_propaga(sessao_teste, usuario_com_token, caplog):
    esperas: list[int] = []
    porta = PortaFalsaComFalhas(
        campanhas=_CAMPANHAS_PADRAO,
        falhas=[TokenExpirado("tok1"), TokenExpirado("tok2")],
    )
    with caplog.at_level(logging.WARNING):
        with pytest.raises(TokenExpirado):
            sincronizar(
                usuario_com_token, CUSTOMER_ID, LOGIN_CUSTOMER_ID, sessao_teste,
                porta, espera=esperas.append,
            )

    assert porta.chamadas == 2
    assert esperas == []
    assert "falhou após nova tentativa" in caplog.text
    total_contas = sessao_teste.scalar(
        select(func.count(ContaGoogleAds.id)).where(
            ContaGoogleAds.usuario_id == usuario_com_token.id
        )
    )
    assert total_contas == 0


def test_in04_refresh_revogado_limpa_token_sem_dados_parciais(
    sessao_teste, usuario_com_token, caplog
):
    esperas: list[int] = []
    porta = PortaFalsaComFalhas(campanhas=[], falhas=[TokenRevogado("revogado")])
    with caplog.at_level(logging.WARNING):
        with pytest.raises(TokenRevogado):
            sincronizar(
                usuario_com_token, CUSTOMER_ID, LOGIN_CUSTOMER_ID, sessao_teste,
                porta, espera=esperas.append,
            )

    sessao_teste.refresh(usuario_com_token)
    assert usuario_com_token.refresh_token_cifrado is None

    total_contas = sessao_teste.scalar(
        select(func.count(ContaGoogleAds.id)).where(
            ContaGoogleAds.usuario_id == usuario_com_token.id
        )
    )
    assert total_contas == 0
    assert "IN-04" in caplog.text
    assert "tok_refresh_fake" not in caplog.text  # token nunca aparece no log


def test_in05_indisponivel_esgota_quatro_chamadas(
    sessao_teste, usuario_com_token, caplog
):
    esperas: list[int] = []
    porta = PortaFalsaComFalhas(
        campanhas=_CAMPANHAS_PADRAO,
        falhas=[ApiIndisponivel(f"err{i}") for i in range(4)],
    )
    with caplog.at_level(logging.WARNING):
        with pytest.raises(ApiIndisponivel):
            sincronizar(
                usuario_com_token, CUSTOMER_ID, LOGIN_CUSTOMER_ID, sessao_teste,
                porta, espera=esperas.append,
            )

    assert porta.chamadas == 4
    assert esperas == [1, 2, 4]
    assert "IN-05" in caplog.text
    assert "esgotadas" in caplog.text
    total_contas = sessao_teste.scalar(
        select(func.count(ContaGoogleAds.id)).where(
            ContaGoogleAds.usuario_id == usuario_com_token.id
        )
    )
    assert total_contas == 0


def test_in05_indisponivel_recupera_na_quarta_tentativa(sessao_teste, usuario_com_token):
    esperas: list[int] = []
    porta = PortaFalsaComFalhas(
        campanhas=_CAMPANHAS_PADRAO,
        falhas=[ApiIndisponivel(f"err{i}") for i in range(3)],
    )
    n = sincronizar(
        usuario_com_token, CUSTOMER_ID, LOGIN_CUSTOMER_ID, sessao_teste,
        porta, espera=esperas.append,
    )

    assert n == 3
    assert porta.chamadas == 4
    assert esperas == [1, 2, 4]
    # exatamente 3 campanhas, sem duplicata
    conta = sessao_teste.scalar(
        select(ContaGoogleAds).where(ContaGoogleAds.usuario_id == usuario_com_token.id)
    )
    total = sessao_teste.scalar(
        select(func.count(Campanha.id)).where(Campanha.conta_id == conta.id)
    )
    assert total == 3


def test_in06_cota_excedida_uma_chamada_codigo_preservado(
    sessao_teste, usuario_com_token, caplog
):
    esperas: list[int] = []
    porta = PortaFalsaComFalhas(
        campanhas=[],
        falhas=[CotaExcedida("cota", codigo="RESOURCE_EXHAUSTED")],
    )
    with caplog.at_level(logging.WARNING):
        with pytest.raises(CotaExcedida) as exc_info:
            sincronizar(
                usuario_com_token, CUSTOMER_ID, LOGIN_CUSTOMER_ID, sessao_teste,
                porta, espera=esperas.append,
            )

    assert porta.chamadas == 1
    assert esperas == []
    assert exc_info.value.codigo == "RESOURCE_EXHAUSTED"
    assert "IN-06" in caplog.text
    assert "RESOURCE_EXHAUSTED" in caplog.text
    total_contas = sessao_teste.scalar(
        select(func.count(ContaGoogleAds.id)).where(
            ContaGoogleAds.usuario_id == usuario_com_token.id
        )
    )
    assert total_contas == 0


def test_generico_erro_google_ads_uma_chamada_sem_retry(
    sessao_teste, usuario_com_token, caplog
):
    esperas: list[int] = []
    porta = PortaFalsaComFalhas(
        campanhas=[],
        falhas=[ErroGoogleAds("permissão negada", codigo="PERMISSION_DENIED")],
    )
    with caplog.at_level(logging.WARNING):
        with pytest.raises(ErroGoogleAds):
            sincronizar(
                usuario_com_token, CUSTOMER_ID, LOGIN_CUSTOMER_ID, sessao_teste,
                porta, espera=esperas.append,
            )

    assert porta.chamadas == 1
    assert esperas == []
    assert "não transitório" in caplog.text


# ---------------------------------------------------------------------------
# Testes de endpoint para os novos handlers HTTP
# ---------------------------------------------------------------------------


def test_endpoint_token_revogado_retorna_409(sessao_teste, usuario_com_token, monkeypatch):
    from app import config
    from app.api.deps import obter_porta_google_ads, obter_sessao, obter_usuario_logado
    from app.main import app

    monkeypatch.setattr(config.configuracoes, "google_customer_id", CUSTOMER_ID)
    monkeypatch.setattr(config.configuracoes, "google_login_customer_id", LOGIN_CUSTOMER_ID)

    porta = PortaFalsaComFalhas(campanhas=[], falhas=[TokenRevogado("revogado")])

    app.dependency_overrides[obter_sessao] = lambda: sessao_teste
    app.dependency_overrides[obter_usuario_logado] = lambda: usuario_com_token
    app.dependency_overrides[obter_porta_google_ads] = lambda: porta

    try:
        with TestClient(app) as c:
            resp = c.post("/campanhas/sincronizar")
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 409
    assert resp.json()["detail"] == "Token Google revogado; faça login com o Google novamente."


def test_endpoint_token_expirado_retorna_503(sessao_teste, usuario_com_token, monkeypatch):
    from app import config
    from app.api.deps import obter_porta_google_ads, obter_sessao, obter_usuario_logado
    from app.main import app

    monkeypatch.setattr(config.configuracoes, "google_customer_id", CUSTOMER_ID)
    monkeypatch.setattr(config.configuracoes, "google_login_customer_id", LOGIN_CUSTOMER_ID)

    # 2 falhas: 1ª tentativa + 1 retry; nenhuma espera entre elas
    porta = PortaFalsaComFalhas(
        campanhas=[], falhas=[TokenExpirado("tok"), TokenExpirado("tok")]
    )

    app.dependency_overrides[obter_sessao] = lambda: sessao_teste
    app.dependency_overrides[obter_usuario_logado] = lambda: usuario_com_token
    app.dependency_overrides[obter_porta_google_ads] = lambda: porta

    try:
        with TestClient(app) as c:
            resp = c.post("/campanhas/sincronizar")
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 503
    assert "Falha temporária" in resp.json()["detail"]


def test_endpoint_api_indisponivel_retorna_503(sessao_teste, usuario_com_token, monkeypatch):
    # Patch direto no módulo da rota para evitar os sleeps reais (1+2+4 s)
    from app import config
    from app.api.deps import obter_porta_google_ads, obter_sessao, obter_usuario_logado
    from app.api.rotas import campanhas as campanhas_route
    from app.main import app

    monkeypatch.setattr(config.configuracoes, "google_customer_id", CUSTOMER_ID)
    monkeypatch.setattr(config.configuracoes, "google_login_customer_id", LOGIN_CUSTOMER_ID)
    monkeypatch.setattr(
        campanhas_route,
        "sincronizar",
        lambda **_kw: (_ for _ in ()).throw(ApiIndisponivel("mock")),
    )

    app.dependency_overrides[obter_sessao] = lambda: sessao_teste
    app.dependency_overrides[obter_usuario_logado] = lambda: usuario_com_token
    app.dependency_overrides[obter_porta_google_ads] = lambda: PortaFalsa(campanhas=[])

    try:
        with TestClient(app) as c:
            resp = c.post("/campanhas/sincronizar")
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 503


def test_endpoint_cota_excedida_retorna_503_com_retry_after(
    sessao_teste, usuario_com_token, monkeypatch
):
    from app import config
    from app.api.deps import obter_porta_google_ads, obter_sessao, obter_usuario_logado
    from app.main import app

    monkeypatch.setattr(config.configuracoes, "google_customer_id", CUSTOMER_ID)
    monkeypatch.setattr(config.configuracoes, "google_login_customer_id", LOGIN_CUSTOMER_ID)

    porta = PortaFalsaComFalhas(
        campanhas=[], falhas=[CotaExcedida("cota", codigo="RESOURCE_EXHAUSTED")]
    )

    app.dependency_overrides[obter_sessao] = lambda: sessao_teste
    app.dependency_overrides[obter_usuario_logado] = lambda: usuario_com_token
    app.dependency_overrides[obter_porta_google_ads] = lambda: porta

    try:
        with TestClient(app) as c:
            resp = c.post("/campanhas/sincronizar")
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 503
    assert resp.headers["retry-after"] == "3600"
    assert "RESOURCE_EXHAUSTED" in resp.json()["detail"]


def test_endpoint_cota_excedida_sem_codigo_sem_none_no_detail(
    sessao_teste, usuario_com_token, monkeypatch
):
    from app import config
    from app.api.deps import obter_porta_google_ads, obter_sessao, obter_usuario_logado
    from app.main import app

    monkeypatch.setattr(config.configuracoes, "google_customer_id", CUSTOMER_ID)
    monkeypatch.setattr(config.configuracoes, "google_login_customer_id", LOGIN_CUSTOMER_ID)

    porta = PortaFalsaComFalhas(
        campanhas=[], falhas=[CotaExcedida("cota", codigo=None)]
    )

    app.dependency_overrides[obter_sessao] = lambda: sessao_teste
    app.dependency_overrides[obter_usuario_logado] = lambda: usuario_com_token
    app.dependency_overrides[obter_porta_google_ads] = lambda: porta

    try:
        with TestClient(app) as c:
            resp = c.post("/campanhas/sincronizar")
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 503
    assert "None" not in resp.json()["detail"]


def test_endpoint_erro_google_ads_generico_retorna_502(
    sessao_teste, usuario_com_token, monkeypatch
):
    from app import config
    from app.api.deps import obter_porta_google_ads, obter_sessao, obter_usuario_logado
    from app.main import app

    monkeypatch.setattr(config.configuracoes, "google_customer_id", CUSTOMER_ID)
    monkeypatch.setattr(config.configuracoes, "google_login_customer_id", LOGIN_CUSTOMER_ID)

    porta = PortaFalsaComFalhas(
        campanhas=[],
        falhas=[ErroGoogleAds("permissão negada", codigo="PERMISSION_DENIED")],
    )

    app.dependency_overrides[obter_sessao] = lambda: sessao_teste
    app.dependency_overrides[obter_usuario_logado] = lambda: usuario_com_token
    app.dependency_overrides[obter_porta_google_ads] = lambda: porta

    try:
        with TestClient(app) as c:
            resp = c.post("/campanhas/sincronizar")
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 502
    assert "PERMISSION_DENIED" in resp.json()["detail"]
