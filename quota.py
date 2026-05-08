"""Gemini API 사용량 일일 카운터.

매 호출 시 increment(), 한도 도달 시 알림. UTC 자정 기준 자동 리셋.
실제 Google 카운터는 조회 API 없어서 로컬 추정값.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

QUOTA_FILE = Path("quota.json")
DAILY_LIMIT = 250  # gemini-2.5-flash free tier 추정 (보수적)


def _today() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def load_quota() -> dict:
    if not QUOTA_FILE.exists():
        return {"date": _today(), "calls": 0, "alerted": False}
    try:
        d = json.loads(QUOTA_FILE.read_text())
    except Exception:
        return {"date": _today(), "calls": 0, "alerted": False}
    if d.get("date") != _today():
        return {"date": _today(), "calls": 0, "alerted": False}
    d.setdefault("alerted", False)
    return d


def save_quota(d: dict) -> None:
    QUOTA_FILE.write_text(json.dumps(d, ensure_ascii=False, indent=2))


def increment() -> dict:
    d = load_quota()
    d["calls"] = d.get("calls", 0) + 1
    save_quota(d)
    return d


def mark_alerted() -> None:
    d = load_quota()
    d["alerted"] = True
    save_quota(d)


def status_text() -> str:
    d = load_quota()
    used = d.get("calls", 0)
    remaining = max(0, DAILY_LIMIT - used)
    pct = min(100, (used / DAILY_LIMIT) * 100) if DAILY_LIMIT else 0
    bar = "█" * int(pct / 10) + "░" * (10 - int(pct / 10))
    return (
        f"📈 <b>Gemini 사용량 (UTC 오늘)</b>\n"
        f"  <code>{bar}</code>  {pct:.0f}%\n"
        f"  사용: <b>{used}</b>회 / 한도: ~<b>{DAILY_LIMIT}</b>회\n"
        f"  남은 추정: <b>{remaining}</b>회\n"
        f"  <i>(UTC 00:00 자동 리셋)</i>"
    )
