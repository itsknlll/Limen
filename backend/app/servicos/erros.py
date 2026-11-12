"""Erros de negócio. A camada de API traduz cada um para um código HTTP."""


class NaoEncontrado(Exception):
    """Recurso inexistente ou de outro usuário (HTTP 404)."""


class ConflitoDados(Exception):
    """Operação conflita com dados existentes (HTTP 409)."""


class TokenGoogleAusente(Exception):
    """Usuário não autorizou acesso ao Google Ads (sem refresh_token_cifrado). HTTP 409."""


class ErroGoogleAds(Exception):
    """Base para falhas na comunicação com a API do Google Ads. HTTP 502/503."""

    def __init__(
        self,
        msg: str,
        codigo: str | None = None,
        request_id: str | None = None,
    ) -> None:
        super().__init__(msg)
        # Código detalhado da API quando disponível (ex.: "quota_error=RESOURCE_EXHAUSTED");
        # cai para o nome gRPC (ex.: "RESOURCE_EXHAUSTED") quando o detalhe não existir.
        self.codigo = codigo
        self.request_id = request_id  # request_id da GoogleAdsException, quando disponível


class TokenExpirado(ErroGoogleAds):
    """Falha temporária ao renovar o access token (retryable). HTTP 503."""


class TokenRevogado(ErroGoogleAds):
    """Refresh token revogado ou inválido (invalid_grant). HTTP 409."""


class ApiIndisponivel(ErroGoogleAds):
    """API indisponível ou timeout (UNAVAILABLE / DEADLINE_EXCEEDED). HTTP 503."""


class CotaExcedida(ErroGoogleAds):
    """Cota de uso excedida (RESOURCE_EXHAUSTED). HTTP 503 + Retry-After."""
