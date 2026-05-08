"""Gemini API 사용량 일일 카운터 / Daily quota counter.

매 호출 시 increment(), 한도 도달 시 알림 / Increment on each call, alert on limit.
실제 Google 카운터는 조회 API 없어서 로컬 추정값 / Local estimate (no public Google counter API).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from i18n import t

QUOTA_FILE = Path("quota.json")
DAILY_LIMIT = 250  # gemini-2.5-flash free tier 추정


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
    return t("quota_message", bar=bar, pct=pct, used=used, limit=DAILY_LIMIT, remaining=remaining)
