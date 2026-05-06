"""Telegram bot으로 알림 메시지 전송.

직접 실행하면 인자(또는 기본값 'hello')를 그대로 전송한다 — 채널 검증용.
다른 모듈에서는 notify(text) 함수를 import해서 사용.
"""

from __future__ import annotations

import os
import sys

import requests
from dotenv import load_dotenv

load_dotenv()


def _config() -> tuple[str, str]:
    token = os.environ.get("TELEGRAM_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        raise RuntimeError(
            "TELEGRAM_TOKEN 또는 TELEGRAM_CHAT_ID가 .env에 설정되지 않았습니다."
        )
    return token, chat_id


def notify(text: str) -> None:
    token, chat_id = _config()
    resp = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
        timeout=10,
    )
    resp.raise_for_status()


if __name__ == "__main__":
    msg = sys.argv[1] if len(sys.argv) > 1 else "hello from mail_project"
    notify(msg)
    print(f"전송 완료: {msg}")
