import base64
import html
import random
import time
import uuid
from threading import Lock
from typing import Dict, Tuple

CAPTCHA_LENGTH = 5
CAPTCHA_TTL_SECONDS = 300
CAPTCHA_CHARS = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


class CaptchaProvider:
    _store: Dict[str, Tuple[str, float]] = {}
    _lock = Lock()

    @classmethod
    def generate(cls) -> dict:
        token = str(uuid.uuid4())
        value = "".join(random.choice(CAPTCHA_CHARS) for _ in range(CAPTCHA_LENGTH))
        expires_at = time.time() + CAPTCHA_TTL_SECONDS

        with cls._lock:
            cls._cleanup_expired()
            cls._store[token] = (value, expires_at)

        return {
            "captcha_token": token,
            "captcha_image": cls._render_svg_data_url(value),
            "expires_in": CAPTCHA_TTL_SECONDS,
        }

    @classmethod
    def validate(cls, token: str, value: str) -> bool:
        normalized_value = value.strip().upper()
        with cls._lock:
            record = cls._store.get(token)
            if record is None:
                return False

            expected, expires_at = record
            if time.time() > expires_at:
                cls._store.pop(token, None)
                return False

            if expected != normalized_value:
                return False

            cls._store.pop(token, None)
            return True

    @classmethod
    def _cleanup_expired(cls) -> None:
        now = time.time()
        expired_tokens = [token for token, (_, expires_at) in cls._store.items() if now > expires_at]
        for token in expired_tokens:
            cls._store.pop(token, None)

    @staticmethod
    def _render_svg_data_url(value: str) -> str:
        width = 150
        height = 52
        chars = []
        for index, char in enumerate(value):
            x = 18 + index * 25
            y = random.randint(31, 39)
            rotate = random.randint(-18, 18)
            chars.append(
                f'<text x="{x}" y="{y}" transform="rotate({rotate} {x} {y})">'
                f"{html.escape(char)}</text>"
            )

        lines = []
        for _ in range(7):
            x1 = random.randint(0, width)
            y1 = random.randint(0, height)
            x2 = random.randint(0, width)
            y2 = random.randint(0, height)
            color = random.choice(["#2563eb", "#16a34a", "#dc2626", "#7c3aed", "#0f766e"])
            lines.append(
                f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
                f'stroke="{color}" stroke-width="1.4" opacity="0.45" />'
            )

        svg = (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}">'
            '<rect width="100%" height="100%" rx="6" fill="#f8fafc"/>'
            '<g font-family="Arial, Helvetica, sans-serif" font-size="28" '
            'font-weight="700" fill="#111827" letter-spacing="2">'
            f'{"".join(chars)}'
            '</g>'
            f'{"".join(lines)}'
            '</svg>'
        )
        encoded = base64.b64encode(svg.encode("utf-8")).decode("ascii")
        return f"data:image/svg+xml;base64,{encoded}"
