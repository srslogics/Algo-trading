from decimal import Decimal
from typing import Literal
from urllib.parse import urlsplit

from pydantic import AliasChoices, Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="OPTIONLAB_", env_file=".env", extra="ignore", populate_by_name=True
    )
    database_url: str = Field(
        default="sqlite:///./optionlab.db",
        validation_alias=AliasChoices("OPTIONLAB_DATABASE_URL", "DATABASE_URL"),
    )
    environment: Literal["local", "render"] = "local"
    public_origin: str = Field(
        default="", validation_alias=AliasChoices("OPTIONLAB_PUBLIC_ORIGIN", "RENDER_EXTERNAL_URL")
    )
    session_hours: int = Field(default=8, ge=1, le=24)
    execution_mode: Literal["paper"] = "paper"  # No setting can enable live execution.
    data_source: Literal["DEMO", "KITE"] = "DEMO"
    demo_enabled: bool = True
    auth_required: bool = False
    api_token: SecretStr = SecretStr("")
    ai_provider: Literal["offline", "openai"] = "offline"
    openai_api_key: SecretStr = SecretStr("")
    openai_model: str = ""
    kite_api_key: SecretStr = SecretStr("")
    kite_access_token: SecretStr = SecretStr("")
    starting_cash: Decimal = Field(default=Decimal("500000"), gt=0, allow_inf_nan=False)
    max_trade_premium: Decimal = Field(default=Decimal("25000"), gt=0, allow_inf_nan=False)
    max_total_premium: Decimal = Field(default=Decimal("100000"), gt=0, allow_inf_nan=False)
    max_daily_loss: Decimal = Field(default=Decimal("10000"), gt=0, allow_inf_nan=False)
    max_positions: int = Field(default=5, ge=1, le=100)
    max_quote_age_seconds: int = Field(default=60, ge=1, le=300)
    proposal_ttl_seconds: int = Field(default=120, ge=1, le=600)
    paper_fee_per_order: Decimal = Field(default=Decimal("20"), ge=0, allow_inf_nan=False)
    risk_free_rate: float = Field(default=0.06, ge=0, le=0.3)

    @field_validator("database_url")
    @classmethod
    def normalize_database_url(cls, value):
        for prefix in ("postgres://", "postgresql://"):
            if value.startswith(prefix):
                return "postgresql+psycopg://" + value[len(prefix) :]
        return value

    @field_validator("public_origin")
    @classmethod
    def validate_origin(cls, value):
        if not value:
            return value
        parsed = urlsplit(value)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
            or parsed.path not in {"", "/"}
        ):
            raise ValueError(
                "Public origin must be an http(s) origin without a path or credentials"
            )
        return value.rstrip("/")

    @model_validator(mode="after")
    def validate_configuration(self):
        if self.environment == "render":
            if not self.auth_required:
                raise ValueError("Render deployments require authentication")
            if not self.database_url.startswith("postgresql+psycopg://"):
                raise ValueError("Render deployments require persistent PostgreSQL")
            if self.public_origin and not self.public_origin.startswith("https://"):
                raise ValueError("Render public origin must use HTTPS")
        if self.auth_required and len(self.api_token.get_secret_value()) < 32:
            raise ValueError("Authenticated mode requires an API token of at least 32 characters")
        if self.data_source == "KITE" and self.demo_enabled:
            raise ValueError("Disable demo when using KITE; use separate databases for each source")
        if self.ai_provider == "openai" and (
            not self.openai_model or not self.openai_api_key.get_secret_value()
        ):
            raise ValueError("OpenAI mode requires an explicit model and API key")
        return self
