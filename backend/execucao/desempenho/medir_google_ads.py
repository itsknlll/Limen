"""Latência da Google Ads API, medida à parte (aba Desempenho, A6). NÃO entra na planilha.

Uso, na pasta backend com o venv ativo, DEPOIS do medir_endpoints e do seu login
OAuth no navegador (passos abaixo):

    DATABASE_URL=<url do banco limen_desempenho> python -m execucao.desempenho.medir_google_ads

O que é medido: porta.listar_campanhas(login_customer_id, customer_id, refresh_token),
a mesma chamada que o sincronizador do app faz (GAQL de leitura em campaign), com a
porta criada por obter_porta_google_ads() (as mesmas credenciais do app). O cliente
real cria um GoogleAdsClient a cada chamada, que renova o access token no OAuth do
Google antes da busca; por isso a latência inclui a rede até o Google, a renovação do
token e a busca. Não é o tempo do Limen e não entra na planilha.

Só leitura: não chama sincronizar (que gravaria campanhas e, com TokenRevogado,
apagaria o token). Nada é escrito no banco.

Login (feito por você, nunca por este script):
  1. DATABASE_URL=<url do limen_desempenho> uvicorn app.main:app --port 8080
  2. janela anônima → http://localhost:8080/api/oauth/google/login → entrar
  3. desligar o uvicorn
Isso cria no limen_desempenho um usuário novo (o do Google), com refresh token
cifrado e R1 a R3; o usuário da base dos endpoints não muda.
Sem exatamente um usuário com token (além do /dev/login), sai com 3.

Cota: intervalo de INTERVALO_S entre chamadas (fora do cronômetro); aquecimentos e
repetições da planilha (5 + 30 = 35 chamadas, longe do limite diário do acesso Test).
CotaExcedida ou TokenRevogado interrompem na hora (não insistir).
Sem repetição automática: cada chamada é uma tentativa só (o sincronizador do app
repete; aqui cada falha é registrada como falha).

Nunca impresso nem gravado: refresh token (nem cifrado), access token, client_id/secret,
e-mail, IDs da conta (customer_id e login_customer_id), URL com code, cabeçalho
Authorization, mensagem de exceção. Os logs da biblioteca google-ads ficam desligados.
Evidência por chamada: latência, status (ok ou o tipo da falha, com o código da API
quando houver) e quantidade de campanhas.

Saída: 0 ok · 1 alguma falha · 3 ambiente (conta não conectada, ordem errada) ·
4 evidência sensível · 5 erro inesperado.
Evidências: docs/evidencias/AAAA-MM-DD_desempenho_google_ads.txt e .json
"""

from __future__ import annotations

import json
import logging
import re
import time
from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, select

from ..comum import FUSO, SAIDA_AMBIENTE, SAIDA_DIVERGENCIA, SAIDA_EVIDENCIA_SENSIVEL, SAIDA_OK, Parada, Relatorio, rodar
from . import base

INTERVALO_S = 2.0
INTERROMPEM = ("CotaExcedida", "TokenRevogado")
BIBLIOTECAS_SILENCIADAS = ("google.ads.googleads", "google.auth", "grpc", "urllib3")


def silenciar_biblioteca() -> None:
    """Os logs da google-ads podem trazer cabeçalhos e corpo do pedido: desligados."""
    for nome in BIBLIOTECAS_SILENCIADAS:
        registro = logging.getLogger(nome)
        registro.setLevel(logging.CRITICAL + 1)
        registro.propagate = False


def conferir_ordem_e_ler_token(sessao) -> str:
    """Refresh token decifrado; nunca sai desta função para a evidência."""
    from app.api.rotas.dev import EMAIL_DEV
    from app.modelos import Regra, Usuario
    from app.servicos.cifra import decifrar

    if not sessao.scalar(select(func.count(Regra.id)).where(Regra.codigo.like("P%"))):
        raise Parada(SAIDA_AMBIENTE, "Rode o medir_endpoints antes (regras P* do DE-03 ausentes).")
    conectados = sessao.scalars(
        select(Usuario).where(Usuario.refresh_token_cifrado.is_not(None), Usuario.email != EMAIL_DEV)
    ).all()
    if len(conectados) != 1:
        raise Parada(
            SAIDA_AMBIENTE,
            f"Conta Google não conectada no {base.BANCO_DESEMPENHO} ({len(conectados)} usuário(s) com token; "
            "precisa ser 1). Faça o login no navegador (passos no topo deste script); o OAuth não é feito aqui.",
        )
    return decifrar(conectados[0].refresh_token_cifrado)


def chamar(porta, ids: tuple[str, str], token: str) -> tuple[int | None, str, int | None]:
    """(latência em ns, status, quantidade de campanhas). Só o tipo da falha, nunca a mensagem."""
    from app.servicos.erros import ErroGoogleAds

    customer_id, login_customer_id = ids
    inicio = time.perf_counter_ns()
    try:
        campanhas = porta.listar_campanhas(
            login_customer_id=login_customer_id, customer_id=customer_id, refresh_token=token
        )
    except ErroGoogleAds as erro:
        fim = time.perf_counter_ns()
        codigo = getattr(erro, "codigo", None)
        return fim - inicio, type(erro).__name__ + (f" [{codigo}]" if codigo else ""), None
    except Exception as erro:  # noqa: BLE001 — só o tipo; sem resposta, sem latência
        return None, type(erro).__name__, None
    fim = time.perf_counter_ns()
    return fim - inicio, "ok", len(campanhas)


def executar_chamadas(porta, ids, token, plano: base.Plano, espera=time.sleep) -> tuple[list[dict], str | None]:
    """(execuções, tipo que interrompeu ou None). Espera INTERVALO_S entre chamadas, fora do cronômetro."""
    execucoes: list[dict] = []
    total = plano.aquecimentos + plano.repeticoes
    for n in range(1, total + 1):
        if n > 1:
            espera(INTERVALO_S)
        ns, status, quantidade = chamar(porta, ids, token)
        execucoes.append({"n": n, "medida": n > plano.aquecimentos, "latencia_ns": ns, "status": status,
                          "campanhas": quantidade})
        print(f"chamada {n} de {total}: {status}")
        tipo = status.split(" ")[0]
        if tipo in INTERROMPEM:
            return execucoes, tipo
    return execucoes, None


def _numero_isolado(valor: str) -> re.Pattern[str]:
    # Sem dígito colado dos dois lados: um ID de 10 dígitos dentro de um número maior
    # (uma latência em ns, por exemplo) não conta.
    return re.compile(rf"(?<!\d){re.escape(valor)}(?!\d)")


def conferir_sem_token(token: str, ids: tuple[str, str], *relatorios: Relatorio) -> None:
    """Para com 4 se o refresh token, o customer_id ou o login_customer_id aparecerem."""
    textos = ["\n".join(r.linhas) for r in relatorios]
    if token and any(token in t for t in textos):
        raise Parada(SAIDA_EVIDENCIA_SENSIVEL, "Evidências NÃO gravadas: o refresh token apareceria.")
    for nome, valor in zip(("customer_id", "login_customer_id"), ids):
        if valor and any(_numero_isolado(valor).search(t) for t in textos):
            raise Parada(SAIDA_EVIDENCIA_SENSIVEL, f"Evidências NÃO gravadas: o {nome} apareceria.")


def _ms(ns: int | None) -> str:
    return "—" if ns is None else str(base.arredondar(Decimal(ns) / base.NS_POR_MS))


def principal() -> int:
    base.url_desempenho()
    plano = base.ler_plano()
    txt, js = Relatorio("desempenho_google_ads.txt"), Relatorio("desempenho_google_ads.json")
    for linha in base.cabecalho(
        "execucao/desempenho/medir_google_ads.py", "Desempenho — latência da Google Ads API (à parte)"
    ):
        txt.add(linha)
    base.conferir_aplicacao_usa_desempenho()
    silenciar_biblioteca()

    from app.api.deps import obter_porta_google_ads
    from app.config import configuracoes
    from app.db import SessaoLocal

    with SessaoLocal() as sessao:
        base.conferir_banco_conectado(sessao)
        token = conferir_ordem_e_ler_token(sessao)
        servidor = base.versao_servidor(sessao)
    ids = configuracoes.ids_google_ads  # (customer_id, login_customer_id); não impressos
    porta = obter_porta_google_ads()  # mesma porta do app (credenciais do client_secret.json)

    execucoes, interrompido = executar_chamadas(porta, ids, token, plano)

    ok_medidas = [e["latencia_ns"] for e in execucoes if e["medida"] and e["status"] == "ok"]
    falhas = [e for e in execucoes if e["status"] != "ok"]
    est = base.estatisticas(ok_medidas) if len(ok_medidas) >= 2 else None

    txt.add("Ambiente:")
    for chave, valor in base.ambiente(servidor).items():
        txt.add(f"  {chave}: {valor}")
    txt.add("")
    txt.add("ATENÇÃO: latência da Google Ads API medida à parte (A6 da aba Desempenho). Inclui a rede até o")
    txt.add("Google, a renovação do access token (um GoogleAdsClient por chamada, como no app) e a busca GAQL.")
    txt.add("NÃO é o tempo do Limen e NÃO entra na planilha.")
    txt.add("")
    txt.add("Chamada: porta.listar_campanhas (obter_porta_google_ads, a do app), só leitura; conta de teste")
    txt.add(f"(IDs não registrados); intervalo de {INTERVALO_S} s entre chamadas; sem repetição automática.")
    txt.add(f"Plano: {plano.aquecimentos} aquecimentos + {plano.repeticoes} medidas (os mesmos números da planilha)")
    txt.add("")
    txt.add("  n  tipo        latência(ms)  status                         campanhas")
    for e in execucoes:
        txt.add(f"{e['n']:>3}  {'medida' if e['medida'] else 'aquec.':<10} {_ms(e['latencia_ns']):>12}  "
                f"{e['status']:<30} {'—' if e['campanhas'] is None else e['campanhas']}")
    txt.add("")
    if est:
        txt.add(f"Medidas ok: {est.n} · média {base.arredondar(est.media_ms)} ms · mediana "
                f"{base.arredondar(est.mediana_ms)} ms · desvio {base.arredondar(est.desvio_ms)} ms · p95 "
                f"{base.arredondar(est.p95_ms)} ms · mín {base.arredondar(est.minimo_ms)} ms · máx "
                f"{base.arredondar(est.maximo_ms)} ms")
    else:
        txt.add("Medidas ok insuficientes para estatística.")
    quantidades = sorted({e["campanhas"] for e in execucoes if e["campanhas"] is not None})
    txt.add(f"Campanhas devolvidas (valores distintos): {quantidades}")
    txt.add(f"Falhas: {len(falhas)}" + (f" · interrompido por {interrompido}" if interrompido else ""))
    txt.add("Banco: nada gravado (sem sincronizar).")

    js.add(json.dumps({
        "atencao": "latência da Google Ads API, inclui rede até o Google; não entra na planilha",
        "intervalo_s": INTERVALO_S,
        "execucoes": execucoes,
        "estatisticas": None if est is None else {
            "n": est.n, "media_ms": str(est.media_ms), "mediana_ms": str(est.mediana_ms),
            "desvio_ms": str(est.desvio_ms), "p95_ms": str(est.p95_ms),
            "minimo_ms": str(est.minimo_ms), "maximo_ms": str(est.maximo_ms),
        },
        "interrompido_por": interrompido,
        "gerado_em": datetime.now(FUSO).isoformat(timespec="seconds"),
    }, ensure_ascii=False, indent=2))

    conferir_sem_token(token, ids, txt, js)
    del token
    base.gravar(txt, js)  # padrões: e-mail, 1//, ya29., Bearer, ?code=, *_token, hostname...
    print("\n".join(txt.linhas))
    return SAIDA_OK if not falhas else SAIDA_DIVERGENCIA


if __name__ == "__main__":
    rodar(principal)
