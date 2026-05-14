from __future__ import annotations

from datetime import UTC, datetime, timedelta

from pbimonitor.domain.sessions.entities import AuthSession
from pbimonitor.domain.sessions.services import SessionService


def test_session_service_reauth_and_keepalive() -> None:
    service = SessionService()
    now = datetime.now(UTC)
    session = AuthSession(username="user", created_at=now - timedelta(hours=1), ttl_seconds=10)

    assert service.should_reauthenticate(session, now) is True

    fresh = service.mark_keepalive(session, now)
    assert service.should_reauthenticate(fresh, now) is False

