"""Partes do medir_endpoints que não precisam de servidor nem banco.

Cobre: porta (livre, ocupada, nunca 8080), comando do uvicorn (sem --reload, 1 worker,
sem log de acesso), cliente (trust_env=False, só 127.0.0.1), encerramento do processo
(terminate, kill e porta presa), conferência de cada endpoint com respostas falsas,
o laço de medição (aquecimentos fora da estatística, falhas contadas) e a checagem do
cookie na evidência.
"""

from __future__ import annotations

import socket
import subprocess
import sys

import httpx
import pytest

from app.api.esquemas import RegraEntrada
from execucao import comum
from execucao.comum import SAIDA_AMBIENTE, SAIDA_EVIDENCIA_SENSIVEL, Parada
from execucao.desempenho import base
from execucao.desempenho import medir_endpoints as me

TOTAL_ALERTAS = 21_280
PLANO = base.Plano(aquecimentos=5, repeticoes=30, motor=(), endpoints=())


# --- Porta e comando --------------------------------------------------------------

def test_porta_fixa_nao_e_8080_e_so_local():
    assert me.PORTA != 8080
    assert me.HOST == "127.0.0.1"


def test_porta_ocupada_e_depois_livre():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as ocupante:
        ocupante.bind((me.HOST, 0))
        ocupante.listen()
        porta = ocupante.getsockname()[1]
        assert me.porta_livre(me.HOST, porta) is False
    assert me.porta_livre(me.HOST, porta) is True


def test_comando_do_uvicorn():
    cmd = me.COMANDO_UVICORN
    assert "--reload" not in cmd
    assert "--no-access-log" in cmd
    assert cmd[cmd.index("--workers") + 1] == "1"
    assert cmd[cmd.index("--host") + 1] == "127.0.0.1"
    assert cmd[cmd.index("--port") + 1] == str(me.PORTA) != "8080"


# --- Cliente ------------------------------------------------------------------------

def test_cliente_ignora_proxy_do_ambiente(monkeypatch):
    monkeypatch.setenv("HTTP_PROXY", "http://10.255.255.1:9")
    monkeypatch.setenv("ALL_PROXY", "http://10.255.255.1:9")
    with me.novo_cliente() as cliente:
        assert cliente.trust_env is False
        assert cliente._mounts == {}  # nenhum transporte de proxy montado
    with httpx.Client(trust_env=True) as controle:  # prova que o ambiente do teste teria efeito
        assert len(controle._mounts) > 0


@pytest.mark.parametrize(
    "url",
    ["http://exemplo.com/", "http://127.0.0.1:8080/", "https://127.0.0.1:8091/", "http://localhost:8091/"],
)
def test_cliente_recusa_pedido_fora_de_127_0_0_1(url):
    with me.novo_cliente() as cliente:
        with pytest.raises(Parada) as erro:
            cliente.get(url)  # o gancho roda antes de qualquer conexão
    assert erro.value.codigo == SAIDA_AMBIENTE


def test_gancho_aceita_o_servidor_do_script():
    me._so_local(httpx.Request("GET", f"http://127.0.0.1:{me.PORTA}/campanhas"))  # não levanta


# --- Encerramento do uvicorn ---------------------------------------------------------

def _processo(codigo: str, stdout=subprocess.DEVNULL) -> subprocess.Popen:
    return subprocess.Popen(
        [sys.executable, "-I", "-c", codigo], stdout=stdout, stderr=subprocess.DEVNULL, text=True
    )


def test_encerra_com_terminate(monkeypatch):
    monkeypatch.setattr(me, "porta_livre", lambda *a: True)
    processo = _processo("import time; time.sleep(60)")
    codigo, livre = me.encerrar_uvicorn(processo)
    assert codigo == -15 and livre is True
    assert processo.poll() is not None


def test_encerra_com_kill_quando_ignora_sigterm(monkeypatch):
    monkeypatch.setattr(me, "porta_livre", lambda *a: True)
    monkeypatch.setattr(me, "ESPERA_ENCERRAR_S", 1)
    processo = _processo(
        "import signal, time\n"
        "signal.signal(signal.SIGTERM, signal.SIG_IGN)\n"
        "print('pronto', flush=True)\n"
        "time.sleep(60)",
        stdout=subprocess.PIPE,
    )
    try:
        # Só manda o terminate depois que o filho avisou que já ignora o SIGTERM.
        assert processo.stdout.readline().strip() == "pronto"
        codigo, livre = me.encerrar_uvicorn(processo)
    finally:
        processo.stdout.close()
    assert codigo == -9 and livre is True


def test_porta_presa_depois_de_encerrar(monkeypatch):
    monkeypatch.setattr(me, "porta_livre", lambda *a: False)
    monkeypatch.setattr(me, "ESPERA_ENCERRAR_S", 0.3)
    _, livre = me.encerrar_uvicorn(_processo("pass"))
    assert livre is False


# --- Conferência de cada endpoint (respostas falsas) ---------------------------------

CASOS = me.casos(campanha_id=7, total_alertas=TOTAL_ALERTAS)
INICIO, FIM = (d.isoformat() for d in base.PERIODO_DE01)


def _linhas(n, primeira=INICIO, ultima=FIM):
    linhas = [{"data": "2026-09-01"} for _ in range(n)]
    if linhas:
        linhas[0]["data"], linhas[-1]["data"] = primeira, ultima
    return linhas


def _conferir(id_, resposta, n=1):
    return CASOS[id_][1](resposta, n)


def test_de01_monta_o_periodo_de_30_dias():
    metodo, caminho, kwargs = CASOS["DE-01"][0](1)
    assert (metodo, caminho) == ("GET", "/campanhas/7/metricas")
    assert kwargs == {"params": {"inicio": "2026-08-28", "fim": "2026-09-26"}}


@pytest.mark.parametrize(
    ("status", "linhas", "ok"),
    [
        (200, _linhas(30), True),
        (200, _linhas(29), False),
        (200, _linhas(31), False),
        (200, _linhas(30, primeira="2026-08-27"), False),
        (200, _linhas(30, ultima="2026-09-25"), False),
        (500, [], False),
    ],
)
def test_de01_conferencia(status, linhas, ok):
    assert _conferir("DE-01", httpx.Response(status, json=linhas))[0] is ok


@pytest.mark.parametrize(("itens", "ok"), [(500, True), (499, False), (501, False)])
def test_de02_espera_500_de_21280(itens, ok):
    assert _conferir("DE-02", httpx.Response(200, json=[{}] * itens)) == (ok, {"itens": itens})


def test_de02_com_menos_alertas_que_o_limite():
    _, conferir, descricao = me.casos(7, 300)["DE-02"]
    assert conferir(httpx.Response(200, json=[{}] * 300), 1)[0] is True
    assert "300 de 300" in descricao


@pytest.mark.parametrize("n", [1, 6, 35])
def test_de03_monta_regra_inativa_valida(n):
    metodo, caminho, kwargs = CASOS["DE-03"][0](n)
    assert (metodo, caminho) == ("POST", "/regras")
    entrada = RegraEntrada.model_validate(kwargs["json"])
    assert entrada.ativa is False and entrada.codigo == f"P{n:03d}"


@pytest.mark.parametrize(
    ("status", "corpo", "n", "ok"),
    [
        (201, {"codigo": "P007", "ativa": False}, 7, True),
        (201, {"codigo": "P006", "ativa": False}, 7, False),  # código de outro pedido
        (201, {"codigo": "P007", "ativa": True}, 7, False),
        (409, {"detail": "x", "tipo": "conflito"}, 7, False),
    ],
)
def test_de03_conferencia(status, corpo, n, ok):
    assert _conferir("DE-03", httpx.Response(status, json=corpo), n)[0] is ok


CORPO_DE04 = {
    "registros_avaliados": 10_000,
    "registros_rejeitados": 0,
    "alertas_gerados": 0,
    "alertas_ja_existentes": TOTAL_ALERTAS,
    "duracao_motor_ms": "35.123",
}


def test_de04_monta_corpo_vazio():
    assert CASOS["DE-04"][0](1) == ("POST", "/avaliacoes", {"json": {}})


@pytest.mark.parametrize(
    ("mudanca", "status", "ok"),
    [
        ({}, 201, True),
        ({"registros_avaliados": 9_999}, 201, False),
        ({"registros_rejeitados": 1}, 201, False),
        ({"alertas_gerados": 1}, 201, False),
        ({"alertas_ja_existentes": TOTAL_ALERTAS - 1}, 201, False),
        ({}, 400, False),
    ],
)
def test_de04_conferencia(mudanca, status, ok):
    ok_obtido, detalhes = _conferir("DE-04", httpx.Response(status, json=CORPO_DE04 | mudanca))
    assert ok_obtido is ok
    if status == 201:
        assert detalhes["registros_avaliados"] == (CORPO_DE04 | mudanca)["registros_avaliados"]
        assert detalhes["duracao_motor_ms"] == "35.123"


# --- Laço de medição ------------------------------------------------------------------

class ClienteFalso:
    """Responde em sequência; 'erro' levanta httpx.ConnectError."""

    def __init__(self, respostas):
        self.respostas = list(respostas)
        self.pedidos = []

    def request(self, metodo, caminho, **kwargs):
        self.pedidos.append((metodo, caminho, kwargs))
        r = self.respostas.pop(0)
        if r == "erro":
            raise httpx.ConnectError("falso")
        return r


def _montar(n):
    return "GET", f"/x/{n}", {}


def _conferir_200(r, _n):
    return r.status_code == 200, {}


def test_aquecimentos_antes_e_fora_da_estatistica():
    cliente = ClienteFalso([httpx.Response(200)] * 35)
    r = me.medir(cliente, PLANO, _montar, _conferir_200)
    assert [p[1] for p in cliente.pedidos] == [f"/x/{n}" for n in range(1, 36)]
    assert len(r["aquecimentos_ns"]) == 5 and len(r["amostras_ns"]) == 30
    assert r["estatisticas"]["n"] == 30
    assert [e["medida"] for e in r["execucoes"]] == [False] * 5 + [True] * 30


def test_falhas_contadas_e_fora_da_estatistica():
    respostas = [httpx.Response(200)] * 35
    respostas[2] = httpx.Response(500)  # aquecimento
    respostas[10] = httpx.Response(500)  # medida
    respostas[20] = "erro"  # medida, exceção
    r = me.medir(ClienteFalso(respostas), PLANO, _montar, _conferir_200)
    assert (r["falhas_aquecimento"], r["falhas_medidas"]) == (1, 2)
    assert len(r["aquecimentos_ns"]) == 4 and len(r["amostras_ns"]) == 28
    assert {"n": 21, "medida": True, "ok": False, "motivo": "ConnectError"} in r["execucoes"]


# --- Cookie na evidência -----------------------------------------------------------

def _relatorio(monkeypatch, tmp_path, texto):
    monkeypatch.setattr(comum, "DIR_EVIDENCIAS", tmp_path)
    rel = comum.Relatorio("desempenho_teste.txt")
    rel.add(texto)
    return rel


def test_cookie_na_evidencia_para_com_4(monkeypatch, tmp_path):
    rel = _relatorio(monkeypatch, tmp_path, "linha com eyJjb29raWUiOiJmYWxzbyJ9.valor")
    with pytest.raises(Parada) as erro:
        me.conferir_sem_cookie("eyJjb29raWUiOiJmYWxzbyJ9.valor", rel)
    assert erro.value.codigo == SAIDA_EVIDENCIA_SENSIVEL
    assert "eyJ" not in erro.value.mensagem


def test_evidencia_sem_cookie_passa(monkeypatch, tmp_path):
    rel = _relatorio(monkeypatch, tmp_path, "DE-01 média 3,2 ms")
    me.conferir_sem_cookie("eyJjb29raWUiOiJmYWxzbyJ9.valor", rel)  # não levanta
    me.conferir_sem_cookie(None, rel)
