"""Confere R1 a R3 de cada usuário do banco de execução contra a planilha.

Uso: DATABASE_URL=<url do limen_execucao> python -m execucao.conferir_regras

As regras são lidas como a tela lê: GET /regras pela aplicação de verdade
(criar_app, uma sessão nova por pedido); só o usuário logado é substituído.
Exigido para cada usuário: exatamente R1, R2 e R3 ativas, nenhuma outra regra
ativa, mesmos nomes, mesmas condições na mesma ordem e limiares iguais como
Decimal (1.000000 do banco = 0,01 × 100 da planilha).
Também é chamado no início de executar_cenarios e executar_integracao.

Saída: 0 iguais · 2 diferença (nada é executado) · 3 ambiente · 4 · 5.
Evidência: docs/evidencias/AAAA-MM-DD_execucao_conferir_regras.txt
(gravada também quando há diferença, para documentar a parada).
"""

from __future__ import annotations

from decimal import Decimal

from fastapi.testclient import TestClient
from openpyxl import load_workbook
from sqlalchemy import select

from .comum import (
    PLANILHA,
    SAIDA_AMBIENTE,
    SAIDA_OK,
    SAIDA_REGRAS_DIFERENTES,
    Parada,
    Relatorio,
    cabecalho,
    conferir_aplicacao_usa_execucao,
    conferir_banco_conectado,
    rodar,
    url_execucao,
)


def linhas_da_planilha() -> list[str]:
    """Linhas 4 a 6 da aba 'Regras e limiares', como estão (a fonte da conferência)."""
    aba = load_workbook(PLANILHA, read_only=True)["Regras e limiares"]
    return [
        "  " + " | ".join("" if v is None else str(v) for v in linha[:6])
        for linha in aba.iter_rows(min_row=4, max_row=6, values_only=True)
    ]


def _da_api(regra: dict) -> tuple:
    condicoes = []
    for c in sorted(regra["condicoes"], key=lambda c: c["ordem"]):
        if not isinstance(c["limiar"], str):  # decimal tem de vir como texto, nunca float
            raise Parada(SAIDA_AMBIENTE, f"{regra['codigo']}: limiar não veio como texto no JSON.")
        condicoes.append((c["metrica"], c["operador"], Decimal(c["limiar"])))
    return regra["nome"], tuple(condicoes)


def _da_tabela(regra) -> tuple:
    return regra.nome, tuple((c.metrica.value, c.operador.value, c.limiar) for c in regra.condicoes)


def _texto(lado: tuple | None) -> str:
    if lado is None:
        return "(ausente ou inativa)"
    nome, condicoes = lado
    return f"'{nome}': " + " E ".join(f"{m} {o} {l}" for m, o, l in condicoes)


def conferir_usuario(usuario_id: int) -> tuple[list[str], list[str]]:
    """(linhas para o relatório, diferenças). Sem diferenças = pode executar."""
    from app.api.deps import obter_usuario_atual
    from app.main import criar_app
    from tests.tabela_congelada import carregar_regras

    app = criar_app()
    app.dependency_overrides[obter_usuario_atual] = lambda: usuario_id
    with TestClient(app) as cliente:
        resposta = cliente.get("/regras")
    if resposta.status_code != 200:
        return [f"Usuário id {usuario_id}: GET /regras devolveu {resposta.status_code}"], ["GET /regras falhou"]

    todas = resposta.json()
    ativas = {r["codigo"]: r for r in todas if r["ativa"]}
    esperadas = {r.id: r for r in carregar_regras()}
    linhas = [f"Usuário id {usuario_id}: {len(todas)} regras, {len(ativas)} ativas ({', '.join(sorted(ativas))})"]
    diferencas: list[str] = []
    extras = sorted(set(ativas) - set(esperadas))
    if extras:
        diferencas.append(f"usuário {usuario_id}: regras ativas fora da planilha {extras}")
    for codigo, regra in esperadas.items():
        banco = _da_api(ativas[codigo]) if codigo in ativas else None
        igual = banco == _da_tabela(regra)
        linhas.append(f"  {codigo} planilha {_texto(_da_tabela(regra))}")
        linhas.append(f"  {codigo} banco    {_texto(banco)}  → {'igual' if igual else 'DIFERENTE'}")
        if not igual:
            diferencas.append(f"usuário {usuario_id}: {codigo} diferente da planilha")
    return linhas, diferencas


def principal() -> int:
    url_execucao()
    rel = Relatorio("execucao_conferir_regras.txt")
    for linha in cabecalho("execucao/conferir_regras.py", "Execução formal — conferência de R1 a R3"):
        rel.add(linha)
    conferir_aplicacao_usa_execucao()

    from app.db import SessaoLocal
    from app.modelos import Usuario

    with SessaoLocal() as sessao:
        conferir_banco_conectado(sessao)
        usuarios = list(sessao.scalars(select(Usuario.id).order_by(Usuario.id)))
    if not usuarios:
        raise Parada(SAIDA_AMBIENTE, "Nenhum usuário no banco: rode execucao.preparar antes.")

    rel.add("Planilha, aba 'Regras e limiares' (ID | Regra | Métrica | Operador | Limiar | Unidade):")
    for linha in linhas_da_planilha():
        rel.add(linha)
    rel.add("(o limiar do R1 está como fração na planilha: 0,01 = 1%; o motor usa %)")
    rel.add("")

    diferencas: list[str] = []
    for usuario_id in usuarios:
        linhas, difs = conferir_usuario(usuario_id)
        for linha in linhas:
            rel.add(linha)
        diferencas += difs
    rel.add("")
    if diferencas:
        rel.add("RESULTADO: DIFERENTE — nada deve ser executado.")
        for d in diferencas:
            rel.add(f"  - {d}")
    else:
        rel.add(f"RESULTADO: R1 a R3 iguais à planilha em {len(usuarios)} usuário(s).")

    destino = rel.gravar()
    print("\n".join(rel.linhas))
    print(f"Evidência gravada: docs/evidencias/{destino.name} (sem padrões sensíveis)")
    return SAIDA_REGRAS_DIFERENTES if diferencas else SAIDA_OK


if __name__ == "__main__":
    rodar(principal)
