"""Apoio comum aos scripts da execução formal da tabela congelada.

Regras deste pacote:
- Só rodam contra o banco limen_execucao, informado na DATABASE_URL do próprio
  comando (variável de ambiente vale mais que o .env no pydantic-settings).
- Nenhuma função imprime a DATABASE_URL, nem em mensagem de erro.
- Toda evidência é montada em memória, verificada contra padrões sensíveis e só
  então gravada em docs/evidencias/; se houver achado, nada é gravado.
- Erro inesperado mostra só o tipo da exceção e onde ocorreu (arquivo:linha),
  sem a mensagem, que pode conter parâmetros de SQL (ex.: e-mail).
"""

from __future__ import annotations

import hashlib
import os
import re
import subprocess
import sys
import traceback
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import NoReturn
from zoneinfo import ZoneInfo

from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import ArgumentError

BANCO_EXECUCAO = "limen_execucao"
BANCOS_PROIBIDOS = frozenset({"limen", "limen_teste"})
# Usuário próprio da execução. Nunca é impresso (o verificador recusaria).
EMAIL_EXECUCAO = "execucao@limen.local"

RAIZ_BACKEND = Path(__file__).resolve().parents[1]
RAIZ_PROJETO = RAIZ_BACKEND.parent
PLANILHA = RAIZ_PROJETO / "docs" / "avaliacao" / "Tabela_limiares_TCC_motor_de_regras.xlsx"
# sha256 do arquivo no commit 29de91d (congelamento, 12/11/2026).
SHA256_CONGELADO = "fbbea2ec0298dfcf20e0d6cba3a364611740d7e2efd86e56d3dad010025d6653"
DIR_EVIDENCIAS = RAIZ_PROJETO / "docs" / "evidencias"
FUSO = ZoneInfo("America/Fortaleza")

# Códigos de saída (iguais em todos os scripts)
SAIDA_OK = 0
SAIDA_DIVERGENCIA = 1  # a execução rodou e algum caso divergiu do esperado
SAIDA_REGRAS_DIFERENTES = 2  # R1 a R3 do banco diferentes da planilha: nada executado
SAIDA_AMBIENTE = 3  # banco errado, fora do ar, já existente, planilha alterada...
SAIDA_EVIDENCIA_SENSIVEL = 4  # a evidência teria dado sensível: não foi gravada
SAIDA_ERRO_INESPERADO = 5

# A palavra "token" sozinha não entra: os textos da aba Integração (IN-03, IN-04)
# a contêm e são copiados para a evidência. Procuram-se os formatos de token.
PADROES_SENSIVEIS: dict[str, re.Pattern[str]] = {
    "e-mail": re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+"),
    "postgresql": re.compile(r"postgresql", re.IGNORECASE),
    "usuário:senha@": re.compile(r"[^\s/:@]+:[^\s/@]+@"),
    "texto cifrado Fernet": re.compile(r"gAAAAA[A-Za-z0-9_=-]{20,}"),
    "refresh token do Google": re.compile(r"1//[A-Za-z0-9_-]{20,}"),
    "access token do Google": re.compile(r"ya29\.[A-Za-z0-9_-]+"),
    "nome de campo de token": re.compile(r"(?:refresh|access|id)_token", re.IGNORECASE),
}


class Parada(Exception):
    """Interrompe o script com um código de saída e uma mensagem sem dado sensível."""

    def __init__(self, codigo: int, mensagem: str) -> None:
        super().__init__(mensagem)
        self.codigo = codigo
        self.mensagem = mensagem


def url_execucao() -> URL:
    """DATABASE_URL do ambiente, validada. Nunca é impressa."""
    bruta = os.environ.get("DATABASE_URL")
    if not bruta:
        raise Parada(SAIDA_AMBIENTE, f"DATABASE_URL ausente: informe-a no comando, com o banco {BANCO_EXECUCAO}.")
    try:
        url = make_url(bruta)
    except ArgumentError:
        raise Parada(SAIDA_AMBIENTE, "DATABASE_URL ilegível (valor não mostrado).") from None
    if url.database in BANCOS_PROIBIDOS:
        raise Parada(SAIDA_AMBIENTE, f"Recusado: o banco '{url.database}' não pode ser usado na execução.")
    if url.database != BANCO_EXECUCAO:
        raise Parada(SAIDA_AMBIENTE, f"O banco da DATABASE_URL precisa ser {BANCO_EXECUCAO}.")
    return url


def conferir_aplicacao_usa_execucao() -> None:
    """A aplicação (app.config) precisa enxergar a mesma URL do comando, e não a do .env."""
    from app.config import configuracoes

    if configuracoes.database_url != os.environ["DATABASE_URL"]:
        raise Parada(SAIDA_AMBIENTE, "A aplicação não usaria o banco da execução (valor não mostrado).")


def conferir_banco_conectado(sessao) -> None:
    """Confirma pelo próprio PostgreSQL em que banco a sessão está."""
    from sqlalchemy import func, select

    atual = sessao.scalar(select(func.current_database()))
    if atual != BANCO_EXECUCAO:
        raise Parada(SAIDA_AMBIENTE, f"Sessão conectada ao banco '{atual}', e não a {BANCO_EXECUCAO}.")


def sha256_planilha() -> str:
    """sha256 da planilha; para se ela não for a congelada."""
    digest = hashlib.sha256(PLANILHA.read_bytes()).hexdigest()
    if digest != SHA256_CONGELADO:
        raise Parada(SAIDA_AMBIENTE, f"Planilha diferente da congelada (sha256 {digest}).")
    return digest


def _git(*args: str) -> str:
    resultado = subprocess.run(
        ["git", "-C", str(RAIZ_PROJETO), *args], capture_output=True, text=True, check=True
    )
    return resultado.stdout.strip()


PREFIXO_EVIDENCIAS = "docs/evidencias/"


def _fora_do_commit() -> tuple[list[str], list[str]]:
    """(código, evidências) fora do commit, pelo git status (-z: caminhos sem aspas)."""
    saida = subprocess.run(
        ["git", "-C", str(RAIZ_PROJETO), "status", "--porcelain", "-z", "--untracked-files=all"],
        capture_output=True, text=True, check=True,
    ).stdout
    entradas = saida.split("\0")
    codigo: list[str] = []
    evidencias: list[str] = []
    i = 0
    while i < len(entradas):
        entrada = entradas[i]
        i += 1
        if not entrada:
            continue
        estado, caminho = entrada[:2], entrada[3:]
        if estado[0] in "RC":
            i += 1  # com -z, o caminho de origem de um rename vem na entrada seguinte
        (evidencias if caminho.startswith(PREFIXO_EVIDENCIAS) else codigo).append(f"{estado} {caminho}")
    return codigo, evidencias


def cabecalho(script: str, titulo: str) -> list[str]:
    agora = datetime.now(timezone.utc)
    codigo, evidencias = _fora_do_commit()
    linhas = [
        titulo,
        "=" * len(titulo),
        f"Script: {script}",
        f"Data e hora: {agora.astimezone(FUSO).isoformat(timespec='seconds')} (America/Fortaleza)"
        f" = {agora.isoformat(timespec='seconds')}",
        f"Commit do código (git rev-parse HEAD): {_git('rev-parse', 'HEAD')}",
        f"Código fora do commit (git status, fora de docs/evidencias/): {len(codigo)}",
        *(f"  {linha}" for linha in codigo),
        "Evidências ainda não commitadas (docs/evidencias/):" + ("" if evidencias else " nenhuma"),
        *(f"  {linha}" for linha in evidencias),
        f"Planilha: {PLANILHA.relative_to(RAIZ_PROJETO)}",
        f"  sha256 {sha256_planilha()} (igual ao do commit 29de91d)",
        f"Banco: {BANCO_EXECUCAO}",
        f"Python: {sys.version.split()[0]}",
        "",
    ]
    return linhas


def padroes_encontrados(texto: str) -> list[str]:
    """Nomes dos padrões sensíveis presentes no texto (nunca o trecho encontrado)."""
    return [nome for nome, padrao in PADROES_SENSIVEIS.items() if padrao.search(texto)]


class Relatorio:
    """Evidência montada em memória; gravada só depois da verificação."""

    def __init__(self, sufixo: str) -> None:
        hoje = datetime.now(FUSO).date().isoformat()
        self.destino = DIR_EVIDENCIAS / f"{hoje}_{sufixo}"
        if self.destino.exists():
            raise Parada(SAIDA_AMBIENTE, f"{self.destino.name} já existe; não sobrescrevo.")
        self.linhas: list[str] = []

    def add(self, texto: str = "") -> None:
        self.linhas.append(texto)

    def gravar(self) -> Path:
        return gravar_juntos(self)[0]


def gravar_juntos(*relatorios: Relatorio) -> list[Path]:
    """Verifica todos antes de gravar qualquer um: ou todos são gravados, ou nenhum."""
    textos: list[str] = []
    for rel in relatorios:
        texto = "\n".join(rel.linhas) + "\n"
        achados = padroes_encontrados(texto)
        if achados:
            raise Parada(
                SAIDA_EVIDENCIA_SENSIVEL,
                f"Evidências NÃO gravadas; {rel.destino.name}: " + ", ".join(achados),
            )
        if rel.destino.exists():
            raise Parada(SAIDA_AMBIENTE, f"{rel.destino.name} já existe; não sobrescrevo.")
        textos.append(texto)
    for rel, texto in zip(relatorios, textos):
        rel.destino.write_text(texto, encoding="utf-8")
    for rel, texto in zip(relatorios, textos):
        relido = rel.destino.read_text(encoding="utf-8")
        if relido != texto or padroes_encontrados(relido):
            for outro in relatorios:
                outro.destino.unlink(missing_ok=True)
            raise Parada(SAIDA_EVIDENCIA_SENSIVEL, "Arquivo relido diferente ou com padrão sensível: todos apagados.")
    return [rel.destino for rel in relatorios]


def rodar(principal: Callable[[], int]) -> NoReturn:
    """Executa o script e sai com o código real, sem expor mensagens de exceção."""
    try:
        codigo = principal()
    except Parada as parada:
        print(f"PAROU: {parada.mensagem}")
        codigo = parada.codigo
    except Exception as erro:  # noqa: BLE001 — o tipo e o local bastam; a mensagem pode ter dados
        quadros = traceback.extract_tb(erro.__traceback__)
        print(f"ERRO inesperado: {type(erro).__name__} (mensagem omitida)")
        for quadro in quadros[-4:]:
            print(f"  em {Path(quadro.filename).name}:{quadro.lineno} ({quadro.name})")
        codigo = SAIDA_ERRO_INESPERADO
    print(f"Código de saída: {codigo}")
    sys.exit(codigo)
