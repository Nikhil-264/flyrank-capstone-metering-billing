from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str
    STRIPE_SECRET_KEY: str
    STRIPE_WEBHOOK_SECRET: str
    ENV: str = "local"
    LOG_LEVEL: str = "info"

    # Background scheduler (APScheduler). Disabled automatically in the test
    # suite; enabled in docker-compose so the nightly reconciliation job runs.
    ENABLE_SCHEDULER: bool = True

    # Optional: pin the Stripe Price ID for the Pro plan so /checkout does not
    # have to list Products/Prices on every call. Leave blank to auto-discover.
    STRIPE_PRO_PRICE_ID: str | None = None

    # Allow loading from a .env file if available
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
