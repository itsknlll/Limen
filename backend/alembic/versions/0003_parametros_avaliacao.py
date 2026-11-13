"""Guarda os parâmetros com que cada avaliação rodou.

Sem eles, o histórico não explica por que uma avaliação teve 60 registros e
outra 90 (a segunda incluiu as campanhas pausadas). Todas as colunas aceitam
NULL: nas avaliações anteriores a esta migração, NULL significa "não
registrado" — e não `false`, que seria falso para a execução real com
incluir_pausadas=true (mesma política do motor: ausente ≠ zero).

- campanha_id: FK com ON DELETE SET NULL, para o histórico sobreviver à
  remoção de uma campanha.
- CHECK inicio <= fim: repete no banco a validação do AvaliacaoEntrada
  (defesa em profundidade, como os demais CHECKs).

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-13
"""

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("avaliacao", sa.Column("incluir_pausadas", sa.Boolean(), nullable=True))
    op.add_column(
        "avaliacao",
        sa.Column(
            "campanha_id",
            sa.BigInteger(),
            sa.ForeignKey("campanha.id", ondelete="SET NULL", name="fk_avaliacao_campanha"),
            nullable=True,
        ),
    )
    op.add_column("avaliacao", sa.Column("inicio", sa.Date(), nullable=True))
    op.add_column("avaliacao", sa.Column("fim", sa.Date(), nullable=True))
    op.create_check_constraint(
        "ck_avaliacao_periodo",
        "avaliacao",
        "inicio IS NULL OR fim IS NULL OR inicio <= fim",
    )


def downgrade() -> None:
    op.drop_constraint("ck_avaliacao_periodo", "avaliacao", type_="check")
    op.drop_column("avaliacao", "fim")
    op.drop_column("avaliacao", "inicio")
    op.drop_column("avaliacao", "campanha_id")  # remove também a FK
    op.drop_column("avaliacao", "incluir_pausadas")
