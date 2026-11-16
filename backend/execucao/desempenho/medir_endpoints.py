"""DE-01 a DE-04: tempo dos 4 endpoints fixos (aba Desempenho, linhas 22 a 25).

Uso, na pasta backend com o venv ativo (a URL vai no comando, não no .env):

    DATABASE_URL=<url do banco limen_desempenho> python -m execucao.desempenho.medir_endpoints

Pré-condição: execucao.desempenho.preparar rodou neste banco e este script ainda não
(as regras P001 a P035 do DE-03 não podem existir).

Servidor: o próprio script sobe o uvicorn como subprocesso, em 127.0.0.1:PORTA
(nunca 8080), sem --reload, com --workers 1, --log-level warning e --no-access-log,
com a DATABASE_URL do comando e AMBIENTE=desenvolvimento (para o /dev/login). A
saída e os logs do uvicorn vão para /dev/null: nunca entram na evidência nem no
terminal. O uvicorn roda em sessão própria (Ctrl+C chega só a este script) e é
encerrado no finally (terminate; kill após 10 s), também com erro, Ctrl+C, SIGTERM
ou SIGHUP; depois o script confere que a porta ficou livre.
Log de acesso desligado: com ele, cada pedido formataria e escreveria uma linha no
mesmo processo que responde, e esse custo entraria em cada amostra.

Cliente: httpx.Client com trust_env=False (sem proxy nem .netrc do ambiente) e um
gancho que recusa qualquer pedido fora de 127.0.0.1:PORTA.

Prova de que o servidor está no banco certo: GET /campanhas tem de devolver
exatamente as 10 campanhas fictícias (900001 a 900010) e GET /regras, R1 a R10
ativas iguais a definicoes_regras(10). Senão, sai com 3 ou 2 sem medir.

Fora do cronômetro: subir o servidor, /dev/login (o cookie fica só no cliente;
nem ele nem a resposta, que traz o e-mail, vão para a evidência), as conferências
acima, montar o corpo de cada pedido, ler o JSON e contar os itens. Dentro: só
client.request(...), que volta com o corpo já lido.

Ordem: DE-01, DE-02, DE-03, DE-04 (a da planilha); cada endpoint faz os seus
aquecimentos (B3 = 5) e só depois as repetições medidas (B4 = 30).
Esperado a cada pedido (senão é falha e a amostra não entra na estatística):
  DE-01 GET /campanhas/{id}/metricas?inicio=2026-08-28&fim=2026-09-26 → 200, 30 linhas
        do primeiro ao último dia do período;
  DE-02 GET /alertas → 200, min(500, total) itens; total = GET /resumo = motor puro;
  DE-03 POST /regras com a regra P<n> inativa → 201, o mesmo código P<n>, ativa false;
  DE-04 POST /avaliacoes {} → 201, 10.000 avaliados, 0 rejeitados, 0 gerados,
        total já existentes (estado estável deixado pelo preparar).
Exceção (timeout, conexão) também é falha.

Saída: 0 ok · 1 alguma falha · 2 regras diferentes · 3 ambiente (porta ocupada,
servidor não subiu, banco errado, porta presa no fim) · 4 evidência sensível · 5.
Evidências: docs/evidencias/AAAA-MM-DD_desempenho_endpoints.txt e .json
"""

from __future__ import annotations

import json
import os
import signal
import socket
import subprocess
import sys
import time
from datetime import datetime
from decimal import Decimal

import httpx

from ..comum import (
    FUSO,
    RAIZ_BACKEND,
    SAIDA_AMBIENTE,
    SAIDA_DIVERGENCIA,
    SAIDA_EVIDENCIA_SENSIVEL,
    SAIDA_OK,
    SAIDA_REGRAS_DIFERENTES,
    Parada,
    Relatorio,
    rodar,
)
from . import base
from .preparar import LIMITE_PADRAO_ALERTAS, disparos_esperados

HOST = "127.0.0.1"
PORTA = 8091  # nunca a 8080 do uvicorn de desenvolvimento (URI cadastrada no Google)
ESPERA_SUBIR_S = 30
ESPERA_ENCERRAR_S = 10
TIMEOUT_PEDIDO_S = 120
COMANDO_UVICORN = [
    "-m", "uvicorn", "app.main:app",
    "--host", HOST, "--port", str(PORTA),
    "--workers", "1", "--log-level", "warning", "--no-access-log",
]  # sem --reload


# --- Porta e servidor -----------------------------------------------------------

def porta_livre(host: str = HOST, porta: int = PORTA) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((host, porta))
        except OSError:
            return False
    return True


def _sinal_vira_interrupcao(numero, _quadro):
    raise KeyboardInterrupt(f"sinal {numero}")


def subir_uvicorn() -> subprocess.Popen:
    ambiente = dict(os.environ)  # já tem a DATABASE_URL do comando, validada antes
    ambiente["AMBIENTE"] = "desenvolvimento"
    return subprocess.Popen(
        [sys.executable, *COMANDO_UVICORN],
        cwd=RAIZ_BACKEND,
        env=ambiente,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,  # logs descartados: nada do servidor chega à evidência
        stderr=subprocess.DEVNULL,
        start_new_session=True,  # o Ctrl+C do terminal chega só a este script
    )


def esperar_subir(processo: subprocess.Popen, cliente: httpx.Client) -> None:
    limite = time.monotonic() + ESPERA_SUBIR_S
    while time.monotonic() < limite:
        if processo.poll() is not None:
            raise Parada(SAIDA_AMBIENTE, f"O uvicorn saiu com {processo.returncode} ao subir (logs descartados "
                                         "de propósito; rode-o à mão para ver o erro).")
        try:
            if cliente.get("/openapi.json").status_code == 200:
                return
        except httpx.TransportError:
            pass
        time.sleep(0.2)
    raise Parada(SAIDA_AMBIENTE, f"O uvicorn não respondeu em {ESPERA_SUBIR_S} s.")


def encerrar_uvicorn(processo: subprocess.Popen) -> tuple[int | None, bool]:
    """(código de saída do uvicorn, porta livre depois?)."""
    if processo.poll() is None:
        processo.terminate()
        try:
            processo.wait(ESPERA_ENCERRAR_S)
        except subprocess.TimeoutExpired:
            processo.kill()
            processo.wait(ESPERA_ENCERRAR_S)
    limite = time.monotonic() + ESPERA_ENCERRAR_S
    while time.monotonic() < limite:
        if porta_livre():
            return processo.returncode, True
        time.sleep(0.2)
    return processo.returncode, False


# --- Cliente ----------------------------------------------------------------------

def _so_local(pedido: httpx.Request) -> None:
    if pedido.url.host != HOST or pedido.url.port != PORTA or pedido.url.scheme != "http":
        raise Parada(SAIDA_AMBIENTE, "Pedido fora de 127.0.0.1 recusado pelo cliente.")


def novo_cliente() -> httpx.Client:
    return httpx.Client(
        base_url=f"http://{HOST}:{PORTA}",
        trust_env=False,  # ignora HTTP(S)_PROXY, ALL_PROXY, NO_PROXY e .netrc
        timeout=TIMEOUT_PEDIDO_S,
        follow_redirects=False,
        event_hooks={"request": [_so_local]},
    )


# --- Conferências antes de medir (fora do cronômetro) -------------------------------

def conferir_servidor(cliente: httpx.Client) -> tuple[int, int]:
    """(id da primeira campanha, total de alertas). Para com 3 ou 2 se o banco não for o esperado."""
    campanhas = cliente.get("/campanhas")
    if campanhas.status_code != 200:
        raise Parada(SAIDA_AMBIENTE, f"GET /campanhas devolveu {campanhas.status_code}.")
    por_google = {c["google_campaign_id"]: c for c in campanhas.json()}
    if sorted(por_google) != base.ids_campanhas(base.CAMPANHAS_ENDPOINTS) or any(
        c["status"] != "ENABLED" for c in por_google.values()
    ):
        raise Parada(SAIDA_AMBIENTE, "O servidor não está no limen_desempenho preparado (campanhas diferentes).")

    regras = cliente.get("/regras").json()
    ativas = {
        r["codigo"]: tuple(
            (c["metrica"], c["operador"], Decimal(c["limiar"])) for c in sorted(r["condicoes"], key=lambda c: c["ordem"])
        )
        for r in regras
        if r["ativa"]
    }
    esperadas = {
        d.codigo: tuple((m, o, Decimal(l)) for m, o, l in d.condicoes)
        for d in base.definicoes_regras(base.REGRAS_ENDPOINTS)
    }
    if ativas != esperadas:
        raise Parada(SAIDA_REGRAS_DIFERENTES, "Regras ativas diferentes de R1 a R10 (nada medido).")
    if any(r["codigo"].startswith("P") for r in regras):
        raise Parada(SAIDA_AMBIENTE, "Regras P* já existem: este script já rodou neste banco. Recrie com o preparar.")

    total = cliente.get("/resumo").json()["alertas"]["total"]
    return por_google[base.ids_campanhas(1)[0]]["id"], total


# --- Medição -----------------------------------------------------------------------

def medir(cliente: httpx.Client, plano: base.Plano, montar, conferir) -> dict:
    """montar(n) → (método, caminho, kwargs); conferir(resposta, n) → (ok, detalhes). n começa em 1."""
    aquecimentos, amostras, execucoes = [], [], []
    for n in range(1, plano.aquecimentos + plano.repeticoes + 1):
        medida = n > plano.aquecimentos
        metodo, caminho, kwargs = montar(n)  # fora do cronômetro
        try:
            inicio = time.perf_counter_ns()
            resposta = cliente.request(metodo, caminho, **kwargs)  # volta com o corpo lido
            fim = time.perf_counter_ns()
        except httpx.HTTPError as erro:
            execucoes.append({"n": n, "medida": medida, "ok": False, "motivo": type(erro).__name__})
            continue
        ok, detalhes = conferir(resposta, n)  # fora do cronômetro
        execucoes.append({"n": n, "medida": medida, "ok": ok, "status": resposta.status_code, **detalhes})
        if ok:
            (amostras if medida else aquecimentos).append(fim - inicio)
    falhas = [e for e in execucoes if not e["ok"]]
    est = base.estatisticas(amostras) if len(amostras) >= 2 else None
    return {
        "aquecimentos_ns": aquecimentos,
        "amostras_ns": amostras,
        "execucoes": execucoes,
        "falhas_medidas": sum(1 for e in falhas if e["medida"]),
        "falhas_aquecimento": sum(1 for e in falhas if not e["medida"]),
        "estatisticas": None if est is None else {
            k: str(getattr(est, k)) for k in ("media_ms", "mediana_ms", "desvio_ms", "minimo_ms", "maximo_ms", "p95_ms")
        } | {"n": est.n, "coef_variacao": None if est.coef_variacao is None else str(est.coef_variacao)},
    }


def _json(resposta: httpx.Response, status: int):
    return resposta.json() if resposta.status_code == status else None


def casos(campanha_id: int, total_alertas: int) -> dict:
    """{ID: (montar, conferir, descrição)} dos 4 endpoints."""
    inicio, fim = base.PERIODO_DE01
    itens_de02 = min(LIMITE_PADRAO_ALERTAS, total_alertas)

    def de01(r, _n):
        linhas = _json(r, 200) or []
        datas = (linhas[0]["data"], linhas[-1]["data"]) if linhas else None
        ok = r.status_code == 200 and len(linhas) == base.DIAS_DE01 and datas == (inicio.isoformat(), fim.isoformat())
        return ok, {"itens": len(linhas)}

    def de02(r, _n):
        itens = len(_json(r, 200) or [])
        return r.status_code == 200 and itens == itens_de02, {"itens": itens}

    def de03_montar(n):
        return "POST", "/regras", {"json": base.regra_do_de03(n).corpo(ativa=False)}

    def de03(r, n):
        corpo = _json(r, 201) or {}
        ok = r.status_code == 201 and corpo.get("codigo") == base.regra_do_de03(n).codigo and corpo.get("ativa") is False
        return ok, {"codigo": corpo.get("codigo")}

    def de04(r, _n):
        c = _json(r, 201) or {}
        detalhes = {k: c.get(k) for k in ("registros_avaliados", "registros_rejeitados", "alertas_gerados",
                                          "alertas_ja_existentes", "duracao_motor_ms")}
        ok = r.status_code == 201 and (
            c.get("registros_avaliados") == base.REGISTROS_ENDPOINTS
            and c.get("registros_rejeitados") == 0
            and c.get("alertas_gerados") == 0
            and c.get("alertas_ja_existentes") == total_alertas
        )
        return ok, detalhes

    return {
        "DE-01": (lambda n: ("GET", f"/campanhas/{campanha_id}/metricas",
                             {"params": {"inicio": inicio.isoformat(), "fim": fim.isoformat()}}), de01,
                  f"campanha id {campanha_id} (900001), {inicio.isoformat()} a {fim.isoformat()}, "
                  f"esperado {base.DIAS_DE01} linhas"),
        "DE-02": (lambda n: ("GET", "/alertas", {}), de02,
                  f"sem filtros, limite padrão {LIMITE_PADRAO_ALERTAS}: esperado {itens_de02} de {total_alertas} alertas"),
        "DE-03": (de03_montar, de03, "P001 a P035, inativas (não mudam as 10 regras ativas)"),
        "DE-04": (lambda n: ("POST", "/avaliacoes", {"json": {}}), de04,
                  f"corpo vazio: esperado {base.REGISTROS_ENDPOINTS} avaliados, 0 rejeitados, 0 gerados, "
                  f"{total_alertas} já existentes"),
    }


def conferir_sem_cookie(valor_cookie: str | None, *relatorios: Relatorio) -> None:
    """Para com 4 se o valor do cookie de sessão aparecer em alguma evidência."""
    if valor_cookie and any(valor_cookie in "\n".join(r.linhas) for r in relatorios):
        raise Parada(SAIDA_EVIDENCIA_SENSIVEL, "Evidências NÃO gravadas: o valor do cookie de sessão apareceria.")


def _ms(valor: str | None) -> str:
    return "—" if valor is None else str(base.arredondar(Decimal(valor)))


def principal() -> int:
    base.url_desempenho()
    plano = base.ler_plano()
    txt, js = Relatorio("desempenho_endpoints.txt"), Relatorio("desempenho_endpoints.json")
    for linha in base.cabecalho("execucao/desempenho/medir_endpoints.py", "Desempenho — endpoints (DE)"):
        txt.add(linha)
    base.conferir_aplicacao_usa_desempenho()

    from app.db import SessaoLocal

    with SessaoLocal() as sessao:
        base.conferir_banco_conectado(sessao)
        servidor = base.versao_servidor(sessao)

    if not porta_livre():
        raise Parada(SAIDA_AMBIENTE, f"Porta {PORTA} ocupada em {HOST}: libere-a antes de medir.")

    esperado_motor = sum(disparos_esperados().values())  # oráculo sem banco, antes de subir o servidor
    amb = base.ambiente(servidor)

    for sinal in (signal.SIGTERM, signal.SIGHUP):
        signal.signal(sinal, _sinal_vira_interrupcao)  # o finally roda também nesses casos

    processo = subir_uvicorn()
    resultados: dict[str, dict] = {}
    ordem: list[dict] = []
    valor_cookie = None
    ativas_depois: list[str] = []
    try:
        with novo_cliente() as cliente:
            esperar_subir(processo, cliente)
            login = cliente.post("/dev/login")  # fora do cronômetro; a resposta (com e-mail) é descartada
            if login.status_code != 200:
                raise Parada(SAIDA_AMBIENTE, f"/dev/login devolveu {login.status_code}.")
            valor_cookie = cliente.cookies.get("session")
            del login
            campanha_id, total_alertas = conferir_servidor(cliente)
            if total_alertas != esperado_motor:
                raise Parada(SAIDA_AMBIENTE, f"Alertas no banco ({total_alertas}) ≠ motor puro ({esperado_motor}): "
                                             "rode o preparar de novo num banco novo.")
            for id_, endpoint in plano.endpoints:
                montar, conferir, descricao = casos(campanha_id, total_alertas)[id_]
                inicio = datetime.now(FUSO)
                resultados[id_] = {"endpoint": endpoint, "descricao": descricao,
                                   **medir(cliente, plano, montar, conferir)}
                ordem.append({"id": id_, "inicio": inicio.isoformat(timespec="seconds"),
                              "fim": datetime.now(FUSO).isoformat(timespec="seconds")})
                print(f"{id_} concluído")
            ativas_depois = sorted(r["codigo"] for r in cliente.get("/regras").json() if r["ativa"])
    finally:
        codigo_uvicorn, porta_liberada = encerrar_uvicorn(processo)
        print(f"uvicorn encerrado (código {codigo_uvicorn}); porta {PORTA} livre: {porta_liberada}")

    # --- Evidência ---------------------------------------------------------------
    txt.add("Ambiente:")
    for chave, valor in amb.items():
        txt.add(f"  {chave}: {valor}")
    txt.add("Servidor: uvicorn " + " ".join(COMANDO_UVICORN[2:]) + " (sem --reload; logs descartados)")
    txt.add(f"Cliente: httpx {httpx.__version__}, trust_env=False, só {HOST}:{PORTA}, timeout {TIMEOUT_PEDIDO_S} s, "
            "uma conexão mantida; sessão por /dev/login fora do cronômetro (cookie e resposta não registrados)")
    txt.add(f"Plano (planilha): {plano.aquecimentos} aquecimentos e {plano.repeticoes} repetições por endpoint")
    txt.add("Medido: só client.request(...), do envio até o corpo lido.")
    txt.add("")
    txt.add("Ordem de execução:")
    for posicao, o in enumerate(ordem, start=1):
        txt.add(f"  {posicao}. {o['id']}  {o['inicio']} → {o['fim']}")
    txt.add("")
    txt.add("ID     Endpoint                       Média(ms) Mediana(ms) Desvio(ms)  p95(ms)  Mín(ms)  Máx(ms) Falhas")
    for id_, r in resultados.items():
        e = r["estatisticas"] or {}
        txt.add(f"{id_}  {r['endpoint']:<30} " + " ".join(
            f"{_ms(e.get(k)):>9}" for k in ("media_ms", "mediana_ms", "desvio_ms", "p95_ms", "minimo_ms", "maximo_ms")
        ) + f"  {r['falhas_medidas']}")
    txt.add("")
    for id_, r in resultados.items():
        itens = sorted({x.get("itens") for x in r["execucoes"] if "itens" in x})
        txt.add(f"{id_}: {r['descricao']}. Falhas: {r['falhas_medidas']} medidas, {r['falhas_aquecimento']} no "
                f"aquecimento" + (f"; itens devolvidos em todas as execuções: {itens}" if itens else ""))
    if "DE-02" in resultados:
        txt.add(f"  Nota: o DE-02 devolve sempre {min(LIMITE_PADRAO_ALERTAS, total_alertas)} de {total_alertas} "
                f"alertas por causa do limite padrão do GET /alertas; o tempo é o de listar "
                f"{min(LIMITE_PADRAO_ALERTAS, total_alertas)}, não {total_alertas}.")
    if "DE-03" in resultados:
        codigos = [x.get("codigo") for x in resultados["DE-03"]["execucoes"] if x.get("codigo")]
        faixa = f"{codigos[0]} a {codigos[-1]}" if codigos else "nenhuma"
        txt.add(f"  DE-03 criou {len(codigos)} regras inativas ({faixa}); ativas depois: {', '.join(ativas_depois)}")
    if "DE-04" in resultados:
        motor_ns = [int(Decimal(str(x["duracao_motor_ms"])) * 1_000_000) for x in resultados["DE-04"]["execucoes"]
                    if x["ok"] and x["medida"]]
        if len(motor_ns) >= 2:
            em = base.estatisticas(motor_ns)
            txt.add(f"  DE-04, parte do motor (duracao_motor_ms da resposta, mesmas {em.n} repetições): média "
                    f"{base.arredondar(em.media_ms)} ms, mediana {base.arredondar(em.mediana_ms)} ms, p95 "
                    f"{base.arredondar(em.p95_ms)} ms; o resto do pedido é leitura no banco, INSERT ... ON CONFLICT "
                    "e serialização.")
    txt.add("")
    txt.add(f"Encerramento: uvicorn saiu com {codigo_uvicorn}; porta {PORTA} livre depois: {porta_liberada}")

    falhou = any(r["falhas_medidas"] or r["falhas_aquecimento"] for r in resultados.values())
    txt.add(f"Resultado: {'sem falhas' if not falhou else 'COM FALHAS'}")
    js.add(json.dumps({"ambiente": amb, "resumo_ambiente_b5": base.resumo_ambiente(amb), "ordem": ordem,
                       "total_alertas": total_alertas, "endpoints": resultados}, ensure_ascii=False, indent=2))

    conferir_sem_cookie(valor_cookie, txt, js)
    base.gravar(txt, js)
    print("\n".join(txt.linhas))
    if not porta_liberada:
        return SAIDA_AMBIENTE
    return SAIDA_DIVERGENCIA if falhou else SAIDA_OK


if __name__ == "__main__":
    rodar(principal)
