from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Betty"
    environment: str = "development"
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/betty"

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)


settings = Settings()
