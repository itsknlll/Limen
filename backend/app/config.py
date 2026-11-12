"""Configuração lida de variáveis de ambiente ou do arquivo backend/.env."""

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


configuracoes = Configuracoes()
