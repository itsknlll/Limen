"""Base dos testes de desempenho (aba Desempenho da tabela congelada).

Mesmas regras da execução formal (execucao/comum.py), com o banco próprio:
- Só rodam contra o banco limen_desempenho, informado na DATABASE_URL do próprio
  comando; limen, limen_teste e limen_execucao são recusados pelo nome.
- A DATABASE_URL nunca é impressa, nem em mensagem de erro.
- Com código fora do commit (git status fora de docs/evidencias/), o script para
  com 3 antes de medir: o que foi medido tem de ser o que está no commit.
- Evidência montada em memória e verificada antes de gravar: os padrões do
  comum.py (e-mail, tokens, URL do banco...) e, aqui, também hostname, nome do
  usuário do sistema, caminhos /home e URL com parâmetro code.
- Tempos em nanossegundos inteiros (perf_counter_ns); estatística em Decimal.

Importar este módulo não abre banco nem rede.
"""

from __future__ import annotations

import getpass
import hashlib
import importlib.metadata
import os
import platform
import re
import socket
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal, localcontext
from pathlib import Path

from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import ArgumentError

from app import motor
from app.servicos.sinteticas.gerador import MetricaGerada, gerar_metricas

from .. import comum
from ..comum import FUSO, PLANILHA, SAIDA_AMBIENTE, SAIDA_EVIDENCIA_SENSIVEL, Parada, Relatorio

BANCO_DESEMPENHO = "limen_desempenho"
BANCOS_PROIBIDOS = frozenset({"limen", "limen_teste", "limen_execucao"})

# --- Dados sintéticos (semente fixa) -----------------------------------------
SEMENTE = 20261116  # data do plano de desempenho
INICIO_DADOS = date(2024, 1, 1)
DIAS_POR_CAMPANHA = 1000
FIM_DADOS = INICIO_DADOS + timedelta(days=DIAS_POR_CAMPANHA - 1)  # 26/09/2026
# IDs fictícios e declarados (não são da conta de teste do Google Ads): 900001...
BASE_GOOGLE_CAMPAIGN_ID = 900_000

# --- Base dos endpoints (aba Desempenho, linha 20: 10.000 registros e 10 regras) ---
CAMPANHAS_ENDPOINTS = 10
REGISTROS_ENDPOINTS = CAMPANHAS_ENDPOINTS * DIAS_POR_CAMPANHA  # DE-04 avalia isto
REGRAS_ENDPOINTS = 10
DIAS_DE01 = 30
PERIODO_DE01 = (FIM_DADOS - timedelta(days=DIAS_DE01 - 1), FIM_DADOS)  # 28/08 a 26/09/2026

ENDPOINTS_FIXOS = ("GET /campanhas/{id}/metricas", "GET /alertas", "POST /regras", "POST /avaliacoes")
LINHAS_MOTOR = range(10, 19)  # DM-01 a DM-09
LINHAS_ENDPOINTS = range(22, 26)  # DE-01 a DE-04

# Padrões além dos do comum.py. Os de máquina são lidos na hora (não ficam no código).
PADROES_EXTRAS: dict[str, re.Pattern[str]] = {
    "caminho /home": re.compile(r"/home/"),
    "URL com parâmetro code": re.compile(r"[?&]code="),
    "cabeçalho Authorization": re.compile(r"Bearer\s+\S", re.IGNORECASE),
}


# --- Trava do banco ------------------------------------------------------------

def url_desempenho() -> URL:
    """DATABASE_URL do ambiente, validada. Nunca é impressa."""
    bruta = os.environ.get("DATABASE_URL")
    if not bruta:
        raise Parada(SAIDA_AMBIENTE, f"DATABASE_URL ausente: informe-a no comando, com o banco {BANCO_DESEMPENHO}.")
    try:
        url = make_url(bruta)
    except ArgumentError:
        raise Parada(SAIDA_AMBIENTE, "DATABASE_URL ilegível (valor não mostrado).") from None
    if url.database in BANCOS_PROIBIDOS:
        raise Parada(SAIDA_AMBIENTE, f"Recusado: o banco '{url.database}' não pode ser usado no desempenho.")
    if url.database != BANCO_DESEMPENHO:
        raise Parada(SAIDA_AMBIENTE, f"O banco da DATABASE_URL precisa ser {BANCO_DESEMPENHO}.")
    return url


def conferir_aplicacao_usa_desempenho() -> None:
    """A aplicação (app.config) precisa enxergar a mesma URL do comando, e não a do .env."""
    from app.config import configuracoes

    if configuracoes.database_url != os.environ["DATABASE_URL"]:
        raise Parada(SAIDA_AMBIENTE, "A aplicação não usaria o banco do desempenho (valor não mostrado).")


def conferir_banco_conectado(sessao) -> None:
    """Confirma pelo próprio servidor em que banco a sessão está."""
    from sqlalchemy import func, select

    atual = sessao.scalar(select(func.current_database()))
    if atual != BANCO_DESEMPENHO:
        raise Parada(SAIDA_AMBIENTE, f"Sessão conectada ao banco '{atual}', e não a {BANCO_DESEMPENHO}.")


def versao_servidor(sessao) -> str:
    # SHOW server_version, e não version(): o texto do version() traz o nome do
    # produto, que o verificador do comum.py recusa (padrão "postgresql").
    from sqlalchemy import text

    return str(sessao.scalar(text("SHOW server_version")))


# --- Plano lido da planilha (oráculo: os números não ficam repetidos no código) ---

@dataclass(frozen=True)
class Plano:
    aquecimentos: int
    repeticoes: int
    motor: tuple[tuple[str, int, int], ...]  # (ID, registros, regras ativas)
    endpoints: tuple[tuple[str, str], ...]  # (ID, endpoint)


def _inteiro(valor: object, onde: str) -> int:
    if not isinstance(valor, int) or isinstance(valor, bool) or valor <= 0:
        raise Parada(SAIDA_AMBIENTE, f"Planilha: {onde} não é inteiro positivo.")
    return valor


def ler_plano() -> Plano:
    comum.sha256_planilha()  # para se a planilha não for a congelada
    from openpyxl import load_workbook

    aba = load_workbook(PLANILHA)["Desempenho"]
    motor_ = tuple(
        (str(aba[f"A{n}"].value), _inteiro(aba[f"B{n}"].value, f"B{n}"), _inteiro(aba[f"C{n}"].value, f"C{n}"))
        for n in LINHAS_MOTOR
    )
    endpoints = tuple((str(aba[f"A{n}"].value), str(aba[f"B{n}"].value)) for n in LINHAS_ENDPOINTS)
    if tuple(e for _, e in endpoints) != ENDPOINTS_FIXOS:
        raise Parada(SAIDA_AMBIENTE, "Planilha: endpoints da aba Desempenho diferentes dos fixos.")
    for id_, volume, regras in motor_:
        if volume % DIAS_POR_CAMPANHA or regras < 3:
            raise Parada(SAIDA_AMBIENTE, f"Planilha: {id_} fora do que o gerador sabe montar.")
    return Plano(_inteiro(aba["B3"].value, "B3"), _inteiro(aba["B4"].value, "B4"), motor_, endpoints)


# --- Regras: R1 a R3 da tabela + sintéticas por fórmula fixa (sem sorteio) ---------

METRICAS = ("impressoes", "cliques", "custo", "conversoes", "ctr", "cpc")
OPERADORES = ("<", "<=", ">", ">=")
# Dentro das faixas do gerador do IN-02b (impressões 3.000 a 10.000, CTR 2% a 6%
# no perfil normal, CPC R$ 0,50 a R$ 3,00, conversões 0 a 10): nenhuma condição
# sozinha é sempre verdadeira ou sempre falsa.
LIMIARES = {
    "impressoes": ("4000", "6500", "9000"),
    "cliques": ("100", "250", "400"),
    "custo": ("100.00", "300.00", "800.00"),
    "conversoes": ("1", "3", "6"),
    "ctr": ("1.0", "3.0", "5.0"),  # em %, como o motor (cliques × 100 / impressões)
    "cpc": ("1.00", "2.00", "5.00"),
}


@dataclass(frozen=True)
class DefinicaoRegra:
    codigo: str
    nome: str
    condicoes: tuple[tuple[str, str, str], ...]  # (métrica, operador, limiar em texto)

    def corpo(self, ativa: bool = True) -> dict:
        """Corpo de POST /regras (o mesmo contrato da tela)."""
        return {
            "codigo": self.codigo,
            "nome": self.nome,
            "ativa": ativa,
            "condicoes": [{"metrica": m, "operador": o, "limiar": l} for m, o, l in self.condicoes],
        }

    def para_motor(self) -> motor.Regra:
        return motor.Regra(
            id=self.codigo,
            nome=self.nome,
            condicoes=tuple(
                motor.Condicao(motor.Metrica(m), motor.Operador(o), Decimal(l)) for m, o, l in self.condicoes
            ),
        )


def definicoes_regras(total: int) -> list[DefinicaoRegra]:
    """R1 a R3 (regras_padrao, os limiares da tabela) e R4 a R<total>.

    A regra k (k >= 4, i = k - 4) tem 1 + i % 3 condições; a condição j usa a
    métrica METRICAS[(i + j) % 6] (distintas dentro da regra, porque j < 3), o
    operador OPERADORES[(i + 2j + i // 36) % 4] e o limiar
    LIMIARES[métrica][(i // 12 + j) % 3]. Métrica, operador e quantidade se
    repetem a cada 12 regras; o limiar muda a cada 12 e o operador a cada 36,
    e por isso nenhuma regra até R50 repete outra (sem isso, R40 a R50 eram
    cópias de R4 a R14).
    """
    if not 3 <= total <= 999:
        raise ValueError(f"total de regras entre 3 e 999 (recebido: {total})")
    padrao = [
        DefinicaoRegra(r.id, r.nome, tuple((c.metrica.value, c.operador.value, str(c.limiar)) for c in r.condicoes))
        for r in motor.regras_padrao()
    ]
    sinteticas = []
    for k in range(4, total + 1):
        i = k - 4
        condicoes = []
        for j in range(1 + i % 3):
            metrica = METRICAS[(i + j) % len(METRICAS)]
            operador = OPERADORES[(i + 2 * j + i // 36) % len(OPERADORES)]
            condicoes.append((metrica, operador, LIMIARES[metrica][(i // 12 + j) % 3]))
        sinteticas.append(DefinicaoRegra(f"R{k}", f"Sintética {k} (desempenho)", tuple(condicoes)))
    return padrao + sinteticas


def regra_do_de03(n: int) -> DefinicaoRegra:
    """Regra criada na repetição n do DE-03 (P001, P002...). Vai inativa."""
    return DefinicaoRegra(f"P{n:03d}", f"Criada no DE-03, pedido {n}", (("ctr", "<", "0.5"),))


# --- Registros -----------------------------------------------------------------

def ids_campanhas(quantidade: int) -> list[int]:
    return [BASE_GOOGLE_CAMPAIGN_ID + n for n in range(1, quantidade + 1)]


def metricas_da_campanha(google_campaign_id: int) -> list[MetricaGerada]:
    """O gerador do IN-02b (testado, valida cada registro), com a semente e o período daqui."""
    return gerar_metricas(google_campaign_id, semente=SEMENTE, inicio=INICIO_DADOS, dias=DIAS_POR_CAMPANHA)


def _campanhas_do_volume(volume: int) -> int:
    if volume <= 0 or volume % DIAS_POR_CAMPANHA:
        raise ValueError(f"volume precisa ser múltiplo positivo de {DIAS_POR_CAMPANHA} (recebido: {volume})")
    return volume // DIAS_POR_CAMPANHA


def registros_motor(volume: int) -> list[motor.RegistroMetricas]:
    """Os `volume` registros do DM, em memória (sem banco)."""
    return [
        motor.RegistroMetricas(m.impressoes, m.cliques, m.custo, m.conversoes)
        for gid in ids_campanhas(_campanhas_do_volume(volume))
        for m in metricas_da_campanha(gid)
    ]


def sha256_dados(volume: int) -> str:
    """Impressão digital do conjunto (campanha; data; impressões; cliques; custo; conversões)."""
    h = hashlib.sha256()
    for gid in ids_campanhas(_campanhas_do_volume(volume)):
        for m in metricas_da_campanha(gid):
            h.update(f"{gid};{m.data.isoformat()};{m.impressoes};{m.cliques};{m.custo};{m.conversoes}\n".encode())
    return h.hexdigest()


# --- Estatística (Decimal, sem float) -------------------------------------------

NS_POR_MS = Decimal(1_000_000)


@dataclass(frozen=True)
class Estatisticas:
    n: int
    media_ms: Decimal
    mediana_ms: Decimal
    desvio_ms: Decimal  # amostral (n − 1)
    minimo_ms: Decimal
    maximo_ms: Decimal
    p95_ms: Decimal  # nearest-rank: um valor observado

    @property
    def coef_variacao(self) -> Decimal | None:
        return None if self.media_ms == 0 else self.desvio_ms / self.media_ms


def percentil_nearest_rank(ordenadas: list[int], p: int) -> int:
    """Menor valor com pelo menos p% das amostras <= ele: posição ⌈p·n/100⌉ (1 a n)."""
    if not ordenadas:
        raise ValueError("sem amostras")
    if not 0 < p <= 100:
        raise ValueError(f"p entre 1 e 100 (recebido: {p})")
    posicao = -(-p * len(ordenadas) // 100)  # teto em inteiros, sem float
    return ordenadas[posicao - 1]


def estatisticas(amostras_ns: list[int]) -> Estatisticas:
    if len(amostras_ns) < 2:
        raise ValueError("pelo menos 2 amostras (o desvio é amostral, n − 1)")
    if any(not isinstance(a, int) or isinstance(a, bool) or a < 0 for a in amostras_ns):
        raise ValueError("amostras devem ser inteiros >= 0 (nanossegundos)")
    n = len(amostras_ns)
    ordenadas = sorted(amostras_ns)
    with localcontext() as ctx:
        ctx.prec = 50
        xs = [Decimal(a) for a in ordenadas]
        media = sum(xs, Decimal(0)) / n
        meio = n // 2
        mediana = xs[meio] if n % 2 else (xs[meio - 1] + xs[meio]) / 2
        desvio = (sum(((x - media) ** 2 for x in xs), Decimal(0)) / (n - 1)).sqrt()
        return Estatisticas(
            n=n,
            media_ms=media / NS_POR_MS,
            mediana_ms=mediana / NS_POR_MS,
            desvio_ms=desvio / NS_POR_MS,
            minimo_ms=xs[0] / NS_POR_MS,
            maximo_ms=xs[-1] / NS_POR_MS,
            p95_ms=Decimal(percentil_nearest_rank(ordenadas, 95)) / NS_POR_MS,
        )


def arredondar(valor: Decimal, casas: int = 3) -> Decimal:
    """Para exibir e para a planilha; o .json guarda as amostras em ns, sem arredondar."""
    with localcontext() as ctx:
        ctx.prec = 50
        return valor.quantize(Decimal(1).scaleb(-casas), rounding=ROUND_HALF_UP)


# --- Ambiente (sem hostname, usuário nem caminhos pessoais) ---------------------

PACOTES = ("fastapi", "starlette", "sqlalchemy", "pydantic", "psycopg", "uvicorn", "httpx", "google-ads", "openpyxl")


def _ler(caminho: str | Path) -> str | None:
    try:
        return Path(caminho).read_text(encoding="utf-8").strip()
    except OSError:
        return None


def _energia() -> str:
    for fonte in sorted(Path("/sys/class/power_supply").glob("*")):
        if _ler(fonte / "type") == "Mains":
            return {"1": "na tomada", "0": "na bateria"}.get(_ler(fonte / "online") or "", "não disponível")
    return "não disponível"


def ambiente(servidor_banco: str | None) -> dict[str, str]:
    cpuinfo = _ler("/proc/cpuinfo") or ""
    modelo = next((l.split(":", 1)[1].strip() for l in cpuinfo.splitlines() if l.startswith("model name")), None)
    memoria = next((l.split()[1] for l in (_ler("/proc/meminfo") or "").splitlines() if l.startswith("MemTotal:")), None)
    os_release = dict(l.split("=", 1) for l in (_ler("/etc/os-release") or "").splitlines() if "=" in l)
    carga = ", ".join(f"{x:.2f}" for x in os.getloadavg())
    versoes = {}
    for pacote in PACOTES:
        try:
            versoes[f"Pacote {pacote}"] = importlib.metadata.version(pacote)
        except importlib.metadata.PackageNotFoundError:
            versoes[f"Pacote {pacote}"] = "não instalado"
    return {
        "CPU": modelo or "não disponível",
        "Núcleos lógicos": str(os.cpu_count()),
        "Memória total": (
            f"{arredondar(Decimal(memoria) / Decimal(1024 * 1024), 1)} GiB" if memoria else "não disponível"
        ),
        "Governor da CPU": _ler("/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor") or "não disponível",
        "Energia": _energia(),
        "Carga média no início (1, 5, 15 min)": carga,
        "SO": os_release.get("PRETTY_NAME", "não disponível").strip('"'),
        "Kernel": platform.release(),
        "Python": platform.python_version(),
        **versoes,
        "Servidor do banco (SHOW server_version, no Docker)": servidor_banco or "não consultado",
    }


def resumo_ambiente(amb: dict[str, str]) -> str:
    """Uma linha para a célula B5 da aba Desempenho."""
    return (
        f"CPU {amb['CPU']} ({amb['Núcleos lógicos']} núcleos lógicos), {amb['Memória total']}, "
        f"{amb['SO']} (kernel {amb['Kernel']}), Python {amb['Python']}, FastAPI {amb['Pacote fastapi']}, "
        f"SQLAlchemy {amb['Pacote sqlalchemy']}, banco {amb['Servidor do banco (SHOW server_version, no Docker)']}; "
        f"energia {amb['Energia']}, governor {amb['Governor da CPU']}; cliente, servidor e banco na mesma máquina"
    )


# --- Evidências -------------------------------------------------------------------

def _palavra(valor: str) -> re.Pattern[str]:
    return re.compile(rf"(?<![A-Za-z0-9]){re.escape(valor)}(?![A-Za-z0-9])", re.IGNORECASE)


def padroes_locais() -> dict[str, re.Pattern[str]]:
    """PADROES_EXTRAS + hostname, usuário do sistema e pasta pessoal desta máquina."""
    padroes = dict(PADROES_EXTRAS)
    hostname = socket.gethostname()
    if hostname:
        padroes["hostname"] = _palavra(hostname)
        padroes["hostname (primeiro nome)"] = _palavra(hostname.split(".")[0])
    try:
        usuario = getpass.getuser()
    except (OSError, KeyError):
        usuario = ""
    if usuario:
        padroes["usuário do sistema"] = _palavra(usuario)
    pasta = str(Path.home())
    if pasta not in ("", "/"):
        padroes["pasta pessoal"] = re.compile(re.escape(pasta))
    return padroes


def achados(texto: str) -> list[str]:
    """Nomes dos padrões encontrados (nunca o trecho): os do comum.py e os locais."""
    return comum.padroes_encontrados(texto) + [n for n, p in padroes_locais().items() if p.search(texto)]


def gravar(*relatorios: Relatorio) -> list[Path]:
    """Checa os padrões locais, grava pelo gravar_juntos do comum.py e confere de novo."""
    locais = padroes_locais()
    for rel in relatorios:
        texto = "\n".join(rel.linhas) + "\n"
        encontrados = [n for n, p in locais.items() if p.search(texto)]
        if encontrados:
            raise Parada(SAIDA_EVIDENCIA_SENSIVEL, f"Evidências NÃO gravadas; {rel.destino.name}: " + ", ".join(encontrados))
    caminhos = comum.gravar_juntos(*relatorios)  # checa os padrões do comum.py; tudo ou nada
    for caminho in caminhos:
        texto = caminho.read_text(encoding="utf-8")
        if any(p.search(texto) for p in locais.values()):
            for outro in caminhos:
                outro.unlink(missing_ok=True)
            raise Parada(SAIDA_EVIDENCIA_SENSIVEL, "Arquivo relido com padrão local: todos apagados.")
    return caminhos


def cabecalho(
    script: str, titulo: str, usa_banco: bool = True, motivo_sem_banco: str = "motor em memória"
) -> list[str]:
    """Igual ao do comum.py, com o banco do desempenho; para se houver código fora do commit."""
    codigo, evidencias = comum._fora_do_commit()
    if codigo:
        raise Parada(SAIDA_AMBIENTE, f"Código fora do commit ({len(codigo)} arquivo(s)): commite antes de medir.")
    agora = datetime.now(timezone.utc)
    return [
        titulo,
        "=" * len(titulo),
        f"Script: {script}",
        f"Data e hora: {agora.astimezone(FUSO).isoformat(timespec='seconds')} (America/Fortaleza)"
        f" = {agora.isoformat(timespec='seconds')}",
        f"Commit do código (git rev-parse HEAD): {comum._git('rev-parse', 'HEAD')}",
        "Código fora do commit (git status, fora de docs/evidencias/): 0",
        "Evidências ainda não commitadas (docs/evidencias/):" + ("" if evidencias else " nenhuma"),
        *(f"  {linha}" for linha in evidencias),
        f"Planilha: {PLANILHA.relative_to(comum.RAIZ_PROJETO)}",
        f"  sha256 {comum.sha256_planilha()} (igual ao do commit 29de91d)",
        f"Banco: {BANCO_DESEMPENHO}" if usa_banco else f"Banco: não usado ({motivo_sem_banco})",
        f"Dados: gerar_metricas, semente {SEMENTE}, {INICIO_DADOS.isoformat()} a {FIM_DADOS.isoformat()}"
        f" ({DIAS_POR_CAMPANHA} dias por campanha), IDs de campanha fictícios a partir de {BASE_GOOGLE_CAMPAIGN_ID + 1}",
        "",
    ]
