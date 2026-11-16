"""Partes do medir_google_ads que não precisam de rede, banco nem credencial.

Porta, sessão e decifragem são falsas; os IDs da conta são fictícios
(não são os da conta de teste do Google Ads).
"""

from __future__ import annotations

import logging

import pytest

from app.servicos.erros import ApiIndisponivel, CotaExcedida, ErroGoogleAds, TokenRevogado
from app.servicos.sincronizacao.interface import CampanhaGoogle
from execucao import comum
from execucao.comum import SAIDA_AMBIENTE, SAIDA_EVIDENCIA_SENSIVEL, Parada
from execucao.desempenho import base
from execucao.desempenho import medir_google_ads as mg

IDS = ("1234567890", "0987654321")  # (customer_id, login_customer_id) fictícios
TOKEN = "token-falso-de-teste-abc"
PLANO = base.Plano(aquecimentos=5, repeticoes=30, motor=(), endpoints=())
CAMPANHAS = [CampanhaGoogle(1, "A", "ENABLED", 50_000_000), CampanhaGoogle(2, "B", "PAUSED", None)]


class PortaFalsa:
    """Devolve as campanhas ou levanta a exceção da posição n (1, 2, ...)."""

    def __init__(self, falhas: dict[int, Exception] | None = None):
        self.falhas = falhas or {}
        self.chamadas = []

    def listar_campanhas(self, login_customer_id, customer_id, refresh_token):
        self.chamadas.append((login_customer_id, customer_id, refresh_token))
        erro = self.falhas.get(len(self.chamadas))
        if erro:
            raise erro
        return CAMPANHAS


# --- chamar -------------------------------------------------------------------------

def test_chamar_ok_devolve_latencia_e_quantidade():
    porta = PortaFalsa()
    ns, status, quantidade = mg.chamar(porta, IDS, TOKEN)
    assert status == "ok" and quantidade == 2 and isinstance(ns, int) and ns >= 0
    assert porta.chamadas == [("0987654321", "1234567890", TOKEN)]  # login, customer, token na ordem certa


def test_chamar_falha_do_google_so_tipo_e_codigo():
    erro = CotaExcedida("mensagem com dado ya29.segredo", codigo="quota_error=RESOURCE_EXHAUSTED")
    ns, status, quantidade = mg.chamar(PortaFalsa({1: erro}), IDS, TOKEN)
    assert status == "CotaExcedida [quota_error=RESOURCE_EXHAUSTED]"
    assert "ya29" not in status and quantidade is None and ns is not None


def test_chamar_falha_sem_codigo():
    _, status, _ = mg.chamar(PortaFalsa({1: ErroGoogleAds("detalhe interno")}), IDS, TOKEN)
    assert status == "ErroGoogleAds"


def test_chamar_erro_inesperado_sem_latencia():
    ns, status, quantidade = mg.chamar(PortaFalsa({1: ValueError("detalhe interno")}), IDS, TOKEN)
    assert (ns, status, quantidade) == (None, "ValueError", None)


# --- executar_chamadas --------------------------------------------------------------

def test_35_chamadas_com_intervalo_e_aquecimentos_marcados():
    esperas = []
    execucoes, interrompido = mg.executar_chamadas(PortaFalsa(), IDS, TOKEN, PLANO, espera=esperas.append)
    assert interrompido is None
    assert len(execucoes) == 35
    assert [e["medida"] for e in execucoes] == [False] * 5 + [True] * 30
    assert esperas == [mg.INTERVALO_S] * 34  # entre chamadas, nunca antes da primeira
    assert mg.INTERVALO_S >= 1


@pytest.mark.parametrize("erro", [CotaExcedida("x", codigo="quota_error=RESOURCE_EXHAUSTED"), TokenRevogado("x")])
def test_interrompe_na_cota_e_no_token_revogado(erro):
    porta = PortaFalsa({3: erro})
    execucoes, interrompido = mg.executar_chamadas(porta, IDS, TOKEN, PLANO, espera=lambda s: None)
    assert interrompido == type(erro).__name__
    assert len(execucoes) == 3 and len(porta.chamadas) == 3  # não insiste


def test_api_indisponivel_nao_interrompe():
    porta = PortaFalsa({3: ApiIndisponivel("x")})
    execucoes, interrompido = mg.executar_chamadas(porta, IDS, TOKEN, PLANO, espera=lambda s: None)
    assert interrompido is None and len(execucoes) == 35
    assert execucoes[2]["status"] == "ApiIndisponivel" and execucoes[2]["campanhas"] is None


# --- conferir_sem_token (token e IDs da conta) ---------------------------------------

def _rel(monkeypatch, tmp_path, *linhas):
    monkeypatch.setattr(comum, "DIR_EVIDENCIAS", tmp_path)
    rel = comum.Relatorio("desempenho_teste.txt")
    for linha in linhas:
        rel.add(linha)
    return rel


@pytest.mark.parametrize(
    ("linha", "campo"),
    [
        (f"valor {TOKEN} vazou", "refresh token"),
        ("conta 1234567890 consultada", "customer_id"),
        ("mcc 0987654321", "login_customer_id"),
        ('{"customer_id": "1234567890"}', "customer_id"),
    ],
)
def test_recusa_token_e_ids(monkeypatch, tmp_path, linha, campo):
    rel = _rel(monkeypatch, tmp_path, "cabeçalho", linha)
    with pytest.raises(Parada) as erro:
        mg.conferir_sem_token(TOKEN, IDS, rel)
    assert erro.value.codigo == SAIDA_EVIDENCIA_SENSIVEL
    assert campo in erro.value.mensagem
    assert "1234567890" not in erro.value.mensagem and TOKEN not in erro.value.mensagem


def test_recusa_id_num_segundo_relatorio(monkeypatch, tmp_path):
    txt = _rel(monkeypatch, tmp_path, "texto limpo")
    js = comum.Relatorio("desempenho_teste.json")
    js.add('{"x": "0987654321"}')
    with pytest.raises(Parada):
        mg.conferir_sem_token(TOKEN, IDS, txt, js)


def test_id_dentro_de_numero_maior_nao_conta(monkeypatch, tmp_path):
    rel = _rel(monkeypatch, tmp_path, '"latencia_ns": 91234567890', "ids: 12345678901")
    mg.conferir_sem_token(TOKEN, IDS, rel)  # não levanta


def test_texto_limpo_passa(monkeypatch, tmp_path):
    rel = _rel(monkeypatch, tmp_path, "  1  aquec.        312.441  ok  3")
    mg.conferir_sem_token(TOKEN, IDS, rel)


# --- conferir_ordem_e_ler_token (sessão falsa) ---------------------------------------

class Usuario:
    def __init__(self, cifrado):
        self.refresh_token_cifrado = cifrado


class SessaoFalsa:
    def __init__(self, regras_p: int, conectados: list):
        self.regras_p = regras_p
        self.conectados = conectados

    def scalar(self, _consulta):
        return self.regras_p

    def scalars(self, _consulta):
        conectados = self.conectados

        class _R:
            def all(self):
                return conectados

        return _R()


@pytest.fixture
def decifrar_falso(monkeypatch):
    import app.servicos.cifra as cifra

    monkeypatch.setattr(cifra, "decifrar", lambda cifrado: f"decifrado:{cifrado}")


def test_sem_regras_p_para_com_3(decifrar_falso):
    with pytest.raises(Parada) as erro:
        mg.conferir_ordem_e_ler_token(SessaoFalsa(0, [Usuario("c1")]))
    assert erro.value.codigo == SAIDA_AMBIENTE and "medir_endpoints" in erro.value.mensagem


@pytest.mark.parametrize("conectados", [[], [Usuario("c1"), Usuario("c2")]], ids=["nenhum", "dois"])
def test_conta_nao_conectada_para_com_3_sem_oauth(decifrar_falso, conectados):
    with pytest.raises(Parada) as erro:
        mg.conferir_ordem_e_ler_token(SessaoFalsa(35, conectados))
    assert erro.value.codigo == SAIDA_AMBIENTE
    assert "navegador" in erro.value.mensagem and "não é feito aqui" in erro.value.mensagem


def test_um_conectado_devolve_o_token_decifrado(decifrar_falso):
    assert mg.conferir_ordem_e_ler_token(SessaoFalsa(35, [Usuario("c1")])) == "decifrado:c1"


# --- logs da biblioteca --------------------------------------------------------------

@pytest.fixture
def loggers_restaurados():
    estado = {n: (logging.getLogger(n).level, logging.getLogger(n).propagate) for n in mg.BIBLIOTECAS_SILENCIADAS}
    yield
    for nome, (nivel, propaga) in estado.items():
        logging.getLogger(nome).setLevel(nivel)
        logging.getLogger(nome).propagate = propaga


def test_logs_da_biblioteca_desligados(loggers_restaurados):
    mg.silenciar_biblioteca()
    assert "google.ads.googleads" in mg.BIBLIOTECAS_SILENCIADAS
    for nome in mg.BIBLIOTECAS_SILENCIADAS:
        registro = logging.getLogger(nome)
        assert registro.level > logging.CRITICAL and registro.propagate is False
        assert not registro.isEnabledFor(logging.CRITICAL)
