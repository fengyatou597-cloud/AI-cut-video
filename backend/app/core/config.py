from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path


class Settings(BaseSettings):
    app_name: str = "Local AI Video Rough Cut Assistant"
    database_url: str = "sqlite:///./storage/app.db"
    storage_dir: str = "./storage"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    jianying_drafts_dir: str | None = None

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def storage_path(self) -> Path:
        return Path(self.storage_dir).resolve()

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
settings.storage_path.mkdir(parents=True, exist_ok=True)
