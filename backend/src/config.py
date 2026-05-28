from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import model_validator
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict


# Resolves to the project-root `data/` directory regardless of working directory.
# Local:  backend/src/config.py  → ../../..  → project root → data/
# Docker: /app/backend/src/config.py → ../../.. → /app/ → data/
_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"


class YamlConfigSource(PydanticBaseSettingsSource):
    """Load settings from a YAML file (lowest priority source)."""

    def __init__(self, settings_cls: type[BaseSettings], yaml_file: str | Path = _DATA_DIR / "settings.yaml"):
        super().__init__(settings_cls)
        self._data: dict[str, Any] = {}
        path = Path(yaml_file)
        if path.is_file():
            with open(path) as f:
                self._data = yaml.safe_load(f) or {}

    def get_field_value(self, field: Any, field_name: str) -> tuple[Any, str, bool]:
        return self._data.get(field_name), field_name, self.field_is_complex(field)

    def __call__(self) -> dict[str, Any]:
        return {k: v for k, v in self._data.items() if v is not None}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=[str(_DATA_DIR / ".env"), str(_DATA_DIR / ".env.local")],
        env_file_encoding="utf-8",
        populate_by_name=True,
        extra="ignore",
    )

    port: int = 8888
    debug: bool = False
    load_test_data: bool = False
    secret_key: str = "dev-secret-key-for-testing-change-in-production"
    database_url: str = f"sqlite+aiosqlite:///{_DATA_DIR}/sweepstake.db"
    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_pool_recycle: int = 3600
    access_token_expire_minutes: int = 5
    refresh_token_expire_days: int = 7
    password_reset_expire_minutes: int = 30
    main_host: str = "http://localhost:3000"
    hosts: list[str] = ["http://localhost:3000", "http://localhost:5173"]
    https_auth_only: bool = True
    email_host: str = ""
    email_port: int = 587
    email_host_user: str = ""
    email_host_password: str = ""
    email_from: str = "noreply@example.com"
    email_use_ssl: bool = False
    email_use_tls: bool = True
    football_data_org_api_key: str = ""
    football_data_org_api_tier: Literal["TIER_ONE", "TIER_TWO", "TIER_THREE", "TIER_FOUR"] = "TIER_ONE"
    demo_mode: bool = False
    root_path: str = ""
    sentry_dsn: str = ""
    app_version: str = ""

    @model_validator(mode="after")
    def _apply_demo_mode(self) -> Settings:
        if self.demo_mode:
            self.load_test_data = True
            self.https_auth_only = False
        return self

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        # Priority: env vars > .env files > settings.yaml
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            YamlConfigSource(settings_cls),
            file_secret_settings,
        )


settings = Settings()


def validate_secrets() -> None:
    if not settings.secret_key or settings.secret_key == "dev-secret-key-for-testing-change-in-production":
        print(
            "WARNING: SECRET_KEY not set or is the default dev value. "
            "Set SECRET_KEY environment variable."
        )
    if settings.database_url.startswith("sqlite"):
        print(
            "WARNING: Using SQLite database. "
            "PostgreSQL is recommended for production use. "
            "Set the DATABASE_URL environment variable to use PostgreSQL."
        )


validate_secrets()
