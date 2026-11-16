"""Partes próprias do medir_motor (execucao/desempenho/medir_motor.py), sem medir de verdade.

Volume pequeno (1.000 registros, uma campanha do gerador) e plano curto
(1 aquecimento + 2 repetições). Cobre: o oráculo de R1 a R3 pelos perfis do gerador,
a falha quando uma execução dá disparos diferentes da passada de referência, a falha
por exceção e a ordem dentro de _uma_execucao (gc.collect fora do cronômetro; só a
avaliação entre os dois relógios).
"""

from __future__ import annotations

from collections import Counter

import pytest

from execucao.desempenho import base
from execucao.desempenho import medir_motor as mm

PLANO = base.Plano(aquecimentos=1, repeticoes=2, motor=(), endpoints=())


@pytest.fixture(scope="module")
def registros():
    return base.registros_motor(1000)


def test_combinacao_normal_sem_falhas_e_oraculo_ok(registros):
    r = mm.medir_combinacao("DM-01", 1000, 3, PLANO, registros)
    assert r["oraculo_r1_r3_ok"] is True
    assert r["disparos_por_regra"] == {"R1": 3, "R2": 3, "R3": 3}  # 3 dias de cada perfil por campanha
    assert r["falhas"] == [] and r["falhas_medidas"] == 0
    assert len(r["aquecimentos_ns"]) == 1 and len(r["amostras_ns"]) == 2
    assert r["estatisticas"]["n"] == 2
    assert r["regras_sem_disparo"] == []


def test_disparos_por_regra_com_10_regras_recontados_a_parte(registros):
    r = mm.medir_combinacao("DM-02", 1000, 10, PLANO, registros)
    regras = [d.para_motor() for d in base.definicoes_regras(10)]
    recontagem = Counter()
    for registro in registros:
        recontagem.update(mm.motor.avaliar(registro, regras).disparadas)
    assert r["disparos_por_regra"] == {d.codigo: recontagem.get(d.codigo, 0) for d in base.definicoes_regras(10)}
    assert r["oraculo_r1_r3_ok"] is True


def test_execucao_com_disparos_diferentes_conta_como_falha(registros, monkeypatch):
    original = mm._uma_execucao
    chamadas = []

    def alterada(regs, regras):
        chamadas.append(1)
        ns, resultados = original(regs, regras)
        if len(chamadas) == 2:  # 1ª repetição medida (a 1ª chamada é o aquecimento)
            return ns, resultados[:0]  # nenhum disparo: diferente da referência
        return ns, resultados

    monkeypatch.setattr(mm, "_uma_execucao", alterada)
    r = mm.medir_combinacao("DM-01", 1000, 3, PLANO, registros)
    assert r["falhas"] == [{"execucao": 2, "medida": True, "motivo": "disparos diferentes da referência"}]
    assert r["falhas_medidas"] == 1
    assert len(r["amostras_ns"]) == 1  # a repetição com falha não entra na estatística


def test_excecao_conta_como_falha_so_com_o_tipo(registros, monkeypatch):
    def quebra(regs, regras):
        raise RuntimeError("detalhe interno")

    monkeypatch.setattr(mm, "_uma_execucao", quebra)
    r = mm.medir_combinacao("DM-01", 1000, 3, PLANO, registros)
    assert [f["motivo"] for f in r["falhas"]] == ["RuntimeError"] * 3
    assert r["falhas_medidas"] == 2 and r["estatisticas"] is None


def test_oraculo_diferente_quando_os_disparos_nao_batem_com_os_perfis():
    # Sem registros, o motor não dispara nada, mas os perfis de 1.000 registros pedem 3 por regra.
    r = mm.medir_combinacao("DM-01", 1000, 3, PLANO, [])
    assert r["oraculo_r1_r3_ok"] is False
    assert r["falhas"] == []  # determinístico: a falha aqui é só do oráculo


def test_so_a_avaliacao_fica_entre_os_dois_relogios(registros, monkeypatch):
    eventos = []
    monkeypatch.setattr(mm.gc, "collect", lambda: eventos.append("gc"))
    monkeypatch.setattr(mm.time, "perf_counter_ns", lambda: eventos.append("relogio") or len(eventos))
    avaliar_real = mm.motor.avaliar
    monkeypatch.setattr(mm.motor, "avaliar", lambda r, regras: eventos.append("avaliar") or avaliar_real(r, regras))

    regras = [d.para_motor() for d in base.definicoes_regras(3)]
    mm._uma_execucao(registros[:3], regras)
    assert eventos == ["gc", "relogio", "avaliar", "avaliar", "avaliar", "relogio"]
