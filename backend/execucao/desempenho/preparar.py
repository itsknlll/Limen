"""Prepara o banco dos testes de desempenho e a base dos endpoints.

Uso, na pasta backend com o venv ativo (a URL vai no comando, não no .env):

    DATABASE_URL=<url do banco limen_desempenho> python -m execucao.desempenho.preparar

Passos:
1. Confere a DATABASE_URL (só limen_desempenho), o sha256 da planilha e que não
   há código fora do commit (senão para com 3, antes de criar o banco).
2. Cria o banco limen_desempenho. Se ele já existir, para: não apaga nada.
3. alembic upgrade head e confere que a versão gravada é a head.
4. Confere que a aplicação usa o mesmo banco (app.config e current_database()).
5. Base dos endpoints (aba Desempenho, linha 20: 10.000 registros e 10 regras):
   - usuário com o e-mail do /dev/login (o medir_endpoints entra por ele);
   - R1 a R3 por criar_regras_padrao e R4 a R10 de definicoes_regras(10), pelo
     RegraEntrada e por servico.criar_regra (o mesmo caminho do POST /regras);
   - conta e 10 campanhas ENABLED com IDs fictícios (900001 a 900010);
   - 1.000 dias por campanha do gerar_metricas (semente fixa), cada registro por
     validar_registro e gravado por adicionar_metricas_sinteticas, num commit só.
6. Conferências, todas contra um oráculo calculado sem o banco:
   - R1 a R3 iguais à aba "Regras e limiares" e R1 a R10 iguais a definicoes_regras(10);
   - as 10.000 linhas do banco iguais, uma a uma, às do gerador;
   - uma avaliação NÃO medida (executar_avaliacao com os padrões do POST /avaliacoes
     vazio): 10.000 avaliados, 0 rejeitados e alertas gerados = disparos do motor puro
     sobre os mesmos registros. Ela deixa o DE-04 medido em estado estável (todos os
     alertas já existem) e o DE-02 com alertas para listar.
Se algo falhar no meio, o banco fica incompleto: apague-o à mão e rode de novo
(o script nunca apaga nem reaproveita um banco existente).

Saída: 0 ok · 1 dados ou avaliação diferentes do oráculo · 2 regras diferentes ·
3 ambiente · 4 evidência sensível · 5 erro inesperado.
Evidência: docs/evidencias/AAAA-MM-DD_desempenho_preparar.txt
(gravada também quando para com 1 ou 2, para documentar a parada).
"""

from __future__ import annotations

from collections import Counter

from sqlalchemy import create_engine, func, select, text
from sqlalchemy.engine import URL
from sqlalchemy.exc import OperationalError

from app import motor

from ..comum import SAIDA_AMBIENTE, SAIDA_DIVERGENCIA, SAIDA_OK, SAIDA_REGRAS_DIFERENTES, Parada, Relatorio, rodar
from ..preparar import aplicar_migracoes
from . import base

CUSTOMER_ID_FICTICIO = "0000000001"  # diferente do 0000000000 da execução formal
LOTE = f"desempenho-s{base.SEMENTE}"
NOME_CAMPANHA = "Desempenho · campanha {n:02d}"
LIMITE_PADRAO_ALERTAS = 500  # padrão do GET /alertas (app/api/rotas/alertas.py)


def criar_banco(url: URL) -> None:
    # Conecta no banco de manutenção "postgres" só para o CREATE DATABASE.
    manutencao = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    try:
        with manutencao.connect() as conexao:
            existe = conexao.scalar(
                text("SELECT datname FROM pg_database WHERE datname = :nome"), {"nome": base.BANCO_DESEMPENHO}
            )
            if existe is not None:
                raise Parada(
                    SAIDA_AMBIENTE,
                    f"O banco {base.BANCO_DESEMPENHO} já existe. Não apago sozinho: confira e, "
                    "se for o caso, apague à mão antes de rodar de novo.",
                )
            # Nome fixo do código (constante), não vem de entrada.
            conexao.execute(text(f"CREATE DATABASE {base.BANCO_DESEMPENHO}"))
    except OperationalError:
        raise Parada(SAIDA_AMBIENTE, "Banco fora do ar: rode 'docker compose up -d' na raiz.") from None
    finally:
        manutencao.dispose()


def disparos_esperados() -> Counter[str]:
    """Oráculo sem banco: o motor puro sobre os mesmos 10.000 registros e as 10 regras."""
    regras = [d.para_motor() for d in base.definicoes_regras(base.REGRAS_ENDPOINTS)]
    contagem: Counter[str] = Counter()
    for registro in base.registros_motor(base.REGISTROS_ENDPOINTS):
        contagem.update(motor.avaliar(registro, regras).disparadas)
    return contagem


def criar_base(rel: Relatorio) -> int:
    base.conferir_aplicacao_usa_desempenho()
    from app.api.esquemas import RegraEntrada
    from app.api.rotas.dev import EMAIL_DEV
    from app.db import SessaoLocal
    from app.modelos import Alerta, Campanha, ContaGoogleAds, MetricaDiaria, Regra, Usuario
    from app.servicos import regras as servico_regras
    from app.servicos.avaliacao import executar_avaliacao
    from app.servicos.campanhas import adicionar_metricas_sinteticas
    from tests.tabela_congelada import carregar_regras

    with SessaoLocal() as sessao:
        base.conferir_banco_conectado(sessao)
        rel.add(f"Servidor do banco (SHOW server_version): {base.versao_servidor(sessao)}")
        if sessao.scalar(select(func.count(Usuario.id))) != 0:
            raise Parada(SAIDA_AMBIENTE, "O banco recém-criado já tem usuários.")

        # --- Usuário e regras -------------------------------------------------
        usuario = Usuario(email=EMAIL_DEV, nome="Desempenho (base dos endpoints)")
        sessao.add(usuario)
        sessao.commit()
        if servico_regras.criar_regras_padrao(sessao, usuario.id) != 3:
            raise Parada(SAIDA_AMBIENTE, "criar_regras_padrao não criou as 3 regras.")
        definicoes = base.definicoes_regras(base.REGRAS_ENDPOINTS)
        for definicao in definicoes[3:]:
            entrada = RegraEntrada.model_validate(definicao.corpo())
            servico_regras.criar_regra(
                sessao, usuario.id, entrada.codigo, entrada.nome, entrada.ativa, entrada.condicoes
            )
        sessao.expire_all()  # relê do banco (expire_on_commit=False em app/db.py)

        rel.add(f"Usuário da base: id {usuario.id} (o do /dev/login; e-mail não registrado aqui)")
        rel.add("")
        rel.add("Regras ativas (relidas do banco):")
        ativas = servico_regras.listar_regras(sessao, usuario.id, apenas_ativas=True)
        do_banco = {r.codigo: servico_regras.para_motor(r) for r in ativas}
        da_planilha = {r.id: r for r in carregar_regras()}
        diferencas = []
        if set(do_banco) != {d.codigo for d in definicoes}:
            diferencas.append(f"códigos ativos {sorted(do_banco)} diferentes de R1 a R{base.REGRAS_ENDPOINTS}")
        for definicao in definicoes:
            codigo, esperada = definicao.codigo, definicao.para_motor()
            atual = do_banco.get(codigo)
            ok = atual == esperada and (codigo not in da_planilha or atual == da_planilha[codigo])
            condicoes = " E ".join(f"{m} {o} {l}" for m, o, l in definicao.condicoes)
            origem = "planilha" if codigo in da_planilha else "definicoes_regras"
            rel.add(f"  {codigo:>3} {condicoes}  → {'igual' if ok else 'DIFERENTE'} ({origem})")
            if not ok:
                diferencas.append(f"{codigo} diferente do esperado")
        if diferencas:
            rel.add("")
            rel.add("PAROU: " + "; ".join(diferencas))
            return SAIDA_REGRAS_DIFERENTES

        # --- Conta, campanhas e métricas (um commit só) -------------------------
        conta = ContaGoogleAds(
            usuario_id=usuario.id,
            customer_id=CUSTOMER_ID_FICTICIO,
            login_customer_id=None,
            nome="Conta sintética do desempenho",
        )
        sessao.add(conta)
        sessao.flush()
        campanhas: dict[int, int] = {}  # google_campaign_id → id
        for n, gid in enumerate(base.ids_campanhas(base.CAMPANHAS_ENDPOINTS), start=1):
            campanha = Campanha(
                conta_id=conta.id,
                google_campaign_id=gid,
                nome=NOME_CAMPANHA.format(n=n),
                status="ENABLED",
                orcamento_micros=None,
                sincronizada_em=None,
            )
            sessao.add(campanha)
            sessao.flush()
            campanhas[gid] = campanha.id
        try:
            for gid, campanha_id in campanhas.items():
                gerados = base.metricas_da_campanha(gid)
                for m in gerados:
                    erros = motor.validar_registro(motor.RegistroMetricas(m.impressoes, m.cliques, m.custo, m.conversoes))
                    if erros:
                        raise Parada(SAIDA_DIVERGENCIA, f"Registro gerado inválido (campanha {gid}): {erros}")
                adicionar_metricas_sinteticas(sessao, usuario.id, campanha_id, LOTE, gerados)
            sessao.commit()
        except Exception:
            sessao.rollback()
            raise

        rel.add("")
        rel.add(f"Conta sintética: id {conta.id}, customer_id {CUSTOMER_ID_FICTICIO} (fictício)")
        rel.add(
            f"Campanhas: {len(campanhas)} ENABLED, google_campaign_id {min(campanhas)} a {max(campanhas)} "
            f"(fictícios), ids {min(campanhas.values())} a {max(campanhas.values())}"
        )

        # --- Conferência linha a linha: banco = gerador --------------------------
        campanhas_iguais = 0
        linhas_lidas = 0
        for gid, campanha_id in campanhas.items():
            linhas = [
                tuple(linha)
                for linha in sessao.execute(
                    select(
                        MetricaDiaria.data, MetricaDiaria.impressoes, MetricaDiaria.cliques,
                        MetricaDiaria.custo, MetricaDiaria.conversoes, MetricaDiaria.origem, MetricaDiaria.lote,
                    )
                    .where(MetricaDiaria.campanha_id == campanha_id)
                    .order_by(MetricaDiaria.data)
                ).all()
            ]
            esperado = [
                (m.data, m.impressoes, m.cliques, m.custo, m.conversoes, "sintetica", LOTE)
                for m in base.metricas_da_campanha(gid)
            ]
            linhas_lidas += len(linhas)
            # Decimal comparado por valor: NUMERIC 9.00 do banco == 9 do gerador.
            if linhas == esperado:
                campanhas_iguais += 1
        total = sessao.scalar(select(func.count(MetricaDiaria.id)))
        periodo = sessao.execute(select(func.min(MetricaDiaria.data), func.max(MetricaDiaria.data))).one()
        rel.add(
            f"Métricas: {total} no banco ({linhas_lidas} lidas por campanha); campanhas iguais ao gerador "
            f"linha a linha: {campanhas_iguais} de {len(campanhas)}; período {periodo[0]} a {periodo[1]}; "
            f"origem sintetica, lote {LOTE}"
        )
        rel.add(f"sha256 dos dados (base.sha256_dados({base.REGISTROS_ENDPOINTS})): "
                f"{base.sha256_dados(base.REGISTROS_ENDPOINTS)}")
        if total != base.REGISTROS_ENDPOINTS or campanhas_iguais != len(campanhas):
            rel.add("DIVERGÊNCIA: banco diferente do gerador.")
            return SAIDA_DIVERGENCIA

        # --- Avaliação não medida ----------------------------------------------
        esperados = disparos_esperados()
        avaliacao = executar_avaliacao(sessao, usuario.id)  # = POST /avaliacoes {}
        no_banco = dict(
            sessao.execute(
                select(Regra.codigo, func.count(Alerta.id))
                .join(Alerta, Alerta.regra_id == Regra.id)
                .where(Regra.usuario_id == usuario.id)
                .group_by(Regra.codigo)
            ).all()
        )
        rel.add("")
        rel.add("Avaliação NÃO medida (executar_avaliacao, padrões do POST /avaliacoes vazio):")
        rel.add(
            f"  id {avaliacao.id}: {avaliacao.registros_avaliados} avaliados, {avaliacao.registros_rejeitados} "
            f"rejeitados, {avaliacao.alertas_gerados} alertas gerados, {avaliacao.alertas_ja_existentes} já existentes"
        )
        rel.add(f"  Esperado pelo motor puro (sem banco): {sum(esperados.values())} disparos")
        for definicao in definicoes:
            c = definicao.codigo
            rel.add(f"    {c:>3}: motor {esperados.get(c, 0):>5} · alertas no banco {no_banco.get(c, 0):>5}")
        total_alertas = sum(no_banco.values())
        rel.add(
            f"  Alertas no banco: {total_alertas}. O DE-02 (GET /alertas, limite padrão {LIMITE_PADRAO_ALERTAS}) "
            f"devolve {min(LIMITE_PADRAO_ALERTAS, total_alertas)} de {total_alertas}."
        )
        ok = (
            avaliacao.registros_avaliados == base.REGISTROS_ENDPOINTS
            and avaliacao.registros_rejeitados == 0
            and avaliacao.alertas_gerados == sum(esperados.values()) == total_alertas
            and avaliacao.alertas_ja_existentes == 0
            and all(no_banco.get(c, 0) == n for c, n in esperados.items())
            and set(no_banco) <= set(esperados)
        )
        if not ok:
            rel.add("DIVERGÊNCIA: avaliação diferente do motor puro.")
            return SAIDA_DIVERGENCIA
        return SAIDA_OK


def principal() -> int:
    url = base.url_desempenho()
    rel = Relatorio("desempenho_preparar.txt")
    for linha in base.cabecalho("execucao/desempenho/preparar.py", "Desempenho — preparação do banco"):
        rel.add(linha)

    criar_banco(url)
    rel.add(f"Banco {base.BANCO_DESEMPENHO} criado (não existia).")
    head = aplicar_migracoes(url)
    rel.add(f"Migrações aplicadas: alembic_version = {head} (head).")
    codigo = criar_base(rel)

    rel.add("")
    rel.add(f"Resultado: {'base pronta' if codigo == SAIDA_OK else 'NÃO pronta'} (código {codigo})")
    destino = base.gravar(rel)[0]  # grava também quando para, para documentar a parada
    print("\n".join(rel.linhas))
    print(f"Evidência gravada: docs/evidencias/{destino.name} (sem padrões sensíveis)")
    return codigo


if __name__ == "__main__":
    rodar(principal)
