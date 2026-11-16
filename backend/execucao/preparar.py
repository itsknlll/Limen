"""Prepara o banco da execução formal e o usuário próprio.

Uso, na pasta backend com o venv ativo (a URL vai no comando, não no .env):

    DATABASE_URL=<url do banco limen_execucao> python -m execucao.preparar

Passos:
1. Confere a DATABASE_URL (só limen_execucao) e o sha256 da planilha.
2. Cria o banco limen_execucao. Se ele já existir, para: não apaga nada.
3. alembic upgrade head e confere que a versão gravada é a head.
4. Confere que a aplicação usa o mesmo banco (app.config e current_database()).
5. Cria o usuário da execução, R1 a R3 (criar_regras_padrao, os limiares da
   tabela) e uma conta e uma campanha sintéticas para os cenários RA/FM.
   O usuário do Google (IN-01) é criado depois, pelo login real.

Saída: 0 ok · 3 ambiente · 4 evidência sensível · 5 erro inesperado.
Evidência: docs/evidencias/AAAA-MM-DD_execucao_preparar.txt
"""

from __future__ import annotations

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.engine import URL
from sqlalchemy.exc import OperationalError

from .comum import (
    BANCO_EXECUCAO,
    EMAIL_EXECUCAO,
    RAIZ_BACKEND,
    SAIDA_AMBIENTE,
    SAIDA_OK,
    Parada,
    Relatorio,
    cabecalho,
    conferir_aplicacao_usa_execucao,
    conferir_banco_conectado,
    rodar,
    url_execucao,
)

# Conta e campanha só de estrutura, para receber as métricas dos cenários.
# IDs fictícios e declarados: não são da conta de teste do Google Ads.
CUSTOMER_ID_SINTETICO = "0000000000"
GOOGLE_CAMPAIGN_ID_SINTETICO = 1
NOME_CAMPANHA_CENARIOS = "Execução · cenários RA/FM"


def criar_banco(url: URL) -> None:
    # Conecta no banco de manutenção "postgres" só para o CREATE DATABASE.
    manutencao = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    try:
        with manutencao.connect() as conexao:
            existe = conexao.scalar(
                text("SELECT datname FROM pg_database WHERE datname = :nome"),
                {"nome": BANCO_EXECUCAO},
            )
            if existe is not None:
                raise Parada(
                    SAIDA_AMBIENTE,
                    f"O banco {BANCO_EXECUCAO} já existe. Não apago sozinho: confira e, "
                    "se for o caso, apague à mão antes de rodar de novo.",
                )
            # Nome fixo do código (constante), não vem de entrada.
            conexao.execute(text(f"CREATE DATABASE {BANCO_EXECUCAO}"))
    except OperationalError:
        raise Parada(SAIDA_AMBIENTE, "Banco fora do ar: rode 'docker compose up -d' na raiz.") from None
    finally:
        manutencao.dispose()


def aplicar_migracoes(url: URL) -> str:
    cfg = Config(str(RAIZ_BACKEND / "alembic.ini"))
    cfg.set_main_option("script_location", str(RAIZ_BACKEND / "alembic"))
    # "%" escapado por causa da interpolação do configparser do Alembic.
    cfg.set_main_option("sqlalchemy.url", url.render_as_string(hide_password=False).replace("%", "%%"))
    command.upgrade(cfg, "head")

    head = ScriptDirectory.from_config(cfg).get_current_head()
    engine = create_engine(url)
    try:
        with engine.connect() as conexao:
            gravada = conexao.scalar(text("SELECT version_num FROM alembic_version"))
    finally:
        engine.dispose()
    if gravada != head:
        raise Parada(SAIDA_AMBIENTE, f"Migração incompleta: banco em {gravada}, head é {head}.")
    return head


def criar_usuario_e_estrutura(rel: Relatorio) -> None:
    conferir_aplicacao_usa_execucao()
    from app.db import SessaoLocal
    from app.modelos import Campanha, ContaGoogleAds, Regra, Usuario
    from app.servicos.regras import criar_regras_padrao, listar_regras

    with SessaoLocal() as sessao:
        conferir_banco_conectado(sessao)
        if sessao.scalar(select(func.count(Usuario.id))) != 0:
            raise Parada(SAIDA_AMBIENTE, "O banco recém-criado já tem usuários.")

        usuario = Usuario(email=EMAIL_EXECUCAO, nome="Execução formal da tabela")
        sessao.add(usuario)
        sessao.commit()

        if criar_regras_padrao(sessao, usuario.id) != 3:
            raise Parada(SAIDA_AMBIENTE, "criar_regras_padrao não criou as 3 regras.")

        conta = ContaGoogleAds(
            usuario_id=usuario.id,
            customer_id=CUSTOMER_ID_SINTETICO,
            login_customer_id=None,
            nome="Conta sintética da execução",
        )
        sessao.add(conta)
        sessao.flush()
        campanha = Campanha(
            conta_id=conta.id,
            google_campaign_id=GOOGLE_CAMPAIGN_ID_SINTETICO,
            nome=NOME_CAMPANHA_CENARIOS,
            status="ENABLED",
            orcamento_micros=None,
            sincronizada_em=None,
        )
        sessao.add(campanha)
        sessao.commit()

        rel.add(f"Usuário da execução: id {usuario.id} (e-mail não registrado aqui)")
        rel.add(f"Conta sintética: id {conta.id}, customer_id {CUSTOMER_ID_SINTETICO} (fictício)")
        rel.add(
            f"Campanha dos cenários: id {campanha.id}, '{campanha.nome}', ENABLED, "
            f"google_campaign_id {GOOGLE_CAMPAIGN_ID_SINTETICO} (fictício), sem orçamento"
        )
        rel.add("")
        rel.add("Regras criadas por criar_regras_padrao (conferidas contra a planilha no próximo script):")
        for regra in listar_regras(sessao, usuario.id):
            condicoes = " E ".join(
                f"{c.metrica} {c.operador} {c.limiar}" for c in sorted(regra.condicoes, key=lambda c: c.ordem)
            )
            rel.add(f"  {regra.codigo} '{regra.nome}' ativa={regra.ativa}: {condicoes}")
        total_regras = sessao.scalar(select(func.count(Regra.id)))
        rel.add(f"Total de regras no banco: {total_regras}")


def principal() -> int:
    url = url_execucao()
    rel = Relatorio("execucao_preparar.txt")
    for linha in cabecalho("execucao/preparar.py", "Execução formal — preparação do banco"):
        rel.add(linha)

    criar_banco(url)
    rel.add(f"Banco {BANCO_EXECUCAO} criado (não existia).")
    head = aplicar_migracoes(url)
    rel.add(f"Migrações aplicadas: alembic_version = {head} (head).")
    rel.add("")
    criar_usuario_e_estrutura(rel)

    destino = rel.gravar()
    print("\n".join(rel.linhas))
    print(f"Evidência gravada: docs/evidencias/{destino.name} (sem padrões sensíveis)")
    return SAIDA_OK


if __name__ == "__main__":
    rodar(principal)
