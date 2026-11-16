"""Execução formal da aba 'Integração' (IN-01 a IN-11 e IN-02b).

Uso: DATABASE_URL=<url do limen_execucao> python -m execucao.executar_integracao

Roda DEPOIS dos passos manuais, no limen_execucao (uvicorn e Vite com a mesma URL):
  IN-01: login com o Google no navegador (cria o usuário Google e R1 a R3);
  IN-02: "Sincronizar" na tela Campanhas (chamada real à Google Ads API).
Depois deste script, a parte do dashboard do IN-10 é conferida no navegador.

Usuários (todos neste banco):
- Google (IN-01): IN-01, IN-02, IN-02b, IN-10, IN-11;
- da execução (preparar): IN-07, numa campanha nova sem métricas;
- de apoio, criados aqui com R1 a R3: um por caso em IN-03 a IN-06 e um para
  IN-08/IN-09 (o IN-04 apaga o token do usuário; a R4 do IN-08 não entra no
  usuário da execução).
IN-03 a IN-06 passam pelo endpoint real POST /campanhas/sincronizar com a porta
do Google trocada por um dublê (a tabela define esses casos como "Simulada");
o sincronizador espera de verdade no IN-05 (1 + 2 + 4 s).
Conferência de R1 a R3 no início (usuários Google e da execução) e no fim (todos).

IDs das campanhas reais, customer_id e login_customer_id escritos aqui: não são
segredos e já constam de arquivos versionados (tests/conftest.py, .env.example).

Saída: 0 todos conferem · 1 algum não confere · 2 regras diferentes · 3 · 4 · 5.
Evidências: docs/evidencias/AAAA-MM-DD_execucao_integracao.txt e .json
"""

from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient
from openpyxl import load_workbook
from sqlalchemy import func, select

from .comum import (
    EMAIL_EXECUCAO,
    FUSO,
    PLANILHA,
    SAIDA_AMBIENTE,
    SAIDA_DIVERGENCIA,
    SAIDA_OK,
    SAIDA_REGRAS_DIFERENTES,
    Parada,
    Relatorio,
    cabecalho,
    conferir_aplicacao_usa_execucao,
    conferir_banco_conectado,
    gravar_juntos,
    rodar,
    url_execucao,
)
from .conferir_regras import conferir_usuario
from .executar_cenarios import LIMITE_ALERTAS, _corpo, _get

IDS_REAIS = {"A": 24444020070, "B": 24464752468, "C": 24458906837}
STATUS_REAL = {"A": "ENABLED", "B": "ENABLED", "C": "PAUSED"}
CUSTOMER_ID, LOGIN_CUSTOMER_ID = "4327030343", "1137051091"
LOTE_IN02B = "in02b-s20261112"
DIA_IN07 = date(2026, 11, 1)
DIA_IN08 = date(2026, 11, 1)
DIA_IN10 = date(2026, 11, 12)  # fora do período do IN-02b (13/10 a 11/11/2026)
NOME_CAMPANHA_IN07 = "Execução · IN-07"
LOGGER_SINC = "app.servicos.sincronizacao.sincronizador"
DOMINIO_SINTETICO = "@limen.local"
# Usuários de apoio (e-mails nunca impressos).
APOIO = {caso: f"execucao-{caso.lower()}{DOMINIO_SINTETICO}" for caso in ("IN-03", "IN-04", "IN-05", "IN-06", "IN-08")}
ORDEM = ("IN-01", "IN-02", "IN-02b", "IN-03", "IN-04", "IN-05", "IN-06", "IN-07", "IN-08", "IN-09", "IN-10", "IN-11")


@dataclass
class Caso:
    id: str
    evidencia: str = "este relatório"
    obtido: list[str] = field(default_factory=list)
    falhas: int = 0
    pendente: str | None = None

    def checar(self, condicao: bool, texto: str) -> bool:
        if not condicao:
            self.falhas += 1
        self.obtido.append(f"[{'ok' if condicao else 'FALHOU'}] {texto}")
        return condicao

    def nota(self, texto: str) -> None:
        self.obtido.append(f"[nota] {texto}")

    @property
    def confere(self) -> bool:
        return self.falhas == 0 and any(l.startswith("[ok]") for l in self.obtido)


class PortaDuble:
    """Porta do Google que falha em sequência e depois responde. Não guarda o token."""

    def __init__(self, falhas=()):
        self.falhas = list(falhas)
        self.chamadas = 0

    def listar_campanhas(self, login_customer_id, customer_id, refresh_token):
        from app.servicos.sincronizacao.interface import CampanhaGoogle

        self.chamadas += 1
        if self.falhas:
            raise self.falhas.pop(0)
        return [CampanhaGoogle(IDS_REAIS[k], f"Limen {k} (dublê)", STATUS_REAL[k], None) for k in "ABC"]


class Coletor(logging.Handler):
    def __init__(self):
        super().__init__(logging.INFO)
        self.mensagens: list[str] = []

    def emit(self, registro):
        self.mensagens.append(registro.getMessage())


def _cliente(usuario_id: int, porta=None) -> TestClient:
    from app.api.deps import obter_porta_google_ads, obter_usuario_atual
    from app.main import criar_app

    app = criar_app()
    app.dependency_overrides[obter_usuario_atual] = lambda: usuario_id
    if porta is not None:
        app.dependency_overrides[obter_porta_google_ads] = lambda: porta
    return TestClient(app)


def _avaliar(cliente, corpo: dict) -> dict | None:
    r = cliente.post("/avaliacoes", json=corpo)
    return r.json() if r.status_code == 201 else None


def _dec(v) -> Decimal | None:
    return None if v is None else Decimal(str(v))


def _texto_dec(v: Decimal | None) -> str:
    return "N/A" if v is None else format(v.normalize(), "f")


def _tem_chave_token(obj) -> bool:
    if isinstance(obj, dict):
        return any("token" in k.lower() or _tem_chave_token(v) for k, v in obj.items())
    if isinstance(obj, list):
        return any(_tem_chave_token(v) for v in obj)
    return False


def _contar(modelo_id, *filtros) -> int:
    from app.db import SessaoLocal

    with SessaoLocal() as s:
        return s.scalar(select(func.count(modelo_id)).where(*filtros))


def _campanhas_de(usuario_id: int) -> int:
    from app.db import SessaoLocal
    from app.modelos import Campanha, ContaGoogleAds

    with SessaoLocal() as s:
        return s.scalar(select(func.count(Campanha.id)).join(Campanha.conta)
                        .where(ContaGoogleAds.usuario_id == usuario_id))


def _tem_token(usuario_id: int) -> bool:
    from app.db import SessaoLocal
    from app.modelos import Usuario

    with SessaoLocal() as s:
        return bool(s.scalar(select(Usuario.refresh_token_cifrado.is_not(None)).where(Usuario.id == usuario_id)))


def _linhas_planilha() -> dict[str, dict]:
    aba = load_workbook(PLANILHA, read_only=True)["Integração"]
    return {l[0]: {"origem": l[1], "cenario": l[2], "precondicao": l[3], "esperado": l[4]}
            for l in aba.iter_rows(min_row=5, max_row=16, values_only=True)}


# --- preparação dos usuários --------------------------------------------------

def _localizar() -> tuple[int, int]:
    from app.db import SessaoLocal
    from app.modelos import Usuario

    with SessaoLocal() as s:
        conferir_banco_conectado(s)
        execucao = list(s.scalars(select(Usuario.id).where(Usuario.email == EMAIL_EXECUCAO)))
        google = list(s.scalars(select(Usuario.id).where(Usuario.email.not_like(f"%{DOMINIO_SINTETICO}"))))
        apoio = s.scalar(select(func.count(Usuario.id)).where(Usuario.email.in_(APOIO.values())))
    if len(execucao) != 1:
        raise Parada(SAIDA_AMBIENTE, "Usuário da execução ausente: rode execucao.preparar antes.")
    if len(google) != 1:
        raise Parada(SAIDA_AMBIENTE, f"Esperado 1 usuário do login Google (IN-01); há {len(google)}.")
    if apoio:
        raise Parada(SAIDA_AMBIENTE, "Usuários de apoio já existem: a integração já rodou neste banco.")
    return execucao[0], google[0]


def _criar_apoio(caso: str, com_token: bool, com_campanha: bool) -> tuple[int, int | None]:
    from app.db import SessaoLocal
    from app.modelos import Campanha, ContaGoogleAds, Usuario
    from app.servicos.cifra import cifrar
    from app.servicos.regras import criar_regras_padrao

    with SessaoLocal() as s:
        u = Usuario(email=APOIO[caso], nome=f"Apoio {caso}",
                    refresh_token_cifrado=cifrar("valor-ficticio-da-execucao") if com_token else None)
        s.add(u)
        s.commit()
        criar_regras_padrao(s, u.id)
        campanha_id = None
        if com_campanha:
            conta = ContaGoogleAds(usuario_id=u.id, customer_id="0000000008", nome=f"Conta sintética {caso}")
            s.add(conta)
            s.flush()
            camp = Campanha(conta_id=conta.id, google_campaign_id=8, nome=f"Execução · {caso}", status="ENABLED")
            s.add(camp)
            s.commit()
            campanha_id = camp.id
        return u.id, campanha_id


# --- casos ----------------------------------------------------------------------

def in01(google_id: int) -> Caso:
    from app.db import SessaoLocal
    from app.modelos import Usuario

    caso = Caso("IN-01", evidencia="prints do login no navegador (2026-11-16_IN-01_*) e este relatório")
    with SessaoLocal() as s:
        cifrado = s.scalar(select(Usuario.refresh_token_cifrado).where(Usuario.id == google_id))
    caso.checar(cifrado is not None and cifrado.startswith("gAAAAA"),
                "refresh token guardado no backend, cifrado (formato Fernet)")
    with _cliente(google_id) as c:
        r = c.get("/eu")
    if caso.checar(r.status_code == 200, f"GET /eu → {r.status_code}"):
        corpo = r.json()
        caso.checar(corpo["google_conectado"] is True, "google_conectado = true")
        caso.checar(not _tem_chave_token(corpo) and cifrado is not None and cifrado not in r.text,
                    "a resposta ao frontend não traz token (nenhuma chave com 'token', nem o texto cifrado)")
        conta = corpo["conta_google_ads"] or {}
        caso.checar(conta == {"customer_id": CUSTOMER_ID, "login_customer_id": LOGIN_CUSTOMER_ID},
                    f"conta de teste vinculada: customer_id {conta.get('customer_id')}, MCC {conta.get('login_customer_id')}")
    caso.nota("a conta fica vinculada na primeira sincronização (IN-02); antes dela, GET /eu traz conta null")
    return caso


def in02(google_id: int) -> tuple[Caso, dict[str, int]]:
    from app.modelos import MetricaDiaria

    caso = Caso("IN-02", evidencia="print da tela Campanhas após Sincronizar (2026-11-16_IN-02_*), "
                                   "prints do Playground (2026-11-12_IN-02_campanhas_api_parte*.png) e este relatório")
    with _cliente(google_id) as c:
        campanhas = _get(c, "/campanhas")
    hoje = datetime.now(FUSO).date()
    por_google = {x["google_campaign_id"]: x for x in campanhas}
    ids: dict[str, int] = {}
    caso.checar(len(campanhas) == 3, f"{len(campanhas)} campanhas persistidas")
    for k, gid in IDS_REAIS.items():
        x = por_google.get(gid)
        if not caso.checar(x is not None, f"campanha {k}: ID real {gid} presente"):
            continue
        ids[k] = x["id"]
        sinc = datetime.fromisoformat(x["sincronizada_em"]).astimezone(FUSO).date() if x["sincronizada_em"] else None
        caso.checar(x["status"] == STATUS_REAL[k] and bool(x["nome"]) and sinc == hoje,
                    f"campanha {k}: '{x['nome']}', {x['status']}, sincronizada em {sinc}")
    n = _contar(MetricaDiaria.id, MetricaDiaria.origem == "google_ads")
    caso.checar(n == 0, f"métricas de origem google_ads gravadas: {n}")
    caso.nota("a sincronização pede à API só a estrutura das campanhas (ID, nome, status, orçamento), não as "
              "métricas. A prova de que as métricas da conta de teste vêm zeradas são os prints do Playground "
              "de 12/11 (2026-11-12_IN-02_campanhas_api_parte*.png): é propriedade da conta de teste, não do "
              "código. Limitação declarada.")
    return caso, ids


def _alertas_do_motor(metricas: dict[str, list], ids: dict[str, int]) -> set[tuple]:
    """Oráculo independente: motor puro com os limiares lidos da planilha."""
    from app.motor import RegistroMetricas, avaliar
    from tests.tabela_congelada import carregar_regras

    regras = carregar_regras()
    saida = set()
    for k, linhas in metricas.items():
        for m in linhas:
            reg = RegistroMetricas(m["impressoes"], m["cliques"], _dec(m["custo"]), _dec(m["conversoes"]))
            saida |= {(ids[k], m["data"], cod) for cod in avaliar(reg, regras).disparadas}
    return saida


def _por_campanha(alertas: set[tuple], ids: dict[str, int]) -> dict[str, int]:
    return {k: sum(1 for a in alertas if a[0] == ids[k]) for k in "ABC"}


def in02b(google_id: int, ids: dict[str, int]) -> Caso:
    caso = Caso("IN-02b")
    if not caso.checar(len(ids) == 3, "pré-condição: IN-02 com as 3 campanhas"):
        return caso
    with _cliente(google_id) as c:
        r = c.post("/dev/metricas-sinteticas")
        if not caso.checar(r.status_code == 200, f"POST /dev/metricas-sinteticas → {r.status_code}"):
            return caso
        sem = r.json()
        caso.checar(sem["lote"] == LOTE_IN02B and len(sem["campanhas"]) == 3
                    and all(x["inseridos"] == 30 and x["ja_existentes"] == 0 for x in sem["campanhas"]),
                    f"lote {sem['lote']}, {sem['inicio']} a {sem['fim']}: "
                    + ", ".join(f"{x['google_campaign_id']} {x['status']} {x['inseridos']} inseridos" for x in sem["campanhas"]))
        metricas = {k: _get(c, f"/campanhas/{ids[k]}/metricas") for k in "ABC"}
        ativas = _avaliar(c, {})
        alertas1 = {(a["campanha_id"], a["data"], a["regra_codigo"]) for a in _get(c, "/alertas", {"limite": LIMITE_ALERTAS})}
        pausadas = _avaliar(c, {"incluir_pausadas": True})
        alertas2 = {(a["campanha_id"], a["data"], a["regra_codigo"]) for a in _get(c, "/alertas", {"limite": LIMITE_ALERTAS})}
    for k in "ABC":
        caso.checar(len(metricas[k]) == 30 and {(m["origem"], m["lote"]) for m in metricas[k]} == {("sintetica", LOTE_IN02B)},
                    f"campanha {k} (ID real {IDS_REAIS[k]}): {len(metricas[k])} dias, origem sintetica, lote {LOTE_IN02B}")
    esp1 = _alertas_do_motor({k: metricas[k] for k in "AB"}, ids)
    esp2 = _alertas_do_motor(metricas, ids)
    caso.checar(ativas is not None and ativas["registros_avaliados"] == 60 and ativas["registros_rejeitados"] == 0
                and ativas["alertas_gerados"] == len(esp1),
                f"POST /avaliacoes {{}}: {ativas and ativas['registros_avaliados']} avaliados, "
                f"{ativas and ativas['registros_rejeitados']} rejeitados, {ativas and ativas['alertas_gerados']} alertas novos")
    caso.checar(alertas1 == esp1 and _por_campanha(alertas1, ids) == {"A": 9, "B": 9, "C": 0},
                f"alertas = motor puro com os limiares da planilha ({len(alertas1)} = {len(esp1)}); por campanha {_por_campanha(alertas1, ids)}")
    caso.checar(pausadas is not None and pausadas["registros_avaliados"] == 90
                and pausadas["alertas_gerados"] == len(esp2 - esp1) and pausadas["alertas_ja_existentes"] == len(esp1),
                f"POST /avaliacoes {{incluir_pausadas: true}}: {pausadas and pausadas['registros_avaliados']} avaliados, "
                f"{pausadas and pausadas['alertas_gerados']} novos, {pausadas and pausadas['alertas_ja_existentes']} já existentes")
    caso.checar(alertas2 == esp2 and _por_campanha(alertas2, ids) == {"A": 9, "B": 9, "C": 9},
                f"com pausadas: {len(alertas2)} = {len(esp2)}; por campanha {_por_campanha(alertas2, ids)}")
    return caso


def in03_a_06() -> list[Caso]:
    from app.servicos.erros import ApiIndisponivel, CotaExcedida, TokenExpirado, TokenRevogado

    coletor = Coletor()
    logger = logging.getLogger(LOGGER_SINC)
    logger.addHandler(coletor)
    logger.setLevel(logging.INFO)
    casos = []
    try:
        # IN-03
        uid, _ = _criar_apoio("IN-03", com_token=True, com_campanha=False)
        caso = Caso("IN-03")
        porta = PortaDuble([TokenExpirado("simulado: falha temporária ao renovar o access token")])
        coletor.mensagens.clear()
        with _cliente(uid, porta) as c:
            r = c.post("/campanhas/sincronizar")
        caso.checar(r.status_code == 200 and r.json().get("campanhas_sincronizadas") == 3,
                    f"POST /campanhas/sincronizar → {r.status_code}, {r.json().get('campanhas_sincronizadas')} campanhas")
        caso.checar(porta.chamadas == 2, f"chamadas à porta: {porta.chamadas} (1 falha + 1 repetição)")
        caso.checar(_campanhas_de(uid) == 3 and _tem_token(uid), f"{_campanhas_de(uid)} campanhas gravadas; refresh token mantido")
        caso.checar(any(m.startswith("IN-03") for m in coletor.mensagens), "falha registrada no log (IN-03 token_expirado)")
        caso.nota("renovação simulada: o dublê falha na 1ª chamada e responde na 2ª; a renovação de verdade é feita pela biblioteca google-ads")
        casos.append(caso)

        # IN-04
        uid, _ = _criar_apoio("IN-04", com_token=True, com_campanha=False)
        caso = Caso("IN-04")
        porta = PortaDuble([TokenRevogado("simulado: invalid_grant", codigo="invalid_grant")])
        coletor.mensagens.clear()
        with _cliente(uid, porta) as c:
            r = c.post("/campanhas/sincronizar")
            eu = _get(c, "/eu")
        caso.checar(r.status_code == 409 and r.json().get("tipo") == "token_google_revogado",
                    f"POST /campanhas/sincronizar → {r.status_code}, tipo {r.json().get('tipo')}")
        caso.checar(porta.chamadas == 1, f"chamadas à porta: {porta.chamadas}")
        caso.checar(_campanhas_de(uid) == 0, f"nenhum dado parcial: {_campanhas_de(uid)} campanhas gravadas")
        caso.checar(not _tem_token(uid) and eu["google_conectado"] is False,
                    "usuário sinalizado para reautorizar: refresh token apagado, GET /eu com google_conectado = false")
        caso.checar(any(m.startswith("IN-04") for m in coletor.mensagens), "erro de autenticação registrado no log (IN-04)")
        casos.append(caso)

        # IN-05
        uid, _ = _criar_apoio("IN-05", com_token=True, com_campanha=False)
        caso = Caso("IN-05")
        porta = PortaDuble([ApiIndisponivel("simulado: UNAVAILABLE", codigo="UNAVAILABLE") for _ in range(4)])
        coletor.mensagens.clear()
        inicio = time.monotonic()
        with _cliente(uid, porta) as c:
            r = c.post("/campanhas/sincronizar")
        decorrido = time.monotonic() - inicio
        esperas = [int(s) for m in coletor.mensagens for s in re.findall(r"aguardando (\d+)s", m)]
        caso.checar(r.status_code == 503 and r.json().get("tipo") == "google_ads_indisponivel",
                    f"4 falhas seguidas: POST → {r.status_code}, tipo {r.json().get('tipo')}")
        caso.checar(porta.chamadas == 4 and esperas == [1, 2, 4] and decorrido >= 7,
                    f"{porta.chamadas} chamadas (1 + 3 novas tentativas), esperas {esperas} s, {decorrido:.1f} s no total")
        caso.checar(_campanhas_de(uid) == 0 and any("esgotadas" in m for m in coletor.mensagens),
                    f"falha registrada no log; {_campanhas_de(uid)} campanhas gravadas")
        porta = PortaDuble([ApiIndisponivel("simulado: UNAVAILABLE", codigo="UNAVAILABLE") for _ in range(3)])
        with _cliente(uid, porta) as c:
            r = c.post("/campanhas/sincronizar")
        caso.checar(r.status_code == 200 and porta.chamadas == 4 and _campanhas_de(uid) == 3,
                    f"3 falhas e sucesso na 4ª chamada: POST → {r.status_code}, {_campanhas_de(uid)} campanhas")
        with _cliente(uid, PortaDuble()) as c:
            r = c.post("/campanhas/sincronizar")
        caso.checar(r.status_code == 200 and _campanhas_de(uid) == 3,
                    f"nova sincronização: {_campanhas_de(uid)} campanhas (nenhum registro duplicado)")
        casos.append(caso)

        # IN-06
        uid, _ = _criar_apoio("IN-06", com_token=True, com_campanha=False)
        caso = Caso("IN-06")
        codigo = "quota_error=RESOURCE_EXHAUSTED"
        porta = PortaDuble([CotaExcedida("simulado: cota excedida", codigo=codigo)])
        coletor.mensagens.clear()
        with _cliente(uid, porta) as c:
            r = c.post("/campanhas/sincronizar")
        caso.checar(r.status_code == 503 and r.json().get("tipo") == "cota_excedida"
                    and r.headers.get("Retry-After") == "3600",
                    f"POST → {r.status_code}, tipo {r.json().get('tipo')}, Retry-After {r.headers.get('Retry-After')} s (sincronização adiada)")
        caso.checar(porta.chamadas == 1 and _campanhas_de(uid) == 0, f"{porta.chamadas} chamada (sem repetir), {_campanhas_de(uid)} campanhas")
        caso.checar(codigo in r.json().get("detail", "") and any(m.startswith("IN-06") and codigo in m for m in coletor.mensagens),
                    f"código devolvido pela API registrado no log e na resposta: {codigo}")
        casos.append(caso)
    finally:
        logger.removeHandler(coletor)
    return casos


def _razoes_planilha(r) -> tuple[Decimal | None, Decimal | None]:
    """Fórmulas das colunas H e I da planilha, em Decimal (CTR em %: a planilha guarda fração)."""
    ctr = None if r.impressoes is None or r.cliques is None or r.impressoes == 0 else Decimal(r.cliques) / Decimal(r.impressoes) * 100
    cpc = None if r.custo is None or r.cliques is None or r.cliques == 0 else r.custo / Decimal(r.cliques)
    return ctr, cpc


def in07(execucao_id: int, cenarios) -> Caso:
    from app.db import SessaoLocal
    from app.modelos import Campanha, ContaGoogleAds
    from app.motor import calcular_cpc, calcular_ctr

    caso = Caso("IN-07")
    with SessaoLocal() as s:
        conta = s.scalar(select(ContaGoogleAds).where(ContaGoogleAds.usuario_id == execucao_id))
        camp = Campanha(conta_id=conta.id, google_campaign_id=7, nome=NOME_CAMPANHA_IN07, status="ENABLED")
        s.add(camp)
        s.commit()
        campanha_id = camp.id
    validos = [x for x in cenarios if x.aceito_esperado]
    corpo = {"lote": "tabela-v1.0", "registros": [
        _corpo(x.registro, DIA_IN07 + timedelta(days=n))["registros"][0] for n, x in enumerate(validos)]}
    with _cliente(execucao_id) as c:
        caso.checar(_get(c, f"/campanhas/{campanha_id}/metricas") == [], "pré-condição: campanha nova, sem métricas")
        r = c.post(f"/campanhas/{campanha_id}/metricas", json=corpo)
        metricas = _get(c, f"/campanhas/{campanha_id}/metricas")
    caso.checar(r.status_code == 201 and r.json().get("inseridos") == len(validos),
                f"POST /campanhas/{{id}}/metricas (lote de {len(validos)} casos válidos) → {r.status_code}, {r.json().get('inseridos')} inseridos")
    caso.checar(len(metricas) == len(validos) and {(m["origem"], m["lote"]) for m in metricas} == {("sintetica", "tabela-v1.0")},
                f"{len(metricas)} registros persistidos, origem sintetica")
    por_dia = {m["data"]: m for m in metricas}
    diferencas = []
    for n, x in enumerate(validos):
        m = por_dia.get((DIA_IN07 + timedelta(days=n)).isoformat(), {})
        ctr_p, cpc_p = _razoes_planilha(x.registro)
        ctr_b, cpc_b = _dec(m.get("ctr")), _dec(m.get("cpc"))
        ok = ctr_b == ctr_p == calcular_ctr(x.registro) and cpc_b == cpc_p == calcular_cpc(x.registro)
        caso.nota(f"{x.id}: CTR banco {_texto_dec(ctr_b)} | planilha {_texto_dec(ctr_p)} · "
                  f"CPC banco {_texto_dec(cpc_b)} | planilha {_texto_dec(cpc_p)}{'' if ok else '  ← DIFERENTE'}")
        if not ok:
            diferencas.append(x.id)
    caso.checar(not diferencas, f"CTR e CPC do banco (view) = fórmula da planilha = motor: {len(validos) - len(diferencas)} de {len(validos)}")
    return caso


def in08_in09(cenarios) -> tuple[Caso, Caso]:
    c08, c09 = Caso("IN-08"), Caso("IN-09")
    uid, campanha_id = _criar_apoio("IN-08", com_token=False, com_campanha=True)
    fm03 = next(x for x in cenarios if x.id == "FM-03")
    nova = {"codigo": "R4", "nome": "CTR abaixo de 2%", "ativa": True,
            "condicoes": [{"metrica": "ctr", "operador": "<", "limiar": "2"}]}
    with _cliente(uid) as c:
        r = c.post("/regras", json=nova)
        c08.checar(r.status_code == 201, f"POST /regras (R4: CTR < 2%) → {r.status_code}")
        regra_id = r.json().get("id") if r.status_code == 201 else None
        regras = _get(c, "/regras")
        r4 = [x for x in regras if x["codigo"] == "R4"]
        c08.checar(len(r4) == 1 and r4[0]["ativa"] and Decimal(r4[0]["condicoes"][0]["limiar"]) == 2,
                   f"regra persistida: GET /regras traz R4 ativa, limiar {r4[0]['condicoes'][0]['limiar'] if r4 else '—'}")
        c.post(f"/campanhas/{campanha_id}/metricas", json=_corpo(fm03.registro, DIA_IN08))
        avaliacao = _avaliar(c, {"campanha_id": campanha_id})
        alertas = _get(c, "/alertas", {"campanha_id": campanha_id, "limite": LIMITE_ALERTAS})
        c08.checar(avaliacao is not None and {a["regra_codigo"] for a in alertas} == {"R4"},
                   f"usada na próxima avaliação: registro do FM-03 (CTR 1,01%) gerou {[a['regra_codigo'] for a in alertas]}")
        c08.nota("a criação passa pelo mesmo POST /regras que a tela de Regras usa (formulário conferido no navegador na Fase 3)")

        antes = len(regras)
        for limiar in ("-1", ""):
            r = c.post("/regras", json={**nova, "codigo": "R5", "condicoes": [{"metrica": "ctr", "operador": "<", "limiar": limiar}]})
            corpo = r.json()
            c09.checar(r.status_code == 400 and corpo.get("tipo") == "validacao" and bool(corpo.get("detail")),
                       f"limiar {limiar!r}: POST /regras → {r.status_code}, tipo {corpo.get('tipo')} (mensagem de validação presente; texto não reproduzido)")
        depois = _get(c, "/regras")
        c09.checar(len(depois) == antes and not any(x["codigo"] == "R5" for x in depois),
                   f"nada persistido: {antes} regras antes e {len(depois)} depois, nenhuma R5")
        if regra_id is not None:
            r = c.delete(f"/regras/{regra_id}")
            c08.nota(f"R4 desativada depois do caso (DELETE → {r.status_code}), para R1 a R3 voltarem a ser as únicas ativas")
    return c08, c09


def in10_in11(google_id: int, ids: dict[str, int], cenarios) -> tuple[Caso, Caso]:
    c10 = Caso("IN-10", evidencia="este relatório (API) e print da tela Alertas (2026-11-16_IN-10_*)")
    c11 = Caso("IN-11")
    if not (c10.checar("A" in ids, "pré-condição: campanha A sincronizada") and c11.checar("A" in ids, "pré-condição: campanha A sincronizada")):
        return c10, c11
    a, d = ids["A"], DIA_IN10.isoformat()
    ra02 = next(x for x in cenarios if x.id == "RA-02")
    filtro = {"campanha_id": a, "inicio": d, "fim": d}
    with _cliente(google_id) as c:
        r = c.post(f"/campanhas/{a}/metricas", json=_corpo(ra02.registro, DIA_IN10))
        c10.checar(r.status_code == 201, f"RA-02 gravado na campanha A em {d} → {r.status_code}")
        av1 = _avaliar(c, filtro)
        dia1 = _get(c, "/alertas", {**filtro, "limite": LIMITE_ALERTAS})
        total1 = len(_get(c, "/alertas", {"limite": LIMITE_ALERTAS}))
        av2 = _avaliar(c, filtro)
        dia2 = _get(c, "/alertas", {**filtro, "limite": LIMITE_ALERTAS})
        total2 = len(_get(c, "/alertas", {"limite": LIMITE_ALERTAS}))
    c10.checar(av1 is not None and av1["registros_avaliados"] == 1 and av1["alertas_gerados"] == 1,
               f"POST /avaliacoes (campanha A, {d}): {av1 and av1['registros_avaliados']} avaliado, {av1 and av1['alertas_gerados']} alerta novo")
    if c10.checar(len(dia1) == 1, f"GET /alertas do dia: {len(dia1)} alerta"):
        x = dia1[0]
        medido = x["valores_medidos"].get("ctr")
        c10.checar(x["campanha_id"] == a and bool(x["campanha_nome"]) and x["regra_codigo"] == "R1"
                   and _dec(medido) == Decimal("0.5") and x["data"] == d,
                   f"campanha '{x['campanha_nome']}', regra {x['regra_codigo']} '{x['regra_nome']}', "
                   f"valor medido CTR {_texto_dec(_dec(medido))}%, data {x['data']}")
    c10.pendente = f"dashboard: abrir /alertas?campanha={a}&inicio={d}&fim={d} e conferir o alerta"
    c11.checar(av2 is not None and av2["alertas_gerados"] == 0 and av2["alertas_ja_existentes"] == 1,
               f"reavaliação sem mudança de dados: {av2 and av2['alertas_gerados']} alertas novos, {av2 and av2['alertas_ja_existentes']} já existente")
    c11.checar(len(dia2) == 1 and total2 == total1,
               f"nenhum alerta duplicado: {len(dia2)} alerta no dia; {total1} alertas do usuário antes e {total2} depois")
    return c10, c11


# --- principal ------------------------------------------------------------------

def principal() -> int:
    url_execucao()
    rel, rel_json = Relatorio("execucao_integracao.txt"), Relatorio("execucao_integracao.json")
    for linha in cabecalho("execucao/executar_integracao.py", "Execução formal — integração"):
        rel.add(linha)
    conferir_aplicacao_usa_execucao()
    from app.db import SessaoLocal
    from app.modelos import Avaliacao, Campanha, ContaGoogleAds, MetricaDiaria, Usuario
    from tests.tabela_congelada import carregar_cenarios

    execucao_id, google_id = _localizar()
    rel.add(f"Usuário da execução: id {execucao_id} · usuário do login Google: id {google_id} (e-mails não registrados)")
    with SessaoLocal() as s:
        metricas_google = s.scalar(select(func.count(MetricaDiaria.id)).join(MetricaDiaria.campanha)
                                   .join(Campanha.conta).where(ContaGoogleAds.usuario_id == google_id))
        avaliacoes_google = s.scalar(select(func.count(Avaliacao.id)).where(Avaliacao.usuario_id == google_id))
    if metricas_google or avaliacoes_google:
        raise Parada(SAIDA_AMBIENTE, "O usuário Google já tem métricas ou avaliações: a integração não é do zero.")

    rel.add("Conferência de R1 a R3 (início):")
    diferencas = []
    for uid in (execucao_id, google_id):
        linhas, difs = conferir_usuario(uid)
        for l in linhas:
            rel.add(l)
        diferencas += difs
    if diferencas:
        rel.add("PAROU: regras diferentes da planilha; nenhum caso executado.")
        rel_json.add(json.dumps({"parou": "regras_diferentes", "diferencas": diferencas}, ensure_ascii=False, indent=2))
        gravar_juntos(rel, rel_json)
        print("\n".join(rel.linhas))
        return SAIDA_REGRAS_DIFERENTES
    rel.add("")

    cenarios = carregar_cenarios()
    casos: dict[str, Caso] = {}
    casos["IN-01"] = in01(google_id)
    casos["IN-02"], ids = in02(google_id)
    casos["IN-02b"] = in02b(google_id, ids)
    casos["IN-10"], casos["IN-11"] = in10_in11(google_id, ids, cenarios)
    casos["IN-07"] = in07(execucao_id, cenarios)
    casos["IN-08"], casos["IN-09"] = in08_in09(cenarios)
    for caso in in03_a_06():
        casos[caso.id] = caso

    planilha = _linhas_planilha()
    for id_ in ORDEM:
        p, caso = planilha[id_], casos[id_]
        rel.add(f"{id_} · {p['origem']} · {p['cenario']}")
        rel.add(f"  Pré-condição: {p['precondicao']}")
        rel.add(f"  Esperado: {p['esperado']}")
        rel.add("  Obtido:")
        for l in caso.obtido:
            rel.add(f"    {l}")
        rel.add(f"  Confere? {'Sim' if caso.confere else 'NÃO'}" + (f" · pendente: {caso.pendente}" if caso.pendente else ""))
        rel.add(f"  Evidência: {caso.evidencia}")
        rel.add("")

    rel.add("Conferência de R1 a R3 (fim, todos os usuários):")
    with SessaoLocal() as s:
        todos = list(s.scalars(select(Usuario.id).order_by(Usuario.id)))
    dif_fim = []
    for uid in todos:
        linhas, difs = conferir_usuario(uid)
        for l in linhas:
            rel.add(l)
        dif_fim += difs
    rel.add("  RESULTADO: " + ("iguais à planilha" if not dif_fim else "DIFERENTE: " + "; ".join(dif_fim)))
    rel.add("")
    conferem = sum(casos[i].confere for i in ORDEM)
    rel.add(f"Casos de integração que conferem: {conferem} de {len(ORDEM)}"
            + (" (IN-10: falta a parte do dashboard, no navegador)" if casos["IN-10"].pendente else ""))

    rel_json.add(json.dumps({"casos": [{"id": i, **planilha[i], "obtido": casos[i].obtido, "confere": casos[i].confere,
                                         "pendente": casos[i].pendente, "evidencia": casos[i].evidencia} for i in ORDEM],
                             "conferem": conferem, "total": len(ORDEM), "regras_fim_iguais": not dif_fim},
                            ensure_ascii=False, indent=2, default=str))
    gravar_juntos(rel, rel_json)
    print("\n".join(rel.linhas))
    return SAIDA_OK if conferem == len(ORDEM) and not dif_fim else SAIDA_DIVERGENCIA


if __name__ == "__main__":
    rodar(principal)
