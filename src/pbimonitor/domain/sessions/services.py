from __future__ import annotations

from datetime import datetime

from pbimonitor.domain.sessions.entities import AuthSession


class SessionService:
    """Проверка жизненного цикла сессии и продление по keepalive."""

    def should_reauthenticate(self, session: AuthSession | None, now: datetime) -> bool:
        if session is None:
            return True
        return not session.is_alive(now)

    def mark_keepalive(self, session: AuthSession, now: datetime) -> AuthSession:
        return AuthSession(
            username=session.username,
            created_at=now,
            ttl_seconds=session.ttl_seconds,
            tokens=session.tokens,
        )

