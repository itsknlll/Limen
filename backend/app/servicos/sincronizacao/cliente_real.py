"""Implementação real da PortaGoogleAds usando a biblioteca google-ads.

A biblioteca é importada dentro do método para que testes com dublê rodem
sem a biblioteca instalada (import lazy).

Decisão: usar google-ads==35.1.0 (padrão v26, developer_token opcional —
descontinuado em 09/09/2026, não enviado quando ausente). Alternativa
descartada: httpx REST direto — funcionaria, mas exigiria gerenciar o ciclo
de vida do access_token manualmente; a biblioteca faz isso automaticamente.
"""

from __future__ import annotations

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
        resposta = ga_service.search(customer_id=customer_id, query=_GAQL)

        campanhas: list[CampanhaGoogle] = []
        for row in resposta:
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
        return campanhas
