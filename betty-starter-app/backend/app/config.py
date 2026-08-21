from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Betty"
    environment: str = "development"
    database_url: str = "sqlite:///./betty.db"

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)


settings = Settings()

# Prefer an explicit database URL from the environment, but keep a local SQLite
# default so the app can start without a running Postgres instance.
if not settings.database_url or settings.database_url.strip() == "":
    settings.database_url = "sqlite:///./betty.db"
