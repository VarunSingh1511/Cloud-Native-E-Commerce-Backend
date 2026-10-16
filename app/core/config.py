"""Application settings loaded from environment variables."""

from pydantic import Field, SecretStr
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
    # Signs JWTs. SecretStr hides the value when printed or logged ('**********').
    # At least 32 characters: short HMAC keys can be brute-forced offline from a
    # single captured token, which would let an attacker forge admin tokens.
    secret_key: SecretStr = Field(min_length=32)
    # How long a login token stays valid. Short-lived tokens limit the damage if
    # one is stolen, since this project has no logout/revocation.
    access_token_expire_minutes: int = Field(default=30, gt=0)


# One shared instance; the app fails at startup if a required setting is missing.
settings = Settings()
