"""Application settings loaded from environment variables."""

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed settings read from environment variables (or a local .env file).

    Field names map to environment variables case-insensitively, so
    `database_url` is read from `DATABASE_URL`.
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    environment: str = "development"
    # No defaults: connection strings and secrets must come from the environment.
    database_url: str
    # SecretStr hides the value when printed or logged (shows '**********').
    secret_key: SecretStr


# One shared instance; the app fails at startup if a required setting is missing.
settings = Settings()
