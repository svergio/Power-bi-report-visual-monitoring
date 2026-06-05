from __future__ import annotations

import logging
import random
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional, TypeVar
from urllib.parse import quote, urlparse, urlunparse

from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

from pbimonitor.domain.sessions.entities import AuthSession
from pbimonitor.domain.sessions.services import SessionService
from pbimonitor.exceptions import SessionExpired, SeleniumTimeout

T = TypeVar("T")


@dataclass(frozen=True)
class RetryPolicy:
    attempts: int = 3
    base_delay_seconds: float = 1.0
    max_delay_seconds: float = 10.0
    jitter_seconds: float = 0.3


@dataclass(frozen=True)
class BrowserConfig:
    width: int
    height: int
    page_load_wait_seconds: int
    auth_server_whitelist: str
    username: Optional[str]
    password: Optional[str]
    headless: bool = True


class SeleniumClient:
    def __init__(
        self,
        browser: BrowserConfig,
        retry_policy: RetryPolicy,
        logger: logging.Logger,
        driver_factory: Callable[[Service, Options], webdriver.Chrome] | None = None,
        chromedriver_resolver: Callable[[], str] | None = None,
    ) -> None:
        self._browser = browser
        self._retry_policy = retry_policy
        self._logger = logger
        self._driver: Optional[webdriver.Chrome] = None
        self._session_service = SessionService()
        self._auth_session: Optional[AuthSession] = None
        self._driver_factory = driver_factory or (lambda service, options: webdriver.Chrome(service=service, options=options))
        self._chromedriver_resolver = chromedriver_resolver or (lambda: ChromeDriverManager().install())

    def close(self) -> None:
        if self._driver is None:
            return
        try:
            self._driver.quit()
        except WebDriverException:
            self._logger.warning("webdriver_quit_failed", exc_info=True)
        finally:
            self._driver = None

    def take_screenshot(self, url: str, output_path: Path) -> int:
        started = time.monotonic()
        self._ensure_driver()
        try:
            auth_url = self._build_auth_url(url)
            self._with_retry("driver_get", lambda: self._driver_get(auth_url))
            self._with_retry("wait_body", self._wait_body_loaded)
            self._with_retry("wait_iframe", self._wait_iframe_optional)
            self._with_retry("wait_spinners", self._wait_spinner_clear)
            time.sleep(self._browser.page_load_wait_seconds)
            self._switch_default_content()
            output_path.parent.mkdir(parents=True, exist_ok=True)
            self._with_retry("save_screenshot", lambda: self._save_screenshot(output_path))
            self._touch_session()
            return int((time.monotonic() - started) * 1000)
        except SessionExpired:
            self._logger.info("session_reauth_started")
            self.reauthenticate()
            auth_url = self._build_auth_url(url)
            self._with_retry("driver_get_post_reauth", lambda: self._driver_get(auth_url))
            self._with_retry("wait_body_post_reauth", self._wait_body_loaded)
            self._with_retry("save_screenshot_post_reauth", lambda: self._save_screenshot(output_path))
            self._touch_session()
            return int((time.monotonic() - started) * 1000)

    def reauthenticate(self) -> None:
        self.close()
        self._ensure_driver()
        self._auth_session = AuthSession(
            username=self._browser.username,
            created_at=datetime.now(timezone.utc),
            ttl_seconds=30 * 60,
        )

    def _ensure_driver(self) -> None:
        if self._driver is not None:
            return
        options = Options()
        if self._browser.headless:
            options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument(f"--window-size={self._browser.width},{self._browser.height}")
        if self._browser.auth_server_whitelist:
            options.add_argument(
                f"--auth-server-whitelist={self._browser.auth_server_whitelist}"
            )
            options.add_argument(
                "--auth-negotiate-delegate-whitelist="
                f"{self._browser.auth_server_whitelist}"
            )
        service = Service(self._chromedriver_resolver())
        self._driver = self._driver_factory(service, options)
        self._auth_session = AuthSession(
            username=self._browser.username,
            created_at=datetime.now(timezone.utc),
            ttl_seconds=30 * 60,
        )

    def _with_retry(self, operation: str, action: Callable[[], T]) -> T:
        last_error: Optional[Exception] = None
        for attempt in range(1, self._retry_policy.attempts + 1):
            try:
                return action()
            except SessionExpired:
                raise
            except (TimeoutException, WebDriverException, OSError) as exc:
                last_error = exc
                self._logger.warning(
                    "selenium_retry",
                    extra={"operation": operation, "attempt": attempt, "error": str(exc)},
                )
                if attempt == self._retry_policy.attempts:
                    break
                delay = min(
                    self._retry_policy.max_delay_seconds,
                    self._retry_policy.base_delay_seconds * (2 ** (attempt - 1)),
                )
                delay += random.uniform(0.0, self._retry_policy.jitter_seconds)  # nosec B311
                time.sleep(delay)
        raise SeleniumTimeout(f"Selenium operation failed: {operation}") from last_error

    def _driver_get(self, url: str) -> None:
        if self._driver is None:
            raise SeleniumTimeout("Webdriver is not initialized")
        self._driver.get(url)
        current_url = self._driver.current_url.lower()
        if "login" in current_url or "signin" in current_url:
            raise SessionExpired("Authentication session appears expired")

    def _wait_body_loaded(self) -> None:
        if self._driver is None:
            raise SeleniumTimeout("Webdriver is not initialized")
        WebDriverWait(self._driver, 30).until(ec.presence_of_element_located((By.TAG_NAME, "body")))

    def _wait_iframe_optional(self) -> None:
        if self._driver is None:
            raise SeleniumTimeout("Webdriver is not initialized")
        try:
            iframe = WebDriverWait(self._driver, 20).until(
                ec.presence_of_element_located((By.TAG_NAME, "iframe"))
            )
            self._driver.switch_to.frame(iframe)
        except TimeoutException:
            self._logger.info("iframe_not_found_continue")

    def _wait_spinner_clear(self) -> None:
        if self._driver is None:
            raise SeleniumTimeout("Webdriver is not initialized")
        try:
            WebDriverWait(self._driver, 25).until_not(
                ec.presence_of_element_located(
                    (By.CSS_SELECTOR, ".spinner, .loading, [class*='loading'], [class*='spinner']")
                )
            )
        except TimeoutException:
            self._logger.info("spinner_wait_timeout_continue")

    def _switch_default_content(self) -> None:
        if self._driver is None:
            return
        self._driver.switch_to.default_content()

    def _save_screenshot(self, output_path: Path) -> None:
        if self._driver is None:
            raise SeleniumTimeout("Webdriver is not initialized")
        if not self._driver.save_screenshot(str(output_path)):
            raise SeleniumTimeout("save_screenshot returned false")

    def _touch_session(self) -> None:
        if self._auth_session is None:
            return
        self._auth_session = self._session_service.mark_keepalive(
            self._auth_session, datetime.now(timezone.utc)
        )

    def _build_auth_url(self, url: str) -> str:
        if not self._browser.username or not self._browser.password:
            return url
        parsed = urlparse(url)
        username = quote(self._browser.username, safe="")
        password = quote(self._browser.password, safe="")
        netloc = f"{username}:{password}@{parsed.hostname}"
        if parsed.port:
            netloc += f":{parsed.port}"
        return urlunparse(
            (
                parsed.scheme,
                netloc,
                parsed.path,
                parsed.params,
                parsed.query,
                parsed.fragment,
            )
        )

