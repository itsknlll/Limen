"""Modelo inicial: usuários, contas, campanhas, métricas, regras, avaliações e alertas.

Revision ID: 0001
Revises:
Create Date: 2026-11-12
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

AGORA = sa.text("now()")


def upgrade() -> None:
    op.create_table(
        "usuario",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("nome", sa.String(200)),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False, server_default=AGORA),
        sa.UniqueConstraint("email", name="uq_usuario_email"),
    )

    op.create_table(
        "conta_google_ads",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("usuario_id", sa.BigInteger(), nullable=False),
        sa.Column("customer_id", sa.String(10), nullable=False),
        sa.Column("login_customer_id", sa.String(10)),
        sa.Column("nome", sa.String(200)),
        sa.Column("refresh_token_cifrado", sa.Text()),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False, server_default=AGORA),
        sa.ForeignKeyConstraint(
            ["usuario_id"], ["usuario.id"], ondelete="CASCADE", name="fk_conta_usuario"
        ),
        sa.UniqueConstraint("usuario_id", "customer_id", name="uq_conta_usuario_customer"),
        sa.CheckConstraint("customer_id ~ '^[0-9]{10}$'", name="ck_conta_customer_id_formato"),
        sa.CheckConstraint(
            "login_customer_id IS NULL OR login_customer_id ~ '^[0-9]{10}$'",
            name="ck_conta_login_customer_id_formato",
        ),
    )

    op.create_table(
        "campanha",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("conta_id", sa.BigInteger(), nullable=False),
        sa.Column("google_campaign_id", sa.BigInteger(), nullable=False),
        sa.Column("nome", sa.String(255), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("orcamento_micros", sa.BigInteger()),
        sa.Column("sincronizada_em", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(
            ["conta_id"], ["conta_google_ads.id"], ondelete="CASCADE", name="fk_campanha_conta"
        ),
        sa.UniqueConstraint("conta_id", "google_campaign_id", name="uq_campanha_conta_google_id"),
        sa.CheckConstraint(
            "status IN ('ENABLED', 'PAUSED', 'REMOVED', 'UNKNOWN')", name="ck_campanha_status"
        ),
        sa.CheckConstraint(
            "orcamento_micros IS NULL OR orcamento_micros >= 0", name="ck_campanha_orcamento"
        ),
    )

    op.create_table(
        "metrica_diaria",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("campanha_id", sa.BigInteger(), nullable=False),
        sa.Column("data", sa.Date(), nullable=False),
        sa.Column("impressoes", sa.BigInteger()),
        sa.Column("cliques", sa.BigInteger()),
        sa.Column("custo", sa.Numeric(14, 2)),
        sa.Column("conversoes", sa.Numeric(18, 6)),
        sa.Column("origem", sa.String(20), nullable=False),
        sa.Column("lote", sa.String(100)),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False, server_default=AGORA),
        sa.ForeignKeyConstraint(
            ["campanha_id"], ["campanha.id"], ondelete="CASCADE", name="fk_metrica_campanha"
        ),
        sa.UniqueConstraint("campanha_id", "data", name="uq_metrica_campanha_data"),
        sa.CheckConstraint("impressoes IS NULL OR impressoes >= 0", name="ck_metrica_impressoes"),
        sa.CheckConstraint("cliques IS NULL OR cliques >= 0", name="ck_metrica_cliques"),
        sa.CheckConstraint("custo IS NULL OR custo >= 0", name="ck_metrica_custo"),
        sa.CheckConstraint(
            "conversoes IS NULL OR conversoes >= 0", name="ck_metrica_conversoes"
        ),
        sa.CheckConstraint(
            "impressoes IS NULL OR cliques IS NULL OR cliques <= impressoes",
            name="ck_metrica_cliques_ate_impressoes",
        ),
        sa.CheckConstraint("origem IN ('sintetica', 'google_ads')", name="ck_metrica_origem"),
    )

    op.create_table(
        "regra",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("usuario_id", sa.BigInteger(), nullable=False),
        sa.Column("codigo", sa.String(20), nullable=False),
        sa.Column("nome", sa.String(120), nullable=False),
        sa.Column("ativa", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("criada_em", sa.DateTime(timezone=True), nullable=False, server_default=AGORA),
        sa.Column(
            "atualizada_em", sa.DateTime(timezone=True), nullable=False, server_default=AGORA
        ),
        sa.ForeignKeyConstraint(
            ["usuario_id"], ["usuario.id"], ondelete="CASCADE", name="fk_regra_usuario"
        ),
        sa.UniqueConstraint("usuario_id", "codigo", name="uq_regra_usuario_codigo"),
    )

    op.create_table(
        "condicao",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("regra_id", sa.BigInteger(), nullable=False),
        sa.Column("ordem", sa.SmallInteger(), nullable=False),
        sa.Column("metrica", sa.String(20), nullable=False),
        sa.Column("operador", sa.String(2), nullable=False),
        sa.Column("limiar", sa.Numeric(18, 6), nullable=False),
        sa.ForeignKeyConstraint(
            ["regra_id"], ["regra.id"], ondelete="CASCADE", name="fk_condicao_regra"
        ),
        sa.UniqueConstraint("regra_id", "ordem", name="uq_condicao_regra_ordem"),
        sa.CheckConstraint(
            "metrica IN ('impressoes', 'cliques', 'custo', 'conversoes', 'ctr', 'cpc')",
            name="ck_condicao_metrica",
        ),
        sa.CheckConstraint(
            "operador IN ('<', '<=', '>', '>=', '==')", name="ck_condicao_operador"
        ),
        sa.CheckConstraint("limiar >= 0", name="ck_condicao_limiar"),
    )

    op.create_table(
        "avaliacao",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("usuario_id", sa.BigInteger(), nullable=False),
        sa.Column("iniciada_em", sa.DateTime(timezone=True), nullable=False, server_default=AGORA),
        sa.Column("concluida_em", sa.DateTime(timezone=True)),
        sa.Column("registros_avaliados", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("registros_rejeitados", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("alertas_gerados", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("alertas_ja_existentes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("duracao_motor_ms", sa.Numeric(12, 3)),
        sa.ForeignKeyConstraint(
            ["usuario_id"], ["usuario.id"], ondelete="CASCADE", name="fk_avaliacao_usuario"
        ),
    )

    op.create_table(
        "alerta",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("avaliacao_id", sa.BigInteger(), nullable=False),
        sa.Column("regra_id", sa.BigInteger(), nullable=False),
        sa.Column("metrica_diaria_id", sa.BigInteger(), nullable=False),
        sa.Column("valores_medidos", postgresql.JSONB(), nullable=False),
        sa.Column("condicoes", postgresql.JSONB(), nullable=False),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False, server_default=AGORA),
        sa.ForeignKeyConstraint(
            ["avaliacao_id"], ["avaliacao.id"], ondelete="CASCADE", name="fk_alerta_avaliacao"
        ),
        sa.ForeignKeyConstraint(
            ["regra_id"], ["regra.id"], ondelete="RESTRICT", name="fk_alerta_regra"
        ),
        sa.ForeignKeyConstraint(
            ["metrica_diaria_id"],
            ["metrica_diaria.id"],
            ondelete="CASCADE",
            name="fk_alerta_metrica",
        ),
        sa.UniqueConstraint("regra_id", "metrica_diaria_id", name="uq_alerta_regra_metrica"),
    )

    # Índices para as consultas mais frequentes do dashboard
    op.create_index("ix_metrica_diaria_data", "metrica_diaria", ["data"])
    op.create_index("ix_alerta_criado_em", "alerta", ["criado_em"])

    # CTR e CPC derivados, com a mesma política do motor:
    # razão com denominador ausente ou zero é NULL (indefinida), nunca zero.
    op.execute(
        """
        CREATE VIEW vw_metrica_diaria AS
        SELECT
            m.*,
            m.cliques::numeric * 100 / NULLIF(m.impressoes, 0) AS ctr,
            m.custo / NULLIF(m.cliques, 0)                    AS cpc
        FROM metrica_diaria m
        """
    )


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS vw_metrica_diaria")
    op.drop_index("ix_alerta_criado_em", table_name="alerta")
    op.drop_index("ix_metrica_diaria_data", table_name="metrica_diaria")
    for tabela in (
        "alerta",
        "avaliacao",
        "condicao",
        "regra",
        "metrica_diaria",
        "campanha",
        "conta_google_ads",
        "usuario",
    ):
        op.drop_table(tabela)
