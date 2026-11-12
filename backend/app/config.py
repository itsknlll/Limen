"""Configuração lida de variáveis de ambiente ou do arquivo backend/.env."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

RAIZ_BACKEND = Path(__file__).resolve().parents[1]


class Configuracoes(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=RAIZ_BACKEND / ".env", env_file_encoding="utf-8", extra="ignore"
    )

    database_url: str = "postgresql+psycopg://limen:limen@localhost:5433/limen"
    database_url_teste: str | None = None


configuracoes = Configuracoes()
