import json
import os
import tempfile

import pytest

from pbimonitor.config.settings import Settings


def test_load_reports_skips_disabled_entries() -> None:
    payload = {
        "reports": [
            {"id": "enabled", "name": "Enabled", "url": "https://example.com/a", "interval": 5, "enabled": True},
            {"id": "disabled", "name": "Disabled", "url": "https://example.com/b", "interval": 5, "enabled": False},
            {"id": "enabled_without_flag", "name": "Enabled2", "url": "https://example.com/c", "interval": 5},
        ]
    }

    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as file:
        json.dump(payload, file)
        json_path = file.name

    try:
        settings = Settings(reports_file=json_path)
        reports = settings.load_reports()
        report_ids = [report.id for report in reports]
        assert report_ids == ["enabled", "enabled_without_flag"]
    finally:
        os.remove(json_path)


def test_reports_validation_rejects_invalid_interval() -> None:
    payload = {"reports": [{"id": "r1", "name": "R1", "url": "https://example.com/a", "interval": 0}]}
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as file:
        json.dump(payload, file)
        json_path = file.name
    try:
        settings = Settings(reports_file=json_path)
        with pytest.raises(ValueError):
            settings.load_reports()
    finally:
        os.remove(json_path)
