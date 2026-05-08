"""새 메일을 감지해서 Claude로 분류한 뒤, 중요 메일만 Telegram으로 알림.

첫 실행: 알림 없이 가장 최신 메시지 ID만 기록 (과거 메일 폭탄 방지).
이후 실행: 기록된 ID 이후의 새 메일을 분류해서 "무관"이 아닌 것만 알림.
차단된 발신자는 분류기 호출 없이 즉시 무시.
"""

from __future__ import annotations

import html
import os.path
import re
from pathlib import Path

import quota
from auth_gmail import get_service
from classify import RateLimitError, classify
from i18n import t
from send_telegram import notify
from telegram_commands import process_commands

LAST_SEEN_FILE = "last_seen_id.txt"
BLOCKED_FILE = "blocked_senders.txt"
MAX_FETCH = 20  # 한 번에 확인할 최신 메일 개수


def extract_email(sender_full: str) -> str:
    """'Name <email@domain>' 또는 'email@domain' → 'email@domain' (소문자)"""
    m = re.search(r"<([^>]+@[^>]+)>", sender_full)
    if m:
        return m.group(1).strip().lower()
    if "@" in sender_full:
        return sender_full.strip().lower()
    return ""


def load_blocked_senders() -> set[str]:
    p = Path(BLOCKED_FILE)
    if not p.exists():
        return set()
    return {
        line.split("#")[0].strip().lower()
        for line in p.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    }


def read_last_seen() -> str:
    if not os.path.exists(LAST_SEEN_FILE):
        return ""
    with open(LAST_SEEN_FILE) as f:
        return f.read().strip()


def write_last_seen(msg_id: str) -> None:
    with open(LAST_SEEN_FILE, "w") as f:
        f.write(msg_id)


def fetch_metadata(service, msg_id: str) -> dict:
    full = (
        service.users()
        .messages()
        .get(
            userId="me",
            id=msg_id,
            format="full",
        )
        .execute()
    )
    headers = {h["name"]: h["value"] for h in full["payload"]["headers"]}
    return {
        "id": msg_id,
        "subject": headers.get("Subject", "(제목 없음)"),
        "from": headers.get("From", ""),
        "snippet": full.get("snippet", ""),
    }


def format_message(m: dict, reasoning: str) -> str:
    subject = html.escape(m["subject"])
    sender = html.escape(m["from"])
    snippet = html.escape(m["snippet"][:300])
    reason = html.escape(reasoning)
    email = extract_email(m["from"])
    judgment = t("alert_judgment", reason=reason)
    block_hint = (
        f"\n\n<i>{t('alert_block_hint')}</i> <code>/block {email}</code>"
        if email else ""
    )
    return (
        f"🔔 <b>{subject}</b>\n"
        f"From: {sender}\n"
        f"<i>{judgment}</i>\n\n"
        f"{snippet}"
        f"{block_hint}"
    )


def main() -> None:
    service = get_service()
    resp = (
        service.users()
        .messages()
        .list(userId="me", q="in:inbox", maxResults=MAX_FETCH)
        .execute()
    )
    msgs = resp.get("messages", [])  # 최신순
    if not msgs:
        print("받은편지함이 비어있습니다.")
        return

    last_seen = read_last_seen()

    if not last_seen:
        write_last_seen(msgs[0]["id"])
        print(
            f"첫 실행 — baseline 설정 (id={msgs[0]['id']}). "
            "다음 실행부터 새 메일을 Telegram으로 알립니다."
        )
        return

    new_ids = []
    for m in msgs:
        if m["id"] == last_seen:
            break
        new_ids.append(m["id"])

    if not new_ids:
        print("새 메일 없음.")
        return

    blocked = load_blocked_senders()
    print(f"새 메일 {len(new_ids)}개 발견. 분류 시작. (차단 발신자: {len(blocked)}개)")
    notified = 0
    blocked_count = 0
    last_processed = None
    quota_hit = False

    for msg_id in reversed(new_ids):
        meta = fetch_metadata(service, msg_id)
        sender_email = extract_email(meta["from"])
        if sender_email and sender_email in blocked:
            blocked_count += 1
            last_processed = msg_id
            print(f"  🚫 [차단] {meta['subject']}  ({sender_email})")
            continue

        try:
            result = classify(meta["from"], meta["subject"], meta["snippet"])
        except RateLimitError as e:
            quota_hit = True
            q = quota.load_quota()
            if not q.get("alerted"):
                notify(t("quota_alert", status=quota.status_text()))
                quota.mark_alerted()
            print(f"  ⚠️  [QUOTA] {meta['subject']}  → 분류 중단 ({e})")
            break

        should_notify = result["notify"]
        reasoning = result["reasoning"]
        last_processed = msg_id

        if should_notify:
            notify(format_message(meta, reasoning))
            notified += 1
            print(f"  🔔 [알림] {meta['subject']}  →  {reasoning}")
        else:
            print(f"  ⏭️  [무시] {meta['subject']}  →  {reasoning}")

    print(f"\n총 {len(new_ids)}개 중 {notified}개 알림, {blocked_count}개 차단 무시{', QUOTA 중단' if quota_hit else ''}.")

    # 처리한 마지막 메일 ID로 baseline 갱신 (quota 중단 시 부분 진행만 저장)
    if last_processed:
        write_last_seen(last_processed)


def run_telegram_commands() -> None:
    """Telegram bot 명령 처리. 메일 체크와 독립적으로 실행."""
    try:
        process_commands()
    except Exception as e:
        print(f"⚠️ Telegram 명령 처리 실패: {e}")


if __name__ == "__main__":
    main()
    run_telegram_commands()
