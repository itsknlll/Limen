"""Preenchimento da aba Desempenho (execucao/desempenho/preencher_planilha.py).

Roda numa pasta temporária: a cópia da execução formal e o .txt que registra o
sha256 dela são COPIADOS para tmp_path (os de docs/evidencias/ só são lidos), e
as evidências do motor e dos endpoints são montadas aqui com amostras fixas.
A planilha congelada é só lida (sha256 conferido no fim).
Oráculo: a estatística das amostras por base.estatisticas (testada contra o
módulo statistics) e a cópia de origem, célula por célula.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from decimal import Decimal

import pytest
from openpyxl import load_workbook

from execucao import comum
from execucao.comum import SAIDA_AMBIENTE, SAIDA_DIVERGENCIA, SAIDA_OK, Parada
from execucao.desempenho import base
from execucao.desempenho import preencher_planilha as pp

DATA = "2026-11-17"
COMMIT = "a" * 40
AQUECIMENTOS = [900_000] * 5
DIR_REAL = comum.DIR_EVIDENCIAS
SHA_COPIA_REAL = hashlib.sha256((DIR_REAL / pp.NOME_COPIA_EXECUCAO).read_bytes()).hexdigest()


def _amostras(base_ns: int, n: int = 30) -> list[int]:
    return [base_ns + (k * 7919 % 1013) * 11 for k in range(n)]


def _est(amostras: list[int]) -> dict:
    e = base.estatisticas(amostras)
    return {k: str(getattr(e, k)) for k in ("media_ms", "mediana_ms", "desvio_ms", "minimo_ms", "maximo_ms", "p95_ms")}


def _item(base_ns: int) -> dict:
    amostras = _amostras(base_ns)
    return {"aquecimentos_ns": AQUECIMENTOS, "amostras_ns": amostras, "estatisticas": _est(amostras)}


def json_motor(plano: base.Plano) -> dict:
    return {"combinacoes": [
        {"id": id_, "registros": volume, "regras_ativas": regras, "falhas": [], "falhas_medidas": 0,
         "oraculo_r1_r3_ok": True, **_item(1_000_000 * (i + 1))}
        for i, (id_, volume, regras) in enumerate(plano.motor)
    ]}


def json_endpoints(plano: base.Plano) -> dict:
    return {
        "resumo_ambiente_b5": "CPU de teste (4 núcleos lógicos), 8.0 GiB, SO de teste; mesma máquina",
        "endpoints": {
            id_: {"endpoint": endpoint, "falhas_medidas": 0, "falhas_aquecimento": 0, **_item(3_000_000 * (i + 1))}
            for i, (id_, endpoint) in enumerate(plano.endpoints)
        },
    }


def txt(commit: str = COMMIT, fora: int = 0, resultado: str = "sem falhas") -> str:
    return (
        "Desempenho\n"
        f"Commit do código (git rev-parse HEAD): {commit}\n"
        f"Código fora do commit (git status, fora de docs/evidencias/): {fora}\n"
        f"Resultado: {resultado}\n"
    )


@pytest.fixture
def pasta(tmp_path, monkeypatch):
    """tmp_path no lugar de docs/evidencias/, com a cópia formal e as evidências montadas."""
    monkeypatch.setattr(comum, "DIR_EVIDENCIAS", tmp_path)
    monkeypatch.setattr(comum, "_fora_do_commit", lambda: ([], []))  # o código real ainda não está no git
    shutil.copy2(DIR_REAL / pp.NOME_COPIA_EXECUCAO, tmp_path / pp.NOME_COPIA_EXECUCAO)
    shutil.copy2(DIR_REAL / pp.NOME_TXT_EXECUCAO, tmp_path / pp.NOME_TXT_EXECUCAO)
    plano = base.ler_plano()

    def gravar(motor=None, endpoints=None, txt_motor=None, txt_endpoints=None):
        (tmp_path / f"{DATA}_desempenho_motor.json").write_text(json.dumps(motor or json_motor(plano)))
        (tmp_path / f"{DATA}_desempenho_endpoints.json").write_text(json.dumps(endpoints or json_endpoints(plano)))
        (tmp_path / f"{DATA}_desempenho_motor.txt").write_text(txt_motor or txt())
        (tmp_path / f"{DATA}_desempenho_endpoints.txt").write_text(txt_endpoints or txt())

    gravar()
    return tmp_path, plano, gravar


def _rodar():
    return pp.principal(["--data", DATA])


def _copias_novas(pasta_tmp):
    return sorted(pasta_tmp.glob("*_desempenho_tabela_preenchida.xlsx"))


def _parar(codigo):
    with pytest.raises(Parada) as erro:
        _rodar()
    assert erro.value.codigo == codigo
    return erro.value


# --- Caminho feliz -----------------------------------------------------------------

def test_preenche_as_66_celulas_e_nada_mais(pasta):
    tmp, plano, _ = pasta
    assert _rodar() == SAIDA_OK
    (nova,) = _copias_novas(tmp)
    origem = load_workbook(tmp / pp.NOME_COPIA_EXECUCAO)
    copia = load_workbook(nova)
    aba = copia["Desempenho"]

    motor = json_motor(plano)["combinacoes"]
    for linha, c in zip(base.LINHAS_MOTOR, motor):
        e = base.estatisticas(c["amostras_ns"])
        assert Decimal(str(aba[f"D{linha}"].value)) == base.arredondar(e.media_ms)
        assert Decimal(str(aba[f"E{linha}"].value)) == base.arredondar(e.desvio_ms)
        assert Decimal(str(aba[f"F{linha}"].value)) == base.arredondar(e.minimo_ms)
        assert Decimal(str(aba[f"G{linha}"].value)) == base.arredondar(e.maximo_ms)
        assert aba[f"I{linha}"].value == 0
    for linha in [*base.LINHAS_MOTOR, *base.LINHAS_ENDPOINTS]:
        assert str(aba[f"H{linha}"].value).startswith("=IF(")  # fórmula intacta, não escrita
        assert aba[f"H{linha}"].value == origem["Desempenho"][f"H{linha}"].value
    assert aba["B5"].value.startswith("CPU de teste")

    escritas = {"B5"} | {f"{col}{l}" for l in [*base.LINHAS_MOTOR, *base.LINHAS_ENDPOINTS] for col in "DEFGI"}
    assert len(escritas) == 66
    diferentes = [
        (o.title, c.coordinate)
        for o in origem.worksheets
        for linha in o.iter_rows()
        for c in linha
        if c.value != copia[o.title][c.coordinate].value
    ]
    assert sorted(diferentes) == sorted(("Desempenho", c) for c in escritas)


def test_origens_continuam_com_o_mesmo_sha256(pasta):
    tmp, _, _ = pasta
    assert _rodar() == SAIDA_OK
    assert hashlib.sha256((tmp / pp.NOME_COPIA_EXECUCAO).read_bytes()).hexdigest() == SHA_COPIA_REAL
    assert hashlib.sha256((DIR_REAL / pp.NOME_COPIA_EXECUCAO).read_bytes()).hexdigest() == SHA_COPIA_REAL
    assert hashlib.sha256(comum.PLANILHA.read_bytes()).hexdigest() == comum.SHA256_CONGELADO


def test_evidencia_tem_cv_esperado_mediana_e_p95(pasta):
    tmp, _, _ = pasta
    _rodar()
    (texto,) = [p.read_text(encoding="utf-8") for p in tmp.glob("*_desempenho_planilha.txt")]
    assert "CV esperado(H)" in texto and "Mediana" in texto and "p95" in texto
    assert "Banco: não usado (lê só planilhas e evidências)" in texto
    assert "Ctrl+Shift+F9" in texto


# --- Travas: nada é gravado ----------------------------------------------------------

def test_commits_diferentes(pasta):
    tmp, _, gravar = pasta
    gravar(txt_endpoints=txt(commit="b" * 40))
    assert "commits diferentes" in _parar(SAIDA_AMBIENTE).mensagem
    assert _copias_novas(tmp) == []


@pytest.mark.parametrize("qual", ["motor", "endpoints"])
def test_codigo_fora_do_commit(pasta, qual):
    tmp, _, gravar = pasta
    gravar(**{f"txt_{qual}": txt(fora=1)})
    _parar(SAIDA_AMBIENTE)
    assert _copias_novas(tmp) == []


@pytest.mark.parametrize("qual", ["motor", "endpoints"])
def test_resultado_com_falhas(pasta, qual):
    tmp, _, gravar = pasta
    gravar(**{f"txt_{qual}": txt(resultado="COM FALHAS")})
    _parar(SAIDA_AMBIENTE)
    assert _copias_novas(tmp) == []


def test_falha_so_no_aquecimento_tambem_impede(pasta):
    tmp, plano, gravar = pasta
    endpoints = json_endpoints(plano)
    endpoints["endpoints"]["DE-02"]["falhas_aquecimento"] = 1
    gravar(endpoints=endpoints)
    _parar(SAIDA_AMBIENTE)
    assert _copias_novas(tmp) == []


def test_falha_no_motor_impede(pasta):
    tmp, plano, gravar = pasta
    motor = json_motor(plano)
    motor["combinacoes"][4]["falhas"] = [{"execucao": 2, "medida": False, "motivo": "x"}]
    gravar(motor=motor)
    _parar(SAIDA_AMBIENTE)
    assert _copias_novas(tmp) == []


def test_estatistica_adulterada_no_json(pasta):
    tmp, plano, gravar = pasta
    motor = json_motor(plano)
    motor["combinacoes"][0]["estatisticas"]["media_ms"] = "0.001"
    gravar(motor=motor)
    assert "recalculado" in _parar(SAIDA_DIVERGENCIA).mensagem
    assert _copias_novas(tmp) == []


def test_29_repeticoes(pasta):
    _, plano, gravar = pasta
    endpoints = json_endpoints(plano)
    amostras = _amostras(3_000_000, n=29)
    endpoints["endpoints"]["DE-01"].update(amostras_ns=amostras, estatisticas=_est(amostras))
    gravar(endpoints=endpoints)
    _parar(SAIDA_AMBIENTE)


def test_volume_diferente_da_planilha(pasta):
    _, plano, gravar = pasta
    motor = json_motor(plano)
    motor["combinacoes"][0]["registros"] = 2000
    gravar(motor=motor)
    _parar(SAIDA_AMBIENTE)


def test_copia_da_execucao_alterada(pasta):
    tmp, _, _ = pasta
    with open(tmp / pp.NOME_COPIA_EXECUCAO, "ab") as f:
        f.write(b"\0")
    assert "diferente da registrada" in _parar(SAIDA_AMBIENTE).mensagem
    assert _copias_novas(tmp) == []


def test_celula_ja_preenchida_na_origem(pasta):
    tmp, _, _ = pasta
    origem = tmp / pp.NOME_COPIA_EXECUCAO
    wb = load_workbook(origem)
    wb["Desempenho"]["D10"] = 1
    wb.save(origem)
    novo_sha = hashlib.sha256(origem.read_bytes()).hexdigest()
    registro = tmp / pp.NOME_TXT_EXECUCAO
    registro.write_text(registro.read_text(encoding="utf-8").replace(SHA_COPIA_REAL, novo_sha), encoding="utf-8")
    assert "já preenchidas" in _parar(SAIDA_AMBIENTE).mensagem
    assert _copias_novas(tmp) == []


def test_segunda_execucao_no_mesmo_dia(pasta):
    tmp, _, _ = pasta
    assert _rodar() == SAIDA_OK
    # o .txt da evidência e o .xlsx já existem: para com 3 e não cria outra cópia
    _parar(SAIDA_AMBIENTE)
    assert len(_copias_novas(tmp)) == 1


# --- Funções puras ----------------------------------------------------------------

@pytest.mark.parametrize(
    ("relido", "escrito", "igual"),
    [
        (1.234, Decimal("1.234"), True),
        (35.123, Decimal("35.123"), True),
        (1.2340000001, Decimal("1.234"), False),
        ("1.234", Decimal("1.234"), False),
        (True, Decimal("1"), False),
        (0, 0, True),
        ("CPU x", "CPU x", True),
    ],
)
def test_igual(relido, escrito, igual):
    assert pp._igual(relido, escrito) is igual


def test_cv_esperado():
    assert pp.cv_esperado({"D10": Decimal("2.000"), "E10": Decimal("0.500")}, 10) == "0.2500"
    assert pp.cv_esperado({"D10": Decimal("0"), "E10": Decimal("0.500")}, 10) == "—"


def test_coluna_i_recebe_as_falhas_da_linha():
    est = base.estatisticas(_amostras(1_000_000))
    escritas = pp.celulas({10: ("DM-01", est, 2)}, {22: ("DE-01", est, 0)}, "amb")
    assert escritas["I10"] == 2 and escritas["I22"] == 0
    assert "H10" not in escritas and "H22" not in escritas
