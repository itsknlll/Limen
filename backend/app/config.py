"""Configuração lida de variáveis de ambiente ou do arquivo backend/.env."""

import json
import re
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

RAIZ_BACKEND = Path(__file__).resolve().parents[1]


class Configuracoes(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=RAIZ_BACKEND / ".env", env_file_encoding="utf-8", extra="ignore"
    )

    # "desenvolvimento" habilita rotas de apoio (ex.: /dev/login); use outro valor fora do seu computador.
    ambiente: str = "desenvolvimento"
    database_url: str = "postgresql+psycopg://limen:limen@localhost:5433/limen"
    database_url_teste: str | None = None
    # Assina o cookie de sessão. Troque por um valor aleatório no .env.
    segredo_sessao: str = "dev-inseguro-troque-no-env"

    # OAuth com Google: aponta para o arquivo client_secret.json (fora do repositório).
    # O segredo nunca é duplicado no .env — é lido em tempo de execução via credenciais_google.
    google_client_secret_file: Path | None = None
    google_redirect_uri: str = "http://localhost:8080/api/oauth/google/callback"

    # Cifragem de refresh tokens (Fernet/AES-128-CBC + HMAC-SHA256).
    # Ausente → falha com mensagem clara ao tentar cifrar/decifrar.
    # Gere com: python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    chave_cifragem: str | None = None

    # Conta Google Ads (não são segredos: IDs públicos). Obrigatórios para sincronizar.
    # customer_id: conta cliente (10 dígitos). login_customer_id: MCC (10 dígitos).
    google_customer_id: str | None = None
    google_login_customer_id: str | None = None

    @property
    def ids_google_ads(self) -> tuple[str, str]:
        """Retorna (customer_id, login_customer_id) validados (exatamente 10 dígitos cada).

        Levanta ValueError com instrução clara se ausente ou fora do formato —
        mesmo padrão da chave_cifragem.
        """
        for nome_var, valor in (
            ("GOOGLE_CUSTOMER_ID", self.google_customer_id),
            ("GOOGLE_LOGIN_CUSTOMER_ID", self.google_login_customer_id),
        ):
            if not valor:
                raise ValueError(
                    f"{nome_var} não configurada no .env — adicione {nome_var}=<10 dígitos>."
                )
            if not re.fullmatch(r"\d{10}", valor):
                raise ValueError(
                    f"{nome_var} inválida: deve ter exatamente 10 dígitos (recebido: '{valor}')."
                )
        return self.google_customer_id, self.google_login_customer_id  # type: ignore[return-value]

    @property
    def credenciais_google(self) -> tuple[str, str]:
        """Retorna (client_id, client_secret) lidos do arquivo JSON.

        Decisão: o segredo nunca passa pela conversa nem fica duplicado no .env.
        Configure GOOGLE_CLIENT_SECRET_FILE=/home/kauan/.config/limen/client_secret.json.
        """
        if self.google_client_secret_file is None:
            raise ValueError(
                "GOOGLE_CLIENT_SECRET_FILE não configurada no .env — "
                "aponte para o client_secret.json do projeto Google Cloud."
            )
        dados = json.loads(self.google_client_secret_file.read_text(encoding="utf-8"))
        # Suporta formato "web" (aplicativo da Web) e "installed" (desktop)
        app_data = dados.get("web") or dados.get("installed") or {}
        return app_data["client_id"], app_data["client_secret"]


configuracoes = Configuracoes()
