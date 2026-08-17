from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AI Usage Monitor"
    environment: str = "development"
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/ai_usage_monitor"
    prompt_monitoring_enabled: bool = True
    prompt_monitoring_disabled_assets: str = ""
    prompt_log_retention_days: int = 30
    demo_mode: bool = True
    access_control_enabled: bool = False
    monitor_api_key: str = "demo-ai-monitor-key"

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)


settings = Settings()

# Prefer PostgreSQL for the AI monitor. If Postgres is not running, fall back to
# SQLite so the app can still be exercised locally without a database service.
if not settings.database_url or settings.database_url.strip() == "":
    settings.database_url = "postgresql+psycopg://postgres:postgres@localhost:5432/ai_usage_monitor"
