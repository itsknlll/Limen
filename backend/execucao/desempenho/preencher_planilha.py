"""Cópia preenchida da planilha com os resultados de desempenho (aba Desempenho).

Uso (sem banco: lê só planilhas e .json/.txt das evidências; não usa DATABASE_URL):

    python -m execucao.desempenho.preencher_planilha [--data AAAA-MM-DD]
        [--data-motor AAAA-MM-DD] [--data-endpoints AAAA-MM-DD]

Parte de: docs/evidencias/2026-11-16_execucao_tabela_preenchida.xlsx (a cópia da
execução formal), conferida pelo sha256 registrado em 2026-11-16_execucao_planilha.txt.
Grava: docs/evidencias/<hoje>_desempenho_tabela_preenchida.xlsx (arquivo novo; se
existir, para). Nenhuma das duas planilhas de origem é alterada.

Escreve SÓ as 66 células amarelas da aba Desempenho:
  B5 (ambiente, uma linha);
  D, E, F, G, I das linhas 10 a 18 (DM-01 a DM-09) e 22 a 25 (DE-01 a DE-04):
  média, desvio padrão (amostral), mínimo, máximo (ms, 3 casas) e falhas.
A coluna I recebe só as falhas das repetições medidas (as do aquecimento ficam fora,
mas qualquer falha, medida ou não, impede o preenchimento: ver travas).
A coluna H é fórmula (E/D) e não é escrita: é recalculada ao abrir no LibreOffice
(Ctrl+Shift+F9); o CV esperado de cada linha vai na evidência para conferir.
Mediana e p95 não têm coluna na planilha congelada: ficam só na evidência.

Números: recalculados por base.estatisticas a partir das amostras em ns do .json
(nunca dos textos formatados do .txt) e conferidos contra a estatística que o
próprio .json registrou; diferença → para com 1.

Travas (antes de escrever qualquer célula):
- .txt e .json do motor e dos endpoints presentes; os dois .txt com o mesmo commit
  e "Código fora do commit ...: 0"; os dois com "Resultado: sem falhas";
- no .json: nenhuma falha (medida ou de aquecimento), oráculo R1 a R3 ok no motor,
  número de aquecimentos e repetições igual ao da planilha, IDs, volumes, regras e
  endpoints iguais às linhas da aba;
- sha256 da planilha congelada = o do commit 29de91d e sha256 da cópia da execução
  formal = o registrado;
- as 66 células estão vazias na cópia de origem.
Depois de gravar: compara célula por célula todas as abas da cópia nova com a de
origem; fora das 66, tudo igual (valor ou fórmula); as 66 relidas iguais ao escrito.
Senão apaga a cópia nova. No fim, confere de novo os dois sha256 de origem (se um
mudou, a cópia nova também é apagada).

Saída: 0 ok · 1 estatística ou cópia divergente (cópia apagada) · 3 ambiente ou
pré-condição (evidência ausente, commit diferente, código fora do commit, falhas,
planilha de origem alterada) · 4 evidência sensível · 5 erro inesperado.
Evidência: docs/evidencias/<hoje>_desempenho_planilha.txt
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from openpyxl import load_workbook

from .. import comum
from ..comum import FUSO, SAIDA_AMBIENTE, SAIDA_DIVERGENCIA, SAIDA_OK, Parada, Relatorio, rodar
from ..preencher_planilha import PADRAO_CODIGO_FORA, PADRAO_COMMIT
from . import base

ABA = "Desempenho"
NOME_COPIA_EXECUCAO = "2026-11-16_execucao_tabela_preenchida.xlsx"
NOME_TXT_EXECUCAO = "2026-11-16_execucao_planilha.txt"
PADRAO_SHA_COPIA = re.compile(rf"^Cópia: {re.escape(NOME_COPIA_EXECUCAO)} · sha256 ([0-9a-f]{{64}})$", re.M)
COLUNAS = {"media_ms": "D", "desvio_ms": "E", "minimo_ms": "F", "maximo_ms": "G"}
COLUNA_FALHAS = "I"
CELULA_AMBIENTE = "B5"
TOTAL_CELULAS = 66


# Caminhos lidos na hora (comum.DIR_EVIDENCIAS e comum.PLANILHA), para o teste poder trocá-los.
def copia_execucao() -> Path:
    return comum.DIR_EVIDENCIAS / NOME_COPIA_EXECUCAO


def txt_execucao() -> Path:
    return comum.DIR_EVIDENCIAS / NOME_TXT_EXECUCAO


def sha256(caminho: Path) -> str:
    return hashlib.sha256(caminho.read_bytes()).hexdigest()


def sha_registrado_da_copia() -> str:
    txt = txt_execucao()
    if not txt.exists():
        raise Parada(SAIDA_AMBIENTE, f"Falta {txt.name}.")
    achado = PADRAO_SHA_COPIA.search(txt.read_text(encoding="utf-8"))
    if not achado:
        raise Parada(SAIDA_AMBIENTE, f"{txt.name} não registra o sha256 da cópia.")
    return achado.group(1)


def conferir_origens(sha_copia: str) -> None:
    if sha256(comum.PLANILHA) != comum.SHA256_CONGELADO:
        raise Parada(SAIDA_AMBIENTE, "Planilha congelada diferente da do commit 29de91d.")
    copia = copia_execucao()
    if not copia.exists() or sha256(copia) != sha_copia:
        raise Parada(SAIDA_AMBIENTE, f"{copia.name} ausente ou diferente da registrada.")


def ler_evidencia(data: str, nome: str) -> tuple[dict, str]:
    """(.json, commit) de uma medição; exige código igual ao commit e resultado sem falhas."""
    txt = comum.DIR_EVIDENCIAS / f"{data}_desempenho_{nome}.txt"
    js = comum.DIR_EVIDENCIAS / f"{data}_desempenho_{nome}.json"
    if not (txt.exists() and js.exists()):
        raise Parada(SAIDA_AMBIENTE, f"Faltam {txt.name} ou {js.name}.")
    texto = txt.read_text(encoding="utf-8")
    commit, fora = PADRAO_COMMIT.search(texto), PADRAO_CODIGO_FORA.search(texto)
    if not commit or not fora or fora.group(1) != "0":
        raise Parada(SAIDA_AMBIENTE, f"{txt.name}: a medição não rodou com o código igual ao commit.")
    if not re.search(r"^Resultado: sem falhas$", texto, re.M):
        raise Parada(SAIDA_AMBIENTE, f"{txt.name}: o resultado não foi 'sem falhas'.")
    return json.loads(js.read_text(encoding="utf-8")), commit.group(1)


def recalcular(item: dict, plano: base.Plano, rotulo: str) -> base.Estatisticas:
    """Estatística das amostras em ns, conferida contra a que o .json registrou."""
    if len(item["aquecimentos_ns"]) != plano.aquecimentos or len(item["amostras_ns"]) != plano.repeticoes:
        raise Parada(SAIDA_AMBIENTE, f"{rotulo}: aquecimentos ou repetições diferentes da planilha.")
    est = base.estatisticas(item["amostras_ns"])
    registrado = item["estatisticas"]
    for campo in ("media_ms", "mediana_ms", "desvio_ms", "minimo_ms", "maximo_ms", "p95_ms"):
        if Decimal(registrado[campo]) != getattr(est, campo):
            raise Parada(SAIDA_DIVERGENCIA, f"{rotulo}: {campo} recalculado diferente do registrado no .json.")
    return est


Linhas = dict[int, tuple[str, base.Estatisticas, int]]  # linha → (ID, estatística, falhas medidas)


def linhas_motor(dados: dict, plano: base.Plano) -> Linhas:
    por_id = {c["id"]: c for c in dados["combinacoes"]}
    saida: Linhas = {}
    for linha, (id_, volume, regras) in zip(base.LINHAS_MOTOR, plano.motor):
        c = por_id.pop(id_, None)
        if c is None or (c["registros"], c["regras_ativas"]) != (volume, regras):
            raise Parada(SAIDA_AMBIENTE, f"{id_}: ausente no .json do motor ou com volume/regras diferentes.")
        if c["falhas"] or not c["oraculo_r1_r3_ok"]:
            raise Parada(SAIDA_AMBIENTE, f"{id_}: há falhas ou o oráculo de R1 a R3 não conferiu.")
        saida[linha] = (id_, recalcular(c, plano, id_), c["falhas_medidas"])
    if por_id:
        raise Parada(SAIDA_AMBIENTE, f"Combinações a mais no .json do motor: {sorted(por_id)}")
    return saida


def linhas_endpoints(dados: dict, plano: base.Plano) -> Linhas:
    endpoints = dict(dados["endpoints"])
    saida: Linhas = {}
    for linha, (id_, endpoint) in zip(base.LINHAS_ENDPOINTS, plano.endpoints):
        e = endpoints.pop(id_, None)
        if e is None or e["endpoint"] != endpoint:
            raise Parada(SAIDA_AMBIENTE, f"{id_}: ausente no .json dos endpoints ou com outro endpoint.")
        if e["falhas_medidas"] or e["falhas_aquecimento"]:
            raise Parada(SAIDA_AMBIENTE, f"{id_}: há falhas.")
        saida[linha] = (id_, recalcular(e, plano, id_), e["falhas_medidas"])
    if endpoints:
        raise Parada(SAIDA_AMBIENTE, f"Endpoints a mais no .json: {sorted(endpoints)}")
    return saida


def celulas(motor: Linhas, endpoints: Linhas, resumo_ambiente: str) -> dict[str, object]:
    """As 66 células: {coordenada: valor}. ms com 3 casas (Decimal); falhas inteiras."""
    escritas: dict[str, object] = {CELULA_AMBIENTE: resumo_ambiente}
    for linha, (_id, est, falhas) in {**motor, **endpoints}.items():
        for campo, coluna in COLUNAS.items():
            escritas[f"{coluna}{linha}"] = base.arredondar(getattr(est, campo))
        escritas[f"{COLUNA_FALHAS}{linha}"] = falhas
    return escritas


def _igual(relido: object, escrito: object) -> bool:
    # openpyxl devolve número como int/float; Decimal == float compara o binário, então
    # o relido passa por str antes (1.234 → Decimal("1.234")).
    if isinstance(escrito, Decimal):
        return isinstance(relido, (int, float)) and not isinstance(relido, bool) and Decimal(str(relido)) == escrito
    return relido == escrito


def _valores(wb) -> dict[tuple[str, str], object]:
    return {(aba.title, c.coordinate): c.value for aba in wb.worksheets for linha in aba.iter_rows() for c in linha}


def cv_esperado(escritas: dict[str, object], linha: int) -> str:
    d, e = escritas[f"D{linha}"], escritas[f"E{linha}"]
    return "—" if d == 0 else str(base.arredondar(e / d, 4))


def principal(argv: list[str] | None = None) -> int:
    args = argparse.ArgumentParser()
    hoje = datetime.now(FUSO).date().isoformat()
    args.add_argument("--data", default=hoje)
    args.add_argument("--data-motor")
    args.add_argument("--data-endpoints")
    opcoes = args.parse_args(argv)
    data_motor = opcoes.data_motor or opcoes.data
    data_endpoints = opcoes.data_endpoints or opcoes.data
    for d in (data_motor, data_endpoints):
        date.fromisoformat(d)

    rel = Relatorio("desempenho_planilha.txt")
    for linha in base.cabecalho("execucao/desempenho/preencher_planilha.py", "Desempenho — planilha preenchida",
                                usa_banco=False, motivo_sem_banco="lê só planilhas e evidências"):
        rel.add(linha)
    destino = comum.DIR_EVIDENCIAS / f"{hoje}_desempenho_tabela_preenchida.xlsx"
    if destino.exists():
        raise Parada(SAIDA_AMBIENTE, f"{destino.name} já existe; não sobrescrevo.")

    sha_copia = sha_registrado_da_copia()
    conferir_origens(sha_copia)
    plano = base.ler_plano()

    dados_motor, commit_m = ler_evidencia(data_motor, "motor")
    dados_endp, commit_e = ler_evidencia(data_endpoints, "endpoints")
    if commit_m != commit_e:
        raise Parada(SAIDA_AMBIENTE, "Motor e endpoints rodaram em commits diferentes.")
    motor = linhas_motor(dados_motor, plano)
    endpoints = linhas_endpoints(dados_endp, plano)
    escritas = celulas(motor, endpoints, dados_endp["resumo_ambiente_b5"])
    if len(escritas) != TOTAL_CELULAS:
        raise Parada(SAIDA_AMBIENTE, f"Esperadas {TOTAL_CELULAS} células, montadas {len(escritas)}.")

    origem_path = copia_execucao()
    origem = load_workbook(origem_path)  # fórmulas preservadas (data_only=False)
    copia = load_workbook(origem_path)
    vals_origem = _valores(origem)
    ocupadas = [c for c in escritas if vals_origem.get((ABA, c)) is not None]
    if ocupadas:
        raise Parada(SAIDA_AMBIENTE, f"Células já preenchidas na cópia de origem: {ocupadas}")
    for coord, valor in escritas.items():
        copia[ABA][coord] = valor
    copia.save(destino)

    relida = _valores(load_workbook(destino))
    alvo = {(ABA, c) for c in escritas}
    fora = [k for k in set(vals_origem) | set(relida) if k not in alvo and vals_origem.get(k) != relida.get(k)]
    erradas = [c for c, v in escritas.items() if not _igual(relida.get((ABA, c)), v)]
    if fora or erradas:
        destino.unlink()
        raise Parada(SAIDA_DIVERGENCIA, f"Cópia diferente da origem ({len(fora)} fora das {TOTAL_CELULAS}, "
                                        f"{len(erradas)} escritas erradas): apagada.")
    try:
        conferir_origens(sha_copia)
    except Parada as parada:
        destino.unlink()
        raise Parada(parada.codigo, f"{parada.mensagem} A cópia nova foi apagada.") from None

    rel.add(f"Medições lidas: motor {data_motor}, endpoints {data_endpoints}; commit {commit_m} (os dois)")
    rel.add(f"Origem: {origem_path.name} · sha256 {sha_copia} (o registrado em {NOME_TXT_EXECUCAO}; inalterado)")
    rel.add(f"Planilha congelada: sha256 {comum.SHA256_CONGELADO} (inalterada)")
    rel.add(f"Cópia nova: {destino.name} · sha256 {sha256(destino)}")
    rel.add(f"Células escritas: {len(escritas)} (B5 + D, E, F, G, I × 13 linhas); comparadas fora delas: "
            f"{len(vals_origem) - len(escritas)}, todas iguais à origem")
    rel.add("")
    rel.add("Estatística recalculada das amostras em ns (igual à registrada no .json):")
    rel.add("Linha ID     Média(D)  Desvio(E)  Mín(F)    Máx(G)    Falhas(I)  CV esperado(H)  Mediana   p95")
    for linha, (id_, est, falhas) in {**motor, **endpoints}.items():
        rel.add(
            f"{linha:>5} {id_:<6} {escritas[f'D{linha}']:>9} {escritas[f'E{linha}']:>10} "
            f"{escritas[f'F{linha}']:>9} {escritas[f'G{linha}']:>9} {falhas:>9}  "
            f"{cv_esperado(escritas, linha):>14}  {base.arredondar(est.mediana_ms):>8} {base.arredondar(est.p95_ms):>8}"
        )
    rel.add("")
    rel.add(f"B5: {escritas[CELULA_AMBIENTE]}")
    rel.add("")
    rel.add("Coluna H: fórmula da planilha, não escrita. Abrir a cópia no LibreOffice, Dados → Calcular →")
    rel.add("Recalcular incondicionalmente (Ctrl+Shift+F9), conferir com o 'CV esperado' acima e NÃO salvar")
    rel.add("por cima (o sha256 acima é o da cópia gerada).")
    base.gravar(rel)
    print("\n".join(rel.linhas))
    return SAIDA_OK


if __name__ == "__main__":
    rodar(principal)
