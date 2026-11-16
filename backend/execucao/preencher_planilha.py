"""Cópia preenchida da tabela congelada com os resultados da execução formal.

Uso: python -m execucao.preencher_planilha --in10-dashboard sim|nao [--data AAAA-MM-DD]
(sem banco: lê só a planilha e os .json das evidências; não usa DATABASE_URL)

Lê docs/evidencias/<data>_execucao_cenarios.json e _integracao.json e grava
docs/evidencias/<data>_execucao_tabela_preenchida.xlsx, escrevendo SÓ as
colunas amarelas:
  Cenários de regras: O (registro observado), P, Q, R (R1 a R3 observados);
  Integração: F (resultado observado), G (confere?), H (evidência).
Travas:
- sha256 do original igual ao congelado, antes e depois;
- os dois .txt da execução dizem "Código fora do commit ...: 0" e têm o mesmo
  commit (evidências ainda não commitadas não contam);
- toda célula a escrever está vazia no original;
- depois de gravar, compara célula por célula todas as abas: fora das células
  permitidas, tudo igual ao original (valor ou fórmula); senão apaga a cópia;
- IN-10 só "Sim" com --in10-dashboard sim (a parte do navegador é sua).
Fórmulas (S, T, U e a aba Resumo) ficam como estão; o openpyxl grava sem os
valores calculados, e o LibreOffice/Excel recalcula ao abrir.

Saída: 0 ok · 1 cópia diferente do original (apagada) · 3 ambiente · 4 · 5.
Evidência: docs/evidencias/<data>_execucao_planilha.txt (células escritas)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import date, datetime

from openpyxl import load_workbook

from .comum import (
    DIR_EVIDENCIAS,
    FUSO,
    PLANILHA,
    SAIDA_AMBIENTE,
    SAIDA_DIVERGENCIA,
    SAIDA_EVIDENCIA_SENSIVEL,
    SAIDA_OK,
    SHA256_CONGELADO,
    Parada,
    Relatorio,
    cabecalho,
    padroes_encontrados,
    rodar,
    sha256_planilha,
)

ABA_CENARIOS, ABA_INTEGRACAO = "Cenários de regras", "Integração"
COLUNAS_CENARIOS = {"registro": "O", "R1": "P", "R2": "Q", "R3": "R"}
LINHAS_CENARIOS = range(5, 28)  # 23 casos
LINHAS_INTEGRACAO = range(5, 17)  # 12 casos
PADRAO_COMMIT = re.compile(r"^Commit do código \(git rev-parse HEAD\): ([0-9a-f]{40})$", re.M)
PADRAO_CODIGO_FORA = re.compile(r"^Código fora do commit \(git status, fora de docs/evidencias/\): (\d+)$", re.M)


def _ler_execucao(data: str, nome: str) -> tuple[dict, str]:
    """(.json, commit) de uma execução; exige código sem alteração fora do commit."""
    txt = DIR_EVIDENCIAS / f"{data}_execucao_{nome}.txt"
    js = DIR_EVIDENCIAS / f"{data}_execucao_{nome}.json"
    if not (txt.exists() and js.exists()):
        raise Parada(SAIDA_AMBIENTE, f"Faltam {txt.name} ou {js.name}.")
    cabeca = txt.read_text(encoding="utf-8")
    commit, fora = PADRAO_COMMIT.search(cabeca), PADRAO_CODIGO_FORA.search(cabeca)
    if not commit or not fora or fora.group(1) != "0":
        raise Parada(SAIDA_AMBIENTE, f"{txt.name}: a execução não rodou com o código igual ao commit.")
    return json.loads(js.read_text(encoding="utf-8")), commit.group(1)


def _texto_integracao(caso: dict) -> str:
    linhas = [
        re.sub(r"^\[(ok|FALHOU|nota)\] ", lambda m: "" if m.group(1) == "ok" else f"{m.group(1)}: ", linha)
        for linha in caso["obtido"]
    ]
    return "\n".join(linhas)


def _valores(wb) -> dict[tuple[str, str], object]:
    return {(aba.title, c.coordinate): c.value for aba in wb.worksheets for linha in aba.iter_rows() for c in linha}


def principal() -> int:
    args = argparse.ArgumentParser()
    args.add_argument("--in10-dashboard", choices=("sim", "nao"), required=True)
    args.add_argument("--data", default=datetime.now(FUSO).date().isoformat())
    opcoes = args.parse_args()
    date.fromisoformat(opcoes.data)

    rel = Relatorio("execucao_planilha.txt")
    for linha in cabecalho("execucao/preencher_planilha.py", "Execução formal — planilha preenchida"):
        rel.add(linha)
    destino = DIR_EVIDENCIAS / f"{opcoes.data}_execucao_tabela_preenchida.xlsx"
    if destino.exists():
        raise Parada(SAIDA_AMBIENTE, f"{destino.name} já existe; não sobrescrevo.")

    cenarios, commit_c = _ler_execucao(opcoes.data, "cenarios")
    integracao, commit_i = _ler_execucao(opcoes.data, "integracao")
    if commit_c != commit_i:
        raise Parada(SAIDA_AMBIENTE, "Cenários e integração rodaram em commits diferentes.")
    if cenarios.get("executados") != 23 or integracao.get("total") != 12:
        raise Parada(SAIDA_AMBIENTE, "Os .json não têm 23 cenários e 12 casos de integração.")
    rel.add(f"Execução lida: commit {commit_c} (cenários e integração, código igual ao commit)")
    rel.add(f"IN-10, parte do dashboard (informada por você): {opcoes.in10_dashboard}")
    rel.add("")

    original = load_workbook(PLANILHA)  # fórmulas preservadas (data_only=False)
    copia = load_workbook(PLANILHA)
    escritas: dict[tuple[str, str], str] = {}

    aba = copia[ABA_CENARIOS]
    por_id = {c["id"]: c for c in cenarios["casos"]}
    for n in LINHAS_CENARIOS:
        caso = por_id.pop(aba[f"A{n}"].value)
        for chave, col in COLUNAS_CENARIOS.items():
            escritas[(ABA_CENARIOS, f"{col}{n}")] = caso["observado"][chave]
    aba = copia[ABA_INTEGRACAO]
    por_id_i = {c["id"]: c for c in integracao["casos"]}
    for n in LINHAS_INTEGRACAO:
        caso = por_id_i.pop(aba[f"A{n}"].value)
        confere = caso["confere"] and (caso["id"] != "IN-10" or opcoes.in10_dashboard == "sim")
        obtido = _texto_integracao(caso)
        if caso["id"] == "IN-10":
            obtido += f"\ndashboard (navegador): {'conferido' if opcoes.in10_dashboard == 'sim' else 'NÃO conferido'}"
        escritas[(ABA_INTEGRACAO, f"F{n}")] = obtido
        escritas[(ABA_INTEGRACAO, f"G{n}")] = "Sim" if confere else "Não"
        escritas[(ABA_INTEGRACAO, f"H{n}")] = f"{caso['evidencia']}; commit {commit_c[:7]}"
    if por_id or por_id_i:
        raise Parada(SAIDA_AMBIENTE, f"Casos sem linha na planilha: {sorted(por_id) + sorted(por_id_i)}")

    vals_orig = _valores(original)
    ocupadas = [k for k in escritas if vals_orig.get(k) is not None]
    if ocupadas:
        raise Parada(SAIDA_AMBIENTE, f"Células já preenchidas no original: {ocupadas}")
    achados = padroes_encontrados("\n".join(str(v) for v in [*escritas.values(), *vals_orig.values()] if v is not None))
    if achados:
        raise Parada(SAIDA_EVIDENCIA_SENSIVEL, "Planilha NÃO gravada; padrões encontrados: " + ", ".join(achados))

    for (nome_aba, coord), valor in escritas.items():
        copia[nome_aba][coord] = valor
    copia.save(destino)

    relida = _valores(load_workbook(destino))
    fora = [k for k in set(vals_orig) | set(relida) if k not in escritas and vals_orig.get(k) != relida.get(k)]
    erradas = [k for k, v in escritas.items() if relida.get(k) != v]
    if fora or erradas:
        destino.unlink()
        raise Parada(SAIDA_DIVERGENCIA, f"Cópia diferente do original ({len(fora)} fora das colunas amarelas, "
                                        f"{len(erradas)} escritas erradas): apagada.")
    if hashlib.sha256(PLANILHA.read_bytes()).hexdigest() != SHA256_CONGELADO:
        raise Parada(SAIDA_AMBIENTE, "O original mudou durante o preenchimento.")

    rel.add(f"Células escritas: {len(escritas)} (Cenários O–R: {4 * len(LINHAS_CENARIOS)}; "
            f"Integração F–H: {3 * len(LINHAS_INTEGRACAO)})")
    rel.add(f"Células comparadas fora das colunas amarelas: {len(vals_orig) - len(escritas)} — todas iguais ao original")
    rel.add(f"Original: sha256 {sha256_planilha()} (inalterado)")
    rel.add(f"Cópia: {destino.name} · sha256 {hashlib.sha256(destino.read_bytes()).hexdigest()}")
    rel.add("")
    for (nome_aba, coord), valor in escritas.items():
        if nome_aba == ABA_CENARIOS or coord.startswith("G"):
            rel.add(f"  {nome_aba}!{coord} = {valor}")
    rel.gravar()
    print("\n".join(rel.linhas))
    return SAIDA_OK


if __name__ == "__main__":
    rodar(principal)
