"""Sincronização de campanhas entre a API do Google Ads e o banco local.

Decisão de idempotência: usa INSERT ... ON CONFLICT DO UPDATE com a constraint
uq_campanha_conta_google_id — rodar duas vezes atualiza sem duplicar.
Decisão de status: normaliza valores desconhecidos para UNKNOWN antes de
gravar (defesa em profundidade contra futuros valores da API).
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from ..cifra import decifrar
from ..erros import TokenGoogleAusente
from ...modelos import STATUS_CAMPANHA, Campanha, ContaGoogleAds, Usuario
from .interface import PortaGoogleAds

_STATUSES_VALIDOS = set(STATUS_CAMPANHA)


def sincronizar(
    usuario: Usuario,
    customer_id: str,
    login_customer_id: str,
    sessao: Session,
    porta: PortaGoogleAds,
) -> int:
    """Sincroniza as campanhas do Google Ads no banco. Retorna o total sincronizado."""
    if not usuario.refresh_token_cifrado:
        raise TokenGoogleAusente("Token Google Ads ausente; faça login com o Google para autorizar.")

    refresh_token = decifrar(usuario.refresh_token_cifrado)

    # Cria ou reaproveita a ContaGoogleAds para esse customer_id
    conta = sessao.scalar(
        select(ContaGoogleAds).where(
            ContaGoogleAds.usuario_id == usuario.id,
            ContaGoogleAds.customer_id == customer_id,
        )
    )
    if conta is None:
        conta = ContaGoogleAds(
            usuario_id=usuario.id,
            customer_id=customer_id,
            login_customer_id=login_customer_id,
        )
        sessao.add(conta)
        sessao.flush()  # garante conta.id antes do upsert

    campanhas_google = porta.listar_campanhas(
        login_customer_id=login_customer_id,
        customer_id=customer_id,
        refresh_token=refresh_token,
    )

    agora = datetime.now(timezone.utc)

    for cg in campanhas_google:
        # Normaliza status: valor fora do conjunto válido vira UNKNOWN
        status = cg.status if cg.status in _STATUSES_VALIDOS else "UNKNOWN"
        stmt = (
            pg_insert(Campanha)
            .values(
                conta_id=conta.id,
                google_campaign_id=cg.google_campaign_id,
                nome=cg.nome,
                status=status,
                orcamento_micros=cg.orcamento_micros,
                sincronizada_em=agora,
            )
            .on_conflict_do_update(
                constraint="uq_campanha_conta_google_id",
                set_={
                    "nome": cg.nome,
                    "status": status,
                    "orcamento_micros": cg.orcamento_micros,
                    "sincronizada_em": agora,
                },
            )
        )
        sessao.execute(stmt)

    sessao.commit()
    return len(campanhas_google)
