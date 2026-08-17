from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AI Usage Monitor"
    environment: str = "development"
    database_url: str = "sqlite:///./ai_usage_monitor.db"
    prompt_monitoring_enabled: bool = True
    prompt_monitoring_disabled_assets: str = ""
    prompt_log_retention_days: int = 30

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)


settings = Settings()

# Prefer PostgreSQL when the environment explicitly supplies one, but allow a
# local SQLite database for test/dev runs where no Postgres service is running.
if not settings.database_url or settings.database_url.strip() == "":
    settings.database_url = "sqlite:///./ai_usage_monitor.db"
