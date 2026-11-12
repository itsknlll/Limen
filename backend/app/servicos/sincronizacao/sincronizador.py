"""Sincronização de campanhas entre a API do Google Ads e o banco local.

Decisão de idempotência: usa INSERT ... ON CONFLICT DO UPDATE com a constraint
uq_campanha_conta_google_id — rodar duas vezes atualiza sem duplicar.
Decisão de status: normaliza valores desconhecidos para UNKNOWN antes de
gravar (defesa em profundidade contra futuros valores da API).
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Callable

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from ..cifra import decifrar
from ..erros import (
    ApiIndisponivel,
    CotaExcedida,
    ErroGoogleAds,
    TokenExpirado,
    TokenGoogleAusente,
    TokenRevogado,
)
from ...modelos import STATUS_CAMPANHA, Campanha, ContaGoogleAds, Usuario
from .interface import CampanhaGoogle, PortaGoogleAds

_logger = logging.getLogger(__name__)
_STATUSES_VALIDOS = set(STATUS_CAMPANHA)


def sincronizar(
    usuario: Usuario,
    customer_id: str,
    login_customer_id: str,
    sessao: Session,
    porta: PortaGoogleAds,
    tentativas_indisp: int = 3,
    espera: Callable[[int], None] = time.sleep,
) -> int:
    """Sincroniza as campanhas do Google Ads no banco. Retorna o total sincronizado.

    A porta é chamada ANTES de qualquer operação no banco: se falhar, nenhum
    dado parcial é persistido.

    Retries aninhados (pior caso: 2 × 4 = 8 chamadas à porta):
    - Externo (TokenExpirado): repete a chamada uma vez sem espera.
    - Interno (ApiIndisponivel): até tentativas_indisp=3 novas tentativas com
      espera crescente (1 s, 2 s, 4 s), totalizando 4 chamadas.
    TokenRevogado, CotaExcedida e ErroGoogleAds genérico saem imediatamente.
    """
    if not usuario.refresh_token_cifrado:
        raise TokenGoogleAusente("Token Google Ads ausente; faça login com o Google para autorizar.")

    refresh_token = decifrar(usuario.refresh_token_cifrado)

    # --- Chamada à porta ANTES de qualquer operação no banco ---
    try:
        campanhas_google = _listar_com_retry(
            porta, login_customer_id, customer_id, refresh_token,
            tentativas_indisp, espera,
        )
    except TokenRevogado as exc:
        _logger.warning(
            "IN-04 token_revogado: refresh inválido para usuário %d [codigo=%s]",
            usuario.id, exc.codigo,
        )
        usuario.refresh_token_cifrado = None
        sessao.commit()  # persiste somente a limpeza do token
        raise

    # --- Operações no banco (somente após retorno bem-sucedido da porta) ---
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


def _listar_com_retry(
    porta: PortaGoogleAds,
    login_customer_id: str,
    customer_id: str,
    refresh_token: str,
    tentativas_indisp: int,
    espera: Callable[[int], None],
) -> list[CampanhaGoogle]:
    """Aplica retries de TokenExpirado (externo) sobre o retry de ApiIndisponivel (interno).

    Pior caso: 2 × (1 + tentativas_indisp) chamadas à porta.
    CotaExcedida, TokenRevogado e ErroGoogleAds genérico propagam sem retry.
    """
    for i_token in range(2):
        try:
            return _listar_com_retry_indisponivel(
                porta, login_customer_id, customer_id, refresh_token,
                tentativas_indisp, espera,
            )
        except TokenExpirado:
            if i_token == 0:
                _logger.warning("IN-03 token_expirado: retentando após falha temporária")
            else:
                _logger.warning("IN-03 token_expirado: falhou após nova tentativa")
                raise
        except ApiIndisponivel:
            raise  # já logado em _listar_com_retry_indisponivel
        except CotaExcedida as exc:
            _logger.warning(
                "IN-06 cota_excedida: sincronização adiada [codigo=%s]", exc.codigo,
            )
            raise
        except ErroGoogleAds as exc:
            # Captura TokenRevogado e ErroGoogleAds base; TokenRevogado é logado
            # em sincronizar() (onde usuario.id está disponível).
            if not isinstance(exc, TokenRevogado):
                _logger.warning(
                    "erro_google_ads não transitório [codigo=%s]", exc.codigo,
                )
            raise

    raise RuntimeError("fluxo inesperado em _listar_com_retry")  # pragma: no cover


def _listar_com_retry_indisponivel(
    porta: PortaGoogleAds,
    login_customer_id: str,
    customer_id: str,
    refresh_token: str,
    tentativas_indisp: int,
    espera: Callable[[int], None],
) -> list[CampanhaGoogle]:
    """Chama a porta até (1 + tentativas_indisp) vezes para falhas transitórias de API."""
    total = 1 + tentativas_indisp
    for i in range(total):
        try:
            return porta.listar_campanhas(login_customer_id, customer_id, refresh_token)
        except ApiIndisponivel as exc:
            if i < tentativas_indisp:
                segundos = 2 ** i
                _logger.warning(
                    "IN-05 tentativa %d/%d falhou, aguardando %ds [codigo=%s]",
                    i + 1, total, segundos, exc.codigo,
                )
                espera(segundos)
            else:
                _logger.warning(
                    "IN-05 api_indisponivel: %d tentativas esgotadas [codigo=%s]",
                    total, exc.codigo,
                )
                raise

    raise RuntimeError("fluxo inesperado em _listar_com_retry_indisponivel")  # pragma: no cover
