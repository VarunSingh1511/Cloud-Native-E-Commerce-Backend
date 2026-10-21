"""Application settings loaded from environment variables."""

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed settings read from environment variables (or a local .env file).

    Field names map to environment variables case-insensitively, so
    `database_url` is read from `DATABASE_URL`.
    """

    # extra="ignore": .env is shared with Docker Compose, which reads its own
    # variables from it (e.g. POSTGRES_PASSWORD). Without this, those unknown
    # keys would stop the app from starting.
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

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
    # Azure Blob Storage for product images, e.g. https://<account>.blob.core.windows.net
    # Not a secret: access uses an Azure identity, never an account key. When it is
    # unset, image upload answers 503 and everything else works normally.
    azure_storage_account_url: str | None = None
    azure_storage_container: str = "product-images"
    # Azure Application Insights. When unset (tests, local runs), no telemetry is
    # sent. Not a secret: key authentication is disabled, so sending also needs
    # the app's Azure identity.
    applicationinsights_connection_string: str | None = None


# One shared instance; the app fails at startup if a required setting is missing.
settings = Settings()
