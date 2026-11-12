"""Move refresh_token_cifrado para a tabela usuario.

O token autoriza o usuário (não a conta): ao fazer login OAuth não conhecemos ainda
o customer_id necessário para criar um registro em conta_google_ads. Fonte única
evita desincronização; a sincronização de campanhas lê o token pelo usuário dono da conta.

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-12
"""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("usuario", sa.Column("refresh_token_cifrado", sa.Text(), nullable=True))
    op.drop_column("conta_google_ads", "refresh_token_cifrado")


def downgrade() -> None:
    op.drop_column("usuario", "refresh_token_cifrado")
    op.add_column("conta_google_ads", sa.Column("refresh_token_cifrado", sa.Text(), nullable=True))
