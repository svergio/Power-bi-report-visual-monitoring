from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from pbimonitor.domain.reports.entities import Report

SCHEMA_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class ReportConfigModel(BaseModel):
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    url: HttpUrl
    interval: int = Field(ge=1, le=1440)
    start_time: str = "09:00"
    threshold: float = Field(default=5.0, ge=0.0, le=100.0)
    enabled: bool = True

    @field_validator("start_time")
    @classmethod
    def validate_start_time(cls, value: str) -> str:
        if not re.match(r"^\d{2}:\d{2}$", value):
            raise ValueError("start_time must be HH:MM")
        hh, mm = value.split(":")
        hour = int(hh)
        minute = int(mm)
        if hour > 23 or minute > 59:
            raise ValueError("start_time must be valid 24h time")
        return value

    def to_domain(self) -> Report:
        return Report(
            id=self.id,
            name=self.name,
            url=str(self.url),
            interval_minutes=self.interval,
            start_time=self.start_time,
            threshold=self.threshold,
            enabled=self.enabled,
        )


class ReportsFileModel(BaseModel):
    reports: list[ReportConfigModel]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    env: Literal["development", "production", "test"] = "development"
    log_level: str = "INFO"

    pg_host: str = "localhost"
    pg_port: int = 5432
    pg_database: str = "postgres"
    pg_user: str = "postgres"
    pg_password: str = ""
    pg_schema: str = "public"
    pg_schema_allowlist: str = "public,sandbox"
    pg_pool_min_size: int = 1
    pg_pool_max_size: int = 10

    powerbi_username: str | None = None
    powerbi_password: str | None = None
    powerbi_auth_server_whitelist: str = ""

    reports_file: str = "reports.json"
    screenshots_dir: str = "./Data"
    min_worker_threads: int = 1
    max_worker_threads: int = 5
    page_load_wait: int = 10
    screenshot_width: int = 1920
    screenshot_height: int = 1080

    mse_threshold: float = 10.0
    min_block_size: int = 32
    max_depth: int = 5
    diff_enabled: bool = True

    retry_attempts: int = 3
    retry_base_delay_seconds: float = 1.0
    retry_max_delay_seconds: float = 10.0
    retry_jitter_seconds: float = 0.3

    @field_validator("pg_schema")
    @classmethod
    def validate_pg_schema(cls, value: str) -> str:
        if not SCHEMA_PATTERN.match(value):
            raise ValueError("PG_SCHEMA is invalid")
        return value

    def validate_allowlist(self) -> None:
        allowlist = [item.strip() for item in self.pg_schema_allowlist.split(",") if item.strip()]
        if self.pg_schema not in allowlist:
            raise ValueError(f"PG_SCHEMA '{self.pg_schema}' is not in allowlist")

    @property
    def dsn(self) -> str:
        return (
            f"host={self.pg_host} port={self.pg_port} dbname={self.pg_database} "
            f"user={self.pg_user} password={self.pg_password}"
        )

    def load_reports(self) -> list[Report]:
        path = Path(self.reports_file)
        payload = json.loads(path.read_text(encoding="utf-8"))
        parsed = ReportsFileModel.model_validate(payload)
        return [item.to_domain() for item in parsed.reports if item.enabled]

    @classmethod
    def from_env_file(cls, env_file: str) -> "Settings":
        return cls(_env_file=env_file)  # type: ignore[call-arg]

