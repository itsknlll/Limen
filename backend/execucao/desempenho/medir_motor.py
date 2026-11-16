"""DM-01 a DM-09: tempo do motor isolado (aba Desempenho, linhas 10 a 18).

Uso, na pasta backend com o venv ativo (sem banco: não usa DATABASE_URL):

    python -m execucao.desempenho.medir_motor

Para cada combinação, na ordem da planilha (DM-01 a DM-09, registrada na evidência):
- FORA do cronômetro: montar os registros (base.registros_motor, uma vez por
  volume), converter as regras (DefinicaoRegra.para_motor), uma passada de
  referência não medida, gc.collect() antes de cada execução e, depois dela,
  a contagem dos disparos;
- DENTRO do cronômetro, só a linha do serviço (app/servicos/avaliacao.py:76):
      resultados = [motor.avaliar(registro, regras) for registro in registros]
  entre dois time.perf_counter_ns();
- aquecimentos e repetições lidos da planilha (B3 = 5, B4 = 30); os aquecimentos
  são descartados da estatística, mas ficam no .json.
O coletor de lixo fica ligado durante a medição, como no serviço; o gc.collect()
antes de cada execução evita cobrar de uma execução o lixo da anterior.

Falha (coluna I): exceção, ou disparos por regra diferentes da passada de
referência. A repetição com falha não entra na estatística.
Oráculo independente para R1 a R3: os perfis do gerador (cada dia "CTR baixo"
dispara só a R1, "CPC alto" só a R2, "custo sem conversão" só a R3, testado no
IN-02b com os limiares da planilha). Vale com 3, 10 ou 50 regras, porque cada
regra é avaliada separadamente.

Saída: 0 ok · 1 falha ou oráculo diferente · 3 ambiente · 4 evidência sensível · 5.
Evidências: docs/evidencias/AAAA-MM-DD_desempenho_motor.txt e .json
"""

from __future__ import annotations

import gc
import json
import resource
import time
from collections import Counter
from datetime import datetime
from decimal import Decimal

from app import motor
from app.servicos.sinteticas.gerador import Perfil

from ..comum import FUSO, SAIDA_DIVERGENCIA, SAIDA_OK, Relatorio, rodar
from . import base

PERFIL_DA_REGRA = {"R1": Perfil.CTR_BAIXO, "R2": Perfil.CPC_ALTO, "R3": Perfil.CUSTO_SEM_CONVERSAO}


def _uma_execucao(registros: list[motor.RegistroMetricas], regras: list[motor.Regra]) -> tuple[int, list]:
    gc.collect()  # fora do cronômetro
    inicio = time.perf_counter_ns()
    resultados = [motor.avaliar(registro, regras) for registro in registros]
    fim = time.perf_counter_ns()
    return fim - inicio, resultados


def _disparos(resultados: list) -> Counter[str]:
    contagem: Counter[str] = Counter()
    for resultado in resultados:
        contagem.update(resultado.disparadas)
    return contagem


def _perfis(volume: int) -> Counter[Perfil]:
    return Counter(
        m.perfil for gid in base.ids_campanhas(volume // base.DIAS_POR_CAMPANHA) for m in base.metricas_da_campanha(gid)
    )


def medir_combinacao(id_: str, volume: int, total_regras: int, plano: base.Plano, registros: list) -> dict:
    definicoes = base.definicoes_regras(total_regras)
    regras = [d.para_motor() for d in definicoes]  # fora do cronômetro

    # Passada de referência (não medida) e oráculo de R1 a R3 pelos perfis do gerador.
    referencia = _disparos([motor.avaliar(r, regras) for r in registros])
    perfis = _perfis(volume)
    oraculo_ok = all(referencia.get(c, 0) == perfis[p] for c, p in PERFIL_DA_REGRA.items())

    aquecimentos, amostras, falhas = [], [], []
    for n in range(plano.aquecimentos + plano.repeticoes):
        medida = n >= plano.aquecimentos
        try:
            ns, resultados = _uma_execucao(registros, regras)
        except Exception as erro:  # noqa: BLE001 — conta como falha; só o tipo é registrado
            falhas.append({"execucao": n + 1, "medida": medida, "motivo": type(erro).__name__})
            continue
        contagem = _disparos(resultados)  # fora do cronômetro
        resultados = None  # libera antes do próximo gc.collect()
        if contagem != referencia:
            falhas.append({"execucao": n + 1, "medida": medida, "motivo": "disparos diferentes da referência"})
            continue
        (amostras if medida else aquecimentos).append(ns)

    falhas_medidas = sum(1 for f in falhas if f["medida"])
    est = base.estatisticas(amostras) if len(amostras) >= 2 else None
    return {
        "id": id_,
        "registros": volume,
        "regras_ativas": total_regras,
        "sha256_dados": base.sha256_dados(volume),
        "oraculo_r1_r3_ok": oraculo_ok,
        "disparos_por_regra": {d.codigo: referencia.get(d.codigo, 0) for d in definicoes},
        "regras_sem_disparo": [d.codigo for d in definicoes if referencia.get(d.codigo, 0) == 0],
        "disparos_total": sum(referencia.values()),
        "aquecimentos_ns": aquecimentos,
        "amostras_ns": amostras,
        "falhas": falhas,
        "falhas_medidas": falhas_medidas,
        "estatisticas": None if est is None else {
            "n": est.n,
            "media_ms": str(est.media_ms),
            "mediana_ms": str(est.mediana_ms),
            "desvio_ms": str(est.desvio_ms),
            "minimo_ms": str(est.minimo_ms),
            "maximo_ms": str(est.maximo_ms),
            "p95_ms": str(est.p95_ms),
            "coef_variacao": None if est.coef_variacao is None else str(est.coef_variacao),
            "us_por_registro": str(est.media_ms * 1000 / volume),
        },
    }


def principal() -> int:
    plano = base.ler_plano()
    txt, js = Relatorio("desempenho_motor.txt"), Relatorio("desempenho_motor.json")
    for linha in base.cabecalho("execucao/desempenho/medir_motor.py", "Desempenho — motor isolado (DM)", usa_banco=False):
        txt.add(linha)

    amb = base.ambiente(None)
    relogio = time.get_clock_info("perf_counter")
    txt.add("Ambiente:")
    for chave, valor in amb.items():
        txt.add(f"  {chave}: {valor}")
    txt.add(f"  Relógio: perf_counter ({relogio.implementation}, resolução {relogio.resolution} s, "
            f"monotônico {relogio.monotonic})")
    txt.add(f"Plano (planilha): {plano.aquecimentos} aquecimentos descartados, {plano.repeticoes} repetições")
    txt.add("Medido: só `[motor.avaliar(r, regras) for r in registros]`; montar registros, converter regras, "
            "gc.collect() e contar disparos ficam fora.")
    txt.add("")

    cache: dict[int, list] = {}
    combinacoes, ordem = [], []
    for posicao, (id_, volume, total_regras) in enumerate(plano.motor, start=1):
        if volume not in cache:
            cache[volume] = base.registros_motor(volume)  # fora do cronômetro
        inicio = datetime.now(FUSO)
        resultado = medir_combinacao(id_, volume, total_regras, plano, cache[volume])
        fim = datetime.now(FUSO)
        ordem.append({"posicao": posicao, "id": id_, "inicio": inicio.isoformat(timespec="seconds"),
                      "fim": fim.isoformat(timespec="seconds")})
        combinacoes.append(resultado)
        print(f"{id_} concluída ({posicao} de {len(plano.motor)})")

    pico_mib = base.arredondar(Decimal(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss) / 1024, 1)

    txt.add("Ordem de execução:")
    for o in ordem:
        txt.add(f"  {o['posicao']}. {o['id']}  {o['inicio']} → {o['fim']}")
    txt.add(f"Pico de memória do processo (ru_maxrss): {pico_mib} MiB")
    txt.add("")
    txt.add("ID     Registros Regras  Média(ms) Mediana(ms) Desvio(ms)  p95(ms)   Mín(ms)   Máx(ms)  CV      µs/reg  Falhas")
    for c in combinacoes:
        e = c["estatisticas"]
        if e is None:
            txt.add(f"{c['id']}  sem amostras suficientes · falhas {c['falhas_medidas']}")
            continue
        cv = "—" if e["coef_variacao"] is None else str(base.arredondar(Decimal(e["coef_variacao"]), 4))
        txt.add(
            f"{c['id']}  {c['registros']:>9} {c['regras_ativas']:>6} "
            + " ".join(f"{base.arredondar(Decimal(e[k])):>10}" for k in
                       ("media_ms", "mediana_ms", "desvio_ms", "p95_ms", "minimo_ms", "maximo_ms"))
            + f"  {cv:>6}  {base.arredondar(Decimal(e['us_por_registro'])):>7}  {c['falhas_medidas']}"
        )
    txt.add("")
    txt.add("Oráculo de R1 a R3 (perfis do gerador): "
            + ", ".join(f"{c['id']} {'ok' if c['oraculo_r1_r3_ok'] else 'DIFERENTE'}" for c in combinacoes))
    txt.add("")
    txt.add("Disparos por regra (passada de referência; vazio = regra fora da combinação):")
    ids = [c["id"] for c in combinacoes]
    txt.add("Regra " + " ".join(f"{i:>9}" for i in ids))
    for d in base.definicoes_regras(max(c["regras_ativas"] for c in combinacoes)):
        celulas = [c["disparos_por_regra"].get(d.codigo) for c in combinacoes]
        txt.add(f"{d.codigo:>5} " + " ".join(f"{'' if v is None else v:>9}" for v in celulas))
    txt.add("Total " + " ".join(f"{c['disparos_total']:>9}" for c in combinacoes))
    txt.add("")
    txt.add("Regras que nunca disparam (mantidas de propósito: condições contraditórias nas faixas do gerador):")
    for c in combinacoes:
        txt.add(f"  {c['id']}: {', '.join(c['regras_sem_disparo']) or 'nenhuma'}")
    txt.add("")
    txt.add("Dados por volume (sha256 de base.sha256_dados):")
    for volume in sorted(cache):
        txt.add(f"  {volume:>6}: {base.sha256_dados(volume)}")

    algum_erro = any(c["falhas_medidas"] or c["falhas"] or not c["oraculo_r1_r3_ok"] for c in combinacoes)
    txt.add("")
    txt.add(f"Resultado: {'sem falhas' if not algum_erro else 'COM FALHAS ou oráculo diferente'}")

    js.add(json.dumps({
        "ambiente": amb,
        "resumo_ambiente_b5": base.resumo_ambiente(amb),
        "plano": {"aquecimentos": plano.aquecimentos, "repeticoes": plano.repeticoes},
        "ordem": ordem,
        "pico_memoria_mib": str(pico_mib),
        "combinacoes": combinacoes,
    }, ensure_ascii=False, indent=2))

    base.gravar(txt, js)
    print("\n".join(txt.linhas))
    return SAIDA_DIVERGENCIA if algum_erro else SAIDA_OK


if __name__ == "__main__":
    rodar(principal)
