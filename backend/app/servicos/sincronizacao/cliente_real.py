"""Implementação real da PortaGoogleAds usando a biblioteca google-ads.

GoogleAdsClient é importado dentro do método (import lazy) para que testes
com dublê rodem sem a biblioteca instalada. grpc e google.auth.exceptions
são importados no topo: são dependências leves disponíveis junto com a lib.

Decisão: usar google-ads==35.1.0 (padrão v26, developer_token opcional —
descontinuado em 09/09/2026, não enviado quando ausente). Alternativa
descartada: httpx REST direto — funcionaria, mas exigiria gerenciar o ciclo
de vida do access_token manualmente; a biblioteca faz isso automaticamente.
"""

from __future__ import annotations

import grpc
from google.auth.exceptions import RefreshError, TransportError

from ..erros import (
    ApiIndisponivel,
    CotaExcedida,
    ErroGoogleAds,
    TokenExpirado,
    TokenRevogado,
)
from .interface import CampanhaGoogle

_STATUSES_VALIDOS = {"ENABLED", "PAUSED", "REMOVED"}

_GAQL = """
    SELECT
        campaign.id,
        campaign.name,
        campaign.status,
        campaign_budget.amount_micros,
        campaign_budget.resource_name
    FROM campaign
"""


def _orcamento(amount_micros: int, resource_name: str) -> int | None:
    """None quando não há orçamento vinculado; 0 é orçamento zero válido (ausente ≠ zero)."""
    return amount_micros if resource_name else None


def _extrair_codigo_falha(ex: object) -> tuple[str | None, str | None]:
    """Extrai (codigo, request_id) de uma GoogleAdsException defensivamente.

    codigo: "campo=VALOR" do primeiro erro do failure (ex.: "quota_error=RESOURCE_EXHAUSTED"),
            ou nome gRPC como fallback, ou None se tudo falhar.
    """
    try:
        grpc_nome: str | None = ex.error.code().name  # type: ignore[attr-defined]
        request_id: str | None = ex.request_id or None  # type: ignore[attr-defined]
        try:
            ec = ex.failure.errors[0].error_code  # type: ignore[attr-defined]
            for campo in type(ec).meta.fields:
                valor = getattr(ec, campo)
                if valor:
                    nome = valor.name if hasattr(valor, "name") else str(valor)
                    return f"{campo}={nome}", request_id
        except Exception:  # noqa: BLE001 — extração defensiva; qualquer falha usa fallback
            pass
        return grpc_nome, request_id
    except Exception:  # noqa: BLE001
        return None, None


def _classificar_status_grpc(
    code: grpc.StatusCode | None,
    detalhes: str,
    codigo: str | None,
    request_id: str | None,
    causa: Exception,
) -> ErroGoogleAds:
    """Converte um status gRPC em exceção do projeto.

    invalid_grant é verificado nos detalhes ANTES do código gRPC: pode chegar
    disfarçado como UNAVAILABLE, UNAUTHENTICATED ou qualquer outro status.
    """
    if "invalid_grant" in detalhes:
        return TokenRevogado("Refresh token inválido (invalid_grant via gRPC).")
    if code == grpc.StatusCode.RESOURCE_EXHAUSTED:
        return CotaExcedida("Cota excedida.", codigo=codigo, request_id=request_id)
    if code in (grpc.StatusCode.UNAVAILABLE, grpc.StatusCode.DEADLINE_EXCEEDED):
        return ApiIndisponivel("API indisponível.", codigo=codigo, request_id=request_id)
    return ErroGoogleAds(str(causa), codigo=codigo, request_id=request_id)


class ClienteRealGoogleAds:
    def __init__(self, client_id: str, client_secret: str) -> None:
        self._client_id = client_id
        self._client_secret = client_secret

    def listar_campanhas(
        self,
        login_customer_id: str,
        customer_id: str,
        refresh_token: str,
    ) -> list[CampanhaGoogle]:
        from google.ads.googleads.client import GoogleAdsClient  # import lazy
        from google.ads.googleads.errors import GoogleAdsException  # import lazy

        cliente = GoogleAdsClient.load_from_dict(
            {
                "use_proto_plus": True,
                "client_id": self._client_id,
                "client_secret": self._client_secret,
                "refresh_token": refresh_token,
                "login_customer_id": login_customer_id,
            }
        )

        ga_service = cliente.get_service("GoogleAdsService")

        campanhas: list[CampanhaGoogle] = []
        try:
            resposta = ga_service.search(customer_id=customer_id, query=_GAQL)
            for row in resposta:  # o erro pode surgir durante a iteração de streaming
                status_raw = row.campaign.status.name
                status = status_raw if status_raw in _STATUSES_VALIDOS else "UNKNOWN"
                orcamento = _orcamento(
                    row.campaign_budget.amount_micros,
                    row.campaign_budget.resource_name,
                )
                campanhas.append(
                    CampanhaGoogle(
                        google_campaign_id=row.campaign.id,
                        nome=row.campaign.name,
                        status=status,
                        orcamento_micros=orcamento,
                    )
                )
        except GoogleAdsException as ex:
            codigo, request_id = _extrair_codigo_falha(ex)
            try:
                code: grpc.StatusCode | None = ex.error.code()
            except Exception:  # noqa: BLE001
                code = None
            raise _classificar_status_grpc(code, str(ex), codigo, request_id, ex) from ex
        except grpc.RpcError as ex:
            try:
                code = ex.code()
                detalhes = ex.details() or str(ex)
                codigo = code.name
            except Exception:  # noqa: BLE001
                code = None
                detalhes = str(ex)
                codigo = None
            raise _classificar_status_grpc(code, detalhes, codigo, None, ex) from ex
        except RefreshError as ex:
            if ex.retryable:
                raise TokenExpirado("Falha temporária ao renovar o token.") from ex
            raise TokenRevogado("Refresh token inválido ou revogado.") from ex
        except TransportError as ex:
            raise ApiIndisponivel("Erro de transporte.") from ex

        return campanhas
