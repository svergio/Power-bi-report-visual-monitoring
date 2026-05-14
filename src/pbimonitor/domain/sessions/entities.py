from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional


@dataclass(frozen=True)
class Tokens:
    access_token: str
    refresh_token: Optional[str] = None
    expires_at: Optional[datetime] = None

    def is_expired(self, now: datetime) -> bool:
        if self.expires_at is None:
            return False
        return now >= self.expires_at


@dataclass
class AuthSession:
    username: Optional[str]
    created_at: datetime
    ttl_seconds: int
    tokens: Optional[Tokens] = None

    def expires_at(self) -> datetime:
        return self.created_at + timedelta(seconds=self.ttl_seconds)

    def is_alive(self, now: datetime) -> bool:
        return now < self.expires_at()

