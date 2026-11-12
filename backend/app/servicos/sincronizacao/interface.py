"""Interface (porta) para a API do Google Ads.

Decisão: a interface devolve objetos do projeto (CampanhaGoogle), não objetos
da biblioteca google-ads. Assim o sincronizador e os testes de dublê não
dependem da biblioteca e podem rodar sem ela instalada.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class CampanhaGoogle:
    """Dados mínimos de uma campanha vindos da API do Google Ads."""

    google_campaign_id: int
    nome: str
    # Valor já normalizado pelo cliente: ENABLED | PAUSED | REMOVED | UNKNOWN
    status: str
    orcamento_micros: int | None


class PortaGoogleAds(Protocol):
    def listar_campanhas(
        self,
        login_customer_id: str,
        customer_id: str,
        refresh_token: str,
    ) -> list[CampanhaGoogle]: ...
