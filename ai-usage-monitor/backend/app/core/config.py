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
    # Comma-separated list of allowed frontend origins for CORS. Defaults
    # cover local dev plus the deployed Vercel frontend. A Vercel *preview*
    # deployment (a PR branch, say) gets its own random subdomain that
    # won't match this list -- add it here (or set CORS_ALLOWED_ORIGINS in
    # Render's env vars) if you need preview builds to reach the API too.
    cors_allowed_origins: str = "http://localhost:3000,http://localhost:5173,https://vict-ai.vercel.app"

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

    @property
    def cors_allowed_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allowed_origins.split(",") if origin.strip()]


settings = Settings()

# Prefer PostgreSQL for the AI monitor. If Postgres is not running, fall back to
# SQLite so the app can still be exercised locally without a database service.
if not settings.database_url or settings.database_url.strip() == "":
    settings.database_url = "postgresql+psycopg://postgres:postgres@localhost:5432/ai_usage_monitor"
