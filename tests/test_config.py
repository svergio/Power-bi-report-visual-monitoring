import os
import tempfile

import pytest

from pbimonitor.config.settings import Settings


def test_load_settings_from_env_file() -> None:
    with tempfile.NamedTemporaryFile("w", suffix=".env", delete=False, encoding="utf-8") as file:
        file.write("PG_HOST=db.example.local\n")
        file.write("PG_DATABASE=monitor\n")
        file.write("PG_USER=monitor_user\n")
        file.write("PG_SCHEMA=analytics\n")
        file.write("PG_SCHEMA_ALLOWLIST=analytics,public\n")
        file.write("MIN_WORKER_THREADS=2\n")
        file.write("MAX_WORKER_THREADS=4\n")
        env_path = file.name

    try:
        settings = Settings.from_env_file(env_path)
        settings.validate_allowlist()
        assert settings.pg_host == "db.example.local"
        assert settings.pg_schema == "analytics"
        assert settings.max_worker_threads == 4
    finally:
        os.remove(env_path)


def test_validation_fails_for_invalid_schema() -> None:
    with tempfile.NamedTemporaryFile("w", suffix=".env", delete=False, encoding="utf-8") as file:
        file.write("PG_SCHEMA=invalid schema\n")
        env_path = file.name

    try:
        with pytest.raises(ValueError):
            Settings.from_env_file(env_path)
    finally:
        os.remove(env_path)
