"""Base dos testes de desempenho (execucao/desempenho/base.py): sem banco e sem rede.

Oráculos:
- estatística: o módulo statistics do Python sobre as mesmas amostras (em float,
  só no teste), com tolerância de 1e-9 ms; p95 de n = 30 = 29º valor ordenado;
- regras: o RegraEntrada da API (o mesmo contrato do POST /regras) e as
  regras_padrao do motor para R1 a R3;
- plano: a própria aba Desempenho da planilha congelada.
"""

from __future__ import annotations

import statistics
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from app import motor
from app.api.esquemas import RegraEntrada
from execucao import comum
from execucao.comum import SAIDA_AMBIENTE, SAIDA_EVIDENCIA_SENSIVEL, Parada
from execucao.desempenho import base

# 30 tempos irregulares em ns (fórmula fixa, sem sorteio), entre ~1,2 e ~5,1 ms.
AMOSTRAS = [1_234_567 + (k * 7919 % 104729) * 37 for k in range(30)]
TOLERANCIA_MS = 1e-9


def _ms(amostras: list[int]) -> list[float]:
    return [a / 1_000_000 for a in amostras]  # float só aqui, no oráculo


# --- (1) Estatística ---------------------------------------------------------------

@pytest.mark.parametrize("amostras", [AMOSTRAS, AMOSTRAS[:29], AMOSTRAS[:2]], ids=["n30", "n29", "n2"])
def test_media_mediana_desvio_conferem_com_statistics(amostras):
    e = base.estatisticas(amostras)
    ms = _ms(amostras)
    assert e.n == len(amostras)
    assert abs(float(e.media_ms) - statistics.fmean(ms)) < TOLERANCIA_MS
    assert abs(float(e.mediana_ms) - statistics.median(ms)) < TOLERANCIA_MS
    assert abs(float(e.desvio_ms) - statistics.stdev(ms)) < TOLERANCIA_MS  # amostral (n − 1)
    assert e.minimo_ms == Decimal(min(amostras)) / 1_000_000
    assert e.maximo_ms == Decimal(max(amostras)) / 1_000_000


def test_desvio_e_amostral_e_nao_populacional():
    e = base.estatisticas(AMOSTRAS)
    pstdev = statistics.pstdev(_ms(AMOSTRAS))
    assert abs(float(e.desvio_ms) - pstdev) > 1e-6  # as duas fórmulas dão números diferentes aqui


def test_p95_de_30_amostras_e_o_29o_valor_ordenado():
    e = base.estatisticas(AMOSTRAS)
    assert e.p95_ms == Decimal(sorted(AMOSTRAS)[28]) / 1_000_000
    assert e.p95_ms != Decimal(sorted(AMOSTRAS)[29]) / 1_000_000  # não é o máximo


@pytest.mark.parametrize(
    ("n", "p", "posicao"),
    [(30, 95, 29), (20, 95, 19), (10, 95, 10), (30, 50, 15), (1, 95, 1), (30, 100, 30)],
)
def test_percentil_nearest_rank(n, p, posicao):
    assert base.percentil_nearest_rank(list(range(1, n + 1)), p) == posicao


@pytest.mark.parametrize("p", [0, 101, -5])
def test_percentil_fora_da_faixa(p):
    with pytest.raises(ValueError):
        base.percentil_nearest_rank([1, 2, 3], p)


@pytest.mark.parametrize("amostras", [[], [5], [1, 2.0], [1, True], [1, -1]])
def test_amostras_invalidas(amostras):
    with pytest.raises(ValueError):
        base.estatisticas(amostras)


def test_coeficiente_de_variacao():
    e = base.estatisticas(AMOSTRAS)
    assert e.coef_variacao == e.desvio_ms / e.media_ms
    assert base.estatisticas([0, 0, 0]).coef_variacao is None  # média zero: indefinido, como a fórmula H


@pytest.mark.parametrize(
    ("valor", "esperado"),
    [("0.0005", "0.001"), ("1.23449", "1.234"), ("1.2345", "1.235"), ("2", "2.000")],
)
def test_arredondar_meio_para_cima(valor, esperado):
    assert str(base.arredondar(Decimal(valor))) == esperado


# --- (2) Regras ---------------------------------------------------------------------

DEFINICOES = base.definicoes_regras(50)


def test_codigos_r1_a_r50_em_ordem():
    assert [d.codigo for d in DEFINICOES] == [f"R{k}" for k in range(1, 51)]


def test_r1_a_r3_sao_as_regras_padrao_do_motor():
    assert [d.para_motor() for d in DEFINICOES[:3]] == motor.regras_padrao()


@pytest.mark.parametrize("definicao", DEFINICOES[3:], ids=lambda d: d.codigo)
def test_r4_a_r50_sem_metrica_repetida_e_aceitas_pela_api(definicao):
    metricas = [m for m, _, _ in definicao.condicoes]
    assert len(metricas) == len(set(metricas))
    validada = RegraEntrada.model_validate(definicao.corpo())
    assert [(c.metrica.value, c.operador.value, c.limiar) for c in validada.condicoes] == [
        (m, o, Decimal(l)) for m, o, l in definicao.condicoes
    ]
    assert validada.codigo.upper() not in motor.CODIGOS_REFERENCIA


def test_nenhuma_regra_repete_outra():
    assinaturas = [d.condicoes for d in DEFINICOES]
    assert len(assinaturas) == len(set(assinaturas))


def test_10_regras_sao_as_10_primeiras_das_50():
    assert base.definicoes_regras(10) == DEFINICOES[:10]
    assert base.definicoes_regras(3) == DEFINICOES[:3]


def test_motor_aceita_as_50_regras():
    registro = motor.RegistroMetricas(5000, 150, Decimal("300.00"), Decimal("2"))
    assert len(motor.avaliar(registro, [d.para_motor() for d in DEFINICOES]).regras) == 50


@pytest.mark.parametrize("total", [2, 0, 1000])
def test_total_de_regras_fora_da_faixa(total):
    with pytest.raises(ValueError):
        base.definicoes_regras(total)


def test_p001_a_p035_inativas_aceitas_pela_api():
    codigos = []
    for n in range(1, 36):
        corpo = base.regra_do_de03(n).corpo(ativa=False)
        validada = RegraEntrada.model_validate(corpo)
        assert validada.ativa is False
        codigos.append(validada.codigo)
    assert codigos[0] == "P001" and codigos[-1] == "P035"
    assert len(set(codigos)) == 35
    assert not set(codigos) & {d.codigo for d in DEFINICOES}


# --- (3) Dados ----------------------------------------------------------------------

# Conjunto fixo: se o gerador ou a semente mudarem, o teste reprova (gerar dados novos
# e registrar, em vez de trocar o valor). Calculado em memória em 16/11/2026.
SHA256_10000 = "a18a636c6ff4a92152bbe54a17566d36f8bd9cb378f95224eebf1b290bd7305d"


def test_mesma_semente_mesmo_sha256():
    assert base.sha256_dados(10_000) == base.sha256_dados(10_000) == SHA256_10000


def test_outra_semente_outro_sha256(monkeypatch):
    monkeypatch.setattr(base, "SEMENTE", base.SEMENTE + 1)
    assert base.sha256_dados(10_000) != SHA256_10000


def test_volume_e_periodo_dos_dados():
    assert len(base.registros_motor(10_000)) == base.REGISTROS_ENDPOINTS == 10_000
    metricas = base.metricas_da_campanha(base.ids_campanhas(1)[0])
    assert (metricas[0].data, metricas[-1].data) == (date(2024, 1, 1), date(2026, 9, 26)) == (
        base.INICIO_DADOS,
        base.FIM_DADOS,
    )


def test_periodo_do_de01_dentro_dos_dados_com_30_dias():
    inicio, fim = base.PERIODO_DE01
    assert (inicio, fim) == (date(2026, 8, 28), date(2026, 9, 26))
    assert base.INICIO_DADOS <= inicio <= fim <= base.FIM_DADOS
    assert (fim - inicio).days + 1 == 30


@pytest.mark.parametrize("volume", [0, 1500, -1000])
def test_volume_invalido(volume):
    with pytest.raises(ValueError):
        base.registros_motor(volume)


def test_ids_de_campanha_ficticios():
    assert base.ids_campanhas(3) == [900_001, 900_002, 900_003]


# --- (4) Padrões locais e evidências ------------------------------------------------

@pytest.fixture
def maquina_falsa(monkeypatch):
    monkeypatch.setattr(base.socket, "gethostname", lambda: "estacao-teste.local")
    monkeypatch.setattr(base.getpass, "getuser", lambda: "fulano")
    monkeypatch.setattr(base.Path, "home", classmethod(lambda cls: Path("/srv/pessoal-fulano")))


@pytest.mark.parametrize(
    ("texto", "padrao"),
    [
        ("Rodado em estacao-teste.local", "hostname"),
        ("Rodado em ESTACAO-TESTE", "hostname (primeiro nome)"),
        ("Executado por fulano", "usuário do sistema"),
        ("arquivo em /srv/pessoal-fulano/x.txt", "pasta pessoal"),
        ("arquivo em /home/outra/x.txt", "caminho /home"),
        ("callback?state=x&code=4/abc", "URL com parâmetro code"),
        ("Authorization: Bearer abc", "cabeçalho Authorization"),
    ],
    # ids próprios: sem eles o pytest -v põe o texto do caso no nome do teste, e o
    # "/home/outra" falso apareceria na evidência do pytest.
    ids=["hostname", "hostname-primeiro-nome", "usuario", "pasta-pessoal", "caminho-home", "url-code", "authorization"],
)
def test_padroes_locais_bloqueiam(maquina_falsa, texto, padrao):
    assert padrao in base.achados(texto)


def test_texto_sem_padroes_passa(maquina_falsa):
    texto = (
        "CPU AMD Ryzen 7 (12 núcleos lógicos), 15.4 GiB, Zorin OS 18 (kernel 7.0.0-43-generic)\n"
        "fulanos estacao-testes codec=1 /srv/outra limen_desempenho"
    )
    assert base.achados(texto) == []


def test_ambiente_real_sem_padroes():
    """Na máquina real: se o hostname coincidir com algo do ambiente, reprova (não afrouxar)."""
    amb = base.ambiente("16.15 (teste)")
    texto = "\n".join(f"{k}: {v}" for k, v in amb.items()) + "\n" + base.resumo_ambiente(amb)
    assert base.achados(texto) == []


def test_gravar_recusa_padrao_local_e_nao_grava(maquina_falsa, monkeypatch, tmp_path):
    monkeypatch.setattr(comum, "DIR_EVIDENCIAS", tmp_path)
    rel = comum.Relatorio("desempenho_teste.txt")
    rel.add("rodado em estacao-teste")
    with pytest.raises(Parada) as erro:
        base.gravar(rel)
    assert erro.value.codigo == SAIDA_EVIDENCIA_SENSIVEL
    assert "estacao-teste" not in erro.value.mensagem  # só o nome do padrão
    assert list(tmp_path.iterdir()) == []


def test_gravar_recusa_padrao_do_comum(maquina_falsa, monkeypatch, tmp_path):
    monkeypatch.setattr(comum, "DIR_EVIDENCIAS", tmp_path)
    rel = comum.Relatorio("desempenho_teste.txt")
    rel.add("contato: alguem@exemplo.com")
    with pytest.raises(Parada) as erro:
        base.gravar(rel)
    assert erro.value.codigo == SAIDA_EVIDENCIA_SENSIVEL
    assert list(tmp_path.iterdir()) == []


def test_gravar_texto_limpo(maquina_falsa, monkeypatch, tmp_path):
    monkeypatch.setattr(comum, "DIR_EVIDENCIAS", tmp_path)
    rel = comum.Relatorio("desempenho_teste.txt")
    rel.add("DM-01 média 0,512 ms")
    (caminho,) = base.gravar(rel)
    assert caminho.parent == tmp_path
    assert caminho.read_text(encoding="utf-8") == "DM-01 média 0,512 ms\n"


# --- Cabeçalho (mutação B2) ---------------------------------------------------------

def test_cabecalho_para_com_codigo_fora_do_commit(monkeypatch):
    monkeypatch.setattr(comum, "_fora_do_commit", lambda: (["?? backend/execucao/desempenho/x.py"], []))
    with pytest.raises(Parada) as erro:
        base.cabecalho("execucao/desempenho/teste.py", "Teste")
    assert erro.value.codigo == SAIDA_AMBIENTE


def test_cabecalho_sem_codigo_fora_tem_as_linhas_que_o_preencher_le(monkeypatch):
    from execucao.preencher_planilha import PADRAO_CODIGO_FORA, PADRAO_COMMIT

    monkeypatch.setattr(comum, "_fora_do_commit", lambda: ([], ["?? docs/evidencias/x.txt"]))
    texto = "\n".join(base.cabecalho("execucao/desempenho/teste.py", "Teste"))
    assert PADRAO_CODIGO_FORA.search(texto).group(1) == "0"
    assert PADRAO_COMMIT.search(texto)
    assert "Banco: limen_desempenho" in texto
    assert "  ?? docs/evidencias/x.txt" in texto  # evidências só listadas
    sem_banco = "\n".join(base.cabecalho("execucao/desempenho/teste.py", "Teste", usa_banco=False))
    assert "Banco: não usado (motor em memória)" in sem_banco


# --- Plano e trava do banco ---------------------------------------------------------

def test_plano_lido_da_planilha():
    plano = base.ler_plano()
    assert (plano.aquecimentos, plano.repeticoes) == (5, 30)
    assert [i for i, _, _ in plano.motor] == [f"DM-0{n}" for n in range(1, 10)]
    assert {(v, r) for _, v, r in plano.motor} == {(v, r) for v in (1000, 10000, 100000) for r in (3, 10, 50)}
    assert [i for i, _ in plano.endpoints] == ["DE-01", "DE-02", "DE-03", "DE-04"]
    assert tuple(e for _, e in plano.endpoints) == base.ENDPOINTS_FIXOS


def test_base_dos_endpoints_igual_a_planilha():
    from openpyxl import load_workbook

    titulo = load_workbook(comum.PLANILHA)["Desempenho"]["A20"].value
    assert f"base de {base.REGISTROS_ENDPOINTS:,} registros e {base.REGRAS_ENDPOINTS} regras".replace(",", ".") in titulo


URL_FALSA = "postgresql+psycopg://usuario_falso:senha_falsa@127.0.0.1:5433/{banco}"


@pytest.mark.parametrize("banco", ["limen", "limen_teste", "limen_execucao", "outro"])
def test_trava_recusa_outros_bancos(monkeypatch, banco):
    monkeypatch.setenv("DATABASE_URL", URL_FALSA.format(banco=banco))
    with pytest.raises(Parada) as erro:
        base.url_desempenho()
    assert erro.value.codigo == SAIDA_AMBIENTE
    assert "senha_falsa" not in erro.value.mensagem and "usuario_falso" not in erro.value.mensagem


def test_trava_aceita_limen_desempenho(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", URL_FALSA.format(banco="limen_desempenho"))
    assert base.url_desempenho().database == "limen_desempenho"


def test_trava_sem_url(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(Parada) as erro:
        base.url_desempenho()
    assert erro.value.codigo == SAIDA_AMBIENTE
