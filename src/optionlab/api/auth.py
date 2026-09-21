"""Single-operator browser sessions; independent of trading authorization."""

import hashlib
import hmac
import secrets
import time
from collections import deque
from threading import Lock

from fastapi import Request

COOKIE = "optionlab_session"


def issue_session(secret: str, hours: int) -> str:
    message = f"v1.{int(time.time()) + hours * 3600}.{secrets.token_hex(16)}"
    signature = hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()
    return f"{message}.{signature}"


def valid_session(value: str, secret: str) -> bool:
    try:
        version, expires, nonce, signature = value.split(".")
        if version != "v1" or len(nonce) != 32 or int(expires) <= time.time():
            return False
        expected = hmac.new(
            secret.encode(), f"{version}.{expires}.{nonce}".encode(), hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(signature, expected)
    except (ValueError, TypeError):
        return False


def authorized(request: Request, settings) -> bool:
    if not settings.auth_required:
        return True
    header = request.headers.get("authorization", "")
    secret = settings.api_token.get_secret_value()
    if header.startswith("Bearer ") and hmac.compare_digest(header[7:].encode(), secret.encode()):
        return True
    return valid_session(request.cookies.get(COOKIE, ""), secret)


class LoginThrottle:
    """Small single-instance guard; use an edge limiter before scaling."""

    def __init__(self):
        self.attempts = deque()
        self.lock = Lock()

    def allow(self):
        with self.lock:
            now = time.monotonic()
            while self.attempts and self.attempts[0] < now - 60:
                self.attempts.popleft()
            if len(self.attempts) >= 20:
                return False
            self.attempts.append(now)
            return True
