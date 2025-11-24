from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Глобальные настройки приложения."""

    project_name: str = "Events Afisha API"
    api_v1_prefix: str = "/api/v1"

    db_host: str = "db"
    db_port: int = 5432
    db_user: str = "afisha"
    db_password: str = "afisha"
    db_name: str = "afisha"

    backend_cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    secret_key: str = "CHANGE_ME_IN_PROD"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def database_url(self) -> str:
        """Собирает URL подключения к базе данных."""
        return (
            f"postgresql+asyncpg://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )


settings = Settings()
