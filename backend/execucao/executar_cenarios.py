"""Execução formal dos 23 casos da aba 'Cenários de regras' (RA-01 a FM-17).

Uso: DATABASE_URL=<url do limen_execucao> python -m execucao.executar_cenarios

Usuário: o da execução (criado por execucao.preparar), campanha dos cenários.
Antes de tudo: conferir_regras para esse usuário; com diferença, sai com 2
sem gravar métrica nenhuma.

Duas camadas por caso:
- Aplicação (o que o sistema entrega): cada caso num POST próprio de
  /campanhas/{id}/metricas, num dia próprio (01/11/2026 + n). Válido: 201 e
  1 inserido → "Aceito"; inválido: 400 e nada gravado naquele dia → "Rejeitado".
  Depois, um POST /avaliacoes da campanha e GET /alertas: regra com alerta
  gravado no dia → "Sim".
- Motor: avaliar() com as regras ativas do banco (para_motor). É a única
  camada que separa "Não" de "N/A", porque o alerta só existe quando dispara.

Observado registrado (colunas O a R da planilha): registro pela API; cada regra
"Sim" se houver alerta gravado; senão, o resultado do motor ("Não" ou "N/A").
Se o motor disse "Sim" e não há alerta, o observado é "Não" (alerta omitido) e
o caso fica incoerente. Indevidos e omitidos pela fórmula das colunas T e U,
nas duas camadas. Veredito: correto (fórmula S) e coerente entre as camadas.

Saída: 0 todos corretos · 1 algum divergiu · 2 regras diferentes · 3 · 4 · 5.
Evidências: docs/evidencias/AAAA-MM-DD_execucao_cenarios.txt e .json
"""

from __future__ import annotations

import json
from datetime import date, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select

from .comum import (
    EMAIL_EXECUCAO,
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
from .preparar import NOME_CAMPANHA_CENARIOS

DIA_INICIAL = date(2026, 11, 1)
LOTE = "tabela-v1.0"
CODIGOS = ("R1", "R2", "R3")
# Máximo aceito por GET /alertas (le=5000 em app/api/rotas/alertas.py).
LIMITE_ALERTAS = 5000


def _get(cliente, caminho: str, params: dict | None = None):
    """GET que exige 200; se não vier, para sem mostrar o corpo da resposta."""
    resposta = cliente.get(caminho, params=params)
    if resposta.status_code != 200:
        raise Parada(SAIDA_AMBIENTE, f"GET {caminho} devolveu {resposta.status_code} (corpo não mostrado).")
    return resposta.json()


def _rotulo(resultado) -> str:
    from app.motor import Resultado

    return {Resultado.DISPARA: "Sim", Resultado.NAO_DISPARA: "Não", Resultado.NAO_AVALIAVEL: "N/A"}[resultado]


def _corpo(registro, dia: date) -> dict:
    texto = lambda v: None if v is None else str(v)  # noqa: E731 (Decimal vai como texto)
    return {
        "lote": LOTE,
        "registros": [{
            "data": dia.isoformat(),
            "impressoes": registro.impressoes,
            "cliques": registro.cliques,
            "custo": texto(registro.custo),
            "conversoes": texto(registro.conversoes),
        }],
    }


def _indevidos_omitidos(esperado: dict, observado: dict) -> tuple[int, int]:
    """Mesma conta das colunas T e U da planilha."""
    indevidos = sum(1 for c in CODIGOS if esperado[c] != "Sim" and observado[c] == "Sim")
    omitidos = sum(1 for c in CODIGOS if esperado[c] == "Sim" and observado[c] != "Sim")
    return indevidos, omitidos


def _localizar(sessao) -> tuple[int, int]:
    from app.modelos import Campanha, ContaGoogleAds, Usuario

    usuarios = list(sessao.scalars(select(Usuario.id).where(Usuario.email == EMAIL_EXECUCAO)))
    if len(usuarios) != 1:
        raise Parada(SAIDA_AMBIENTE, "Usuário da execução ausente: rode execucao.preparar antes.")
    campanhas = list(sessao.scalars(
        select(Campanha.id).join(Campanha.conta)
        .where(ContaGoogleAds.usuario_id == usuarios[0], Campanha.nome == NOME_CAMPANHA_CENARIOS)
    ))
    if len(campanhas) != 1:
        raise Parada(SAIDA_AMBIENTE, "Campanha dos cenários ausente ou repetida.")
    return usuarios[0], campanhas[0]


def principal() -> int:
    url_execucao()
    rel = Relatorio("execucao_cenarios.txt")
    rel_json = Relatorio("execucao_cenarios.json")
    for linha in cabecalho("execucao/executar_cenarios.py", "Execução formal — cenários de regras"):
        rel.add(linha)
    conferir_aplicacao_usa_execucao()

    from app.api.deps import obter_usuario_atual
    from app.db import SessaoLocal
    from app.main import criar_app
    from app.motor import avaliar
    from app.servicos.regras import listar_regras, para_motor
    from tests.tabela_congelada import carregar_cenarios

    with SessaoLocal() as sessao:
        conferir_banco_conectado(sessao)
        usuario_id, campanha_id = _localizar(sessao)

    # 1. Trava: R1 a R3 do banco iguais à planilha
    linhas, diferencas = conferir_usuario(usuario_id)
    rel.add("Conferência de R1 a R3 (antes de gravar qualquer métrica):")
    for linha in linhas:
        rel.add(linha)
    if diferencas:
        rel.add("PAROU: regras diferentes da planilha; nenhum caso executado.")
        rel_json.add(json.dumps({"parou": "regras_diferentes", "diferencas": diferencas}, ensure_ascii=False, indent=2))
        gravar_juntos(rel, rel_json)
        print("\n".join(rel.linhas))
        return SAIDA_REGRAS_DIFERENTES
    rel.add("")

    cenarios = carregar_cenarios()
    if len(cenarios) != 23:
        raise Parada(SAIDA_AMBIENTE, f"A planilha tem {len(cenarios)} casos, e não 23.")

    app = criar_app()
    app.dependency_overrides[obter_usuario_atual] = lambda: usuario_id
    with TestClient(app) as cliente:
        # 2. Pré-condição: campanha sem métricas e usuário sem avaliações
        if _get(cliente, f"/campanhas/{campanha_id}/metricas") != []:
            raise Parada(SAIDA_AMBIENTE, "A campanha dos cenários já tem métricas: execução não é do zero.")
        if _get(cliente, "/avaliacoes", {"limite": 1}) != []:
            raise Parada(SAIDA_AMBIENTE, "O usuário da execução já tem avaliações.")

        # 3. Ingestão, um POST por caso
        registro_obs: dict[str, str] = {}
        ingestao: dict[str, str] = {}
        for n, c in enumerate(cenarios):
            dia = DIA_INICIAL + timedelta(days=n)
            r = cliente.post(f"/campanhas/{campanha_id}/metricas", json=_corpo(c.registro, dia))
            gravado = _get(
                cliente, f"/campanhas/{campanha_id}/metricas", {"inicio": dia.isoformat(), "fim": dia.isoformat()}
            )
            if r.status_code == 201 and r.json()["inseridos"] == 1 and len(gravado) == 1:
                registro_obs[c.id] = "Aceito"
            elif r.status_code == 400 and gravado == []:
                registro_obs[c.id] = "Rejeitado"
            else:
                registro_obs[c.id] = f"inesperado ({r.status_code}, {len(gravado)} gravado)"
            ingestao[c.id] = f"{r.status_code} {r.json().get('tipo', '') if r.status_code != 201 else ''}".strip()

        # 4. Avaliação e alertas
        r = cliente.post("/avaliacoes", json={"campanha_id": campanha_id})
        if r.status_code != 201:
            raise Parada(SAIDA_AMBIENTE, f"POST /avaliacoes devolveu {r.status_code}.")
        avaliacao = r.json()
        alertas = _get(cliente, "/alertas", {"campanha_id": campanha_id, "limite": LIMITE_ALERTAS})
    if len(alertas) >= LIMITE_ALERTAS:
        raise Parada(SAIDA_AMBIENTE, f"GET /alertas chegou ao limite de {LIMITE_ALERTAS}: lista pode estar cortada.")
    emitidos: dict[str, set[str]] = {}
    for a in alertas:
        emitidos.setdefault(a["data"], set()).add(a["regra_codigo"])

    # 5. Camada do motor, com as regras ativas do banco
    with SessaoLocal() as sessao:
        regras_motor = [para_motor(r) for r in listar_regras(sessao, usuario_id, apenas_ativas=True)]

    casos = []
    for n, c in enumerate(cenarios):
        dia = (DIA_INICIAL + timedelta(days=n)).isoformat()
        esperado = {"registro": "Aceito" if c.aceito_esperado else "Rejeitado",
                    **{k: _rotulo(v) for k, v in c.esperados.items()}}
        res = avaliar(c.registro, regras_motor)
        motor = {"registro": "Aceito" if res.aceito else "Rejeitado",
                 **{k: _rotulo(res.regras[k].resultado) for k in CODIGOS}}
        no_dia = emitidos.get(dia, set())
        observado = {"registro": registro_obs[c.id],
                     **{k: "Sim" if k in no_dia else (motor[k] if motor[k] != "Sim" else "Não") for k in CODIGOS}}
        correto = all(observado[k] == esperado[k] for k in ("registro", *CODIGOS))  # fórmula S
        coerente = motor["registro"] == observado["registro"] and all(
            (motor[k] == "Sim") == (k in no_dia) for k in CODIGOS)
        ind_app, omi_app = _indevidos_omitidos(esperado, observado)
        ind_mot, omi_mot = _indevidos_omitidos(esperado, motor)
        casos.append({"id": c.id, "descricao": c.descricao, "dia": dia, "ingestao": ingestao[c.id],
                      "esperado": esperado, "observado": observado, "motor": motor,
                      "correto": correto, "coerente": coerente,
                      "indevidos": ind_app, "omitidos": omi_app,
                      "indevidos_motor": ind_mot, "omitidos_motor": omi_mot})

    # 6. Relatório
    aceitos = sum(1 for c in casos if c["observado"]["registro"] == "Aceito")
    rel.add(f"Avaliação id {avaliacao['id']}: {avaliacao['registros_avaliados']} avaliados, "
            f"{avaliacao['registros_rejeitados']} rejeitados, {avaliacao['alertas_gerados']} alertas, "
            f"motor {avaliacao['duracao_motor_ms']} ms (ingestão aceitou {aceitos})")
    rel.add("")
    rel.add("Caso   | Dia        | Ingestão | Registro esp/obs     | R1 esp/obs | R2 esp/obs | R3 esp/obs | Motor R1 R2 R3 | Correto | Coerente | Ind | Omi")
    for c in casos:
        e, o, m = c["esperado"], c["observado"], c["motor"]
        rel.add(f"{c['id']:<6} | {c['dia']} | {c['ingestao']:<8} | {e['registro']:<9}/{o['registro']:<10} | "
                + " | ".join(f"{e[k]:<3}/{o[k]:<6}" for k in CODIGOS)
                + f" | {m['R1']:<4} {m['R2']:<4} {m['R3']:<4} | {'Sim' if c['correto'] else 'NÃO':<7} | "
                f"{'Sim' if c['coerente'] else 'NÃO':<8} | {c['indevidos']:>3} | {c['omitidos']:>3}")
    corretos = sum(c["correto"] and c["coerente"] for c in casos)
    total = {k: sum(c[k] for c in casos) for k in ("indevidos", "omitidos", "indevidos_motor", "omitidos_motor")}
    rel.add("")
    rel.add(f"Casos executados: {len(casos)}")
    rel.add(f"Casos corretos (e coerentes entre as camadas): {corretos} de {len(casos)}")
    rel.add(f"Alertas indevidos: {total['indevidos']} (aplicação) · {total['indevidos_motor']} (motor)")
    rel.add(f"Alertas omitidos: {total['omitidos']} (aplicação) · {total['omitidos_motor']} (motor)")
    if avaliacao["registros_avaliados"] != aceitos or avaliacao["registros_rejeitados"] != 0:
        rel.add("ATENÇÃO: a avaliação não avaliou exatamente os registros aceitos.")
        corretos = -1

    rel_json.add(json.dumps({"avaliacao": avaliacao, "casos": casos, "totais": total,
                             "corretos": corretos, "executados": len(casos)}, ensure_ascii=False, indent=2))
    gravar_juntos(rel, rel_json)
    print("\n".join(rel.linhas))
    return SAIDA_OK if corretos == len(casos) else SAIDA_DIVERGENCIA


if __name__ == "__main__":
    rodar(principal)
