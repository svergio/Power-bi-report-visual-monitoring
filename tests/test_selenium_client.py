from __future__ import annotations

import logging
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from selenium.common.exceptions import TimeoutException, WebDriverException

from pbimonitor.exceptions import SeleniumTimeout
from pbimonitor.infrastructure.selenium.client import BrowserConfig, RetryPolicy, SeleniumClient


def _make_client(driver: MagicMock) -> SeleniumClient:
    logger = logging.getLogger("test-selenium")
    logger.handlers = []
    logger.addHandler(logging.NullHandler())
    return SeleniumClient(
        browser=BrowserConfig(
            width=1920,
            height=1080,
            page_load_wait_seconds=0,
            auth_server_whitelist="",
            username=None,
            password=None,
            headless=True,
        ),
        retry_policy=RetryPolicy(attempts=2, base_delay_seconds=0.01, max_delay_seconds=0.02),
        logger=logger,
        driver_factory=lambda _service, _options: driver,
        chromedriver_resolver=lambda: "/tmp/chromedriver",
    )


def test_retry_then_success(tmp_path: Path) -> None:
    driver = MagicMock()
    driver.current_url = "https://powerbi.example.com/report"
    driver.get.side_effect = [WebDriverException("temporary"), None]
    driver.save_screenshot.return_value = True

    with patch("pbimonitor.infrastructure.selenium.client.WebDriverWait") as wait_cls:
        wait = wait_cls.return_value
        wait.until.return_value = MagicMock()
        wait.until_not.return_value = True
        client = _make_client(driver)
        output = tmp_path / "shot.png"
        client.take_screenshot("https://powerbi.example.com/report", output)
        assert driver.get.call_count == 2


def test_timeout_raises_selenium_timeout(tmp_path: Path) -> None:
    driver = MagicMock()
    driver.current_url = "https://powerbi.example.com/report"
    driver.get.side_effect = TimeoutException("timeout")

    with patch("pbimonitor.infrastructure.selenium.client.WebDriverWait"):
        client = _make_client(driver)
        output = tmp_path / "shot.png"
        with pytest.raises(SeleniumTimeout):
            client.take_screenshot("https://powerbi.example.com/report", output)


def test_missing_iframe_is_non_fatal(tmp_path: Path) -> None:
    driver = MagicMock()
    driver.current_url = "https://powerbi.example.com/report"
    driver.get.return_value = None
    driver.save_screenshot.return_value = True

    with patch("pbimonitor.infrastructure.selenium.client.WebDriverWait") as wait_cls:
        wait = wait_cls.return_value
        wait.until.side_effect = [MagicMock(), TimeoutException("no iframe")]
        wait.until_not.return_value = True
        client = _make_client(driver)
        output = tmp_path / "shot.png"
        duration = client.take_screenshot("https://powerbi.example.com/report", output)
        assert duration >= 0


def test_auth_failure_triggers_reauth(tmp_path: Path) -> None:
    first_driver = MagicMock()
    second_driver = MagicMock()
    first_driver.current_url = "https://login.microsoftonline.com/auth"
    second_driver.current_url = "https://powerbi.example.com/report"
    first_driver.save_screenshot.return_value = False
    second_driver.save_screenshot.return_value = True

    with patch("pbimonitor.infrastructure.selenium.client.WebDriverWait") as wait_cls:
        wait = wait_cls.return_value
        wait.until.return_value = MagicMock()
        wait.until_not.return_value = True
        logger = logging.getLogger("test-auth")
        logger.handlers = []
        logger.addHandler(logging.NullHandler())
        drivers = [first_driver, second_driver]
        client = SeleniumClient(
            browser=BrowserConfig(
                width=1920,
                height=1080,
                page_load_wait_seconds=0,
                auth_server_whitelist="",
                username="user",
                password="pass",
                headless=True,
            ),
            retry_policy=RetryPolicy(attempts=1, base_delay_seconds=0.01, max_delay_seconds=0.02),
            logger=logger,
            driver_factory=lambda _service, _options: drivers.pop(0),
            chromedriver_resolver=lambda: "/tmp/chromedriver",
        )
        output = tmp_path / "shot.png"
        client.take_screenshot("https://powerbi.example.com/report", output)
        assert wait_cls.call_count >= 1

