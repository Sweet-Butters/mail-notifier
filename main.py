"""새 메일을 감지해서 Claude로 분류한 뒤, 중요 메일만 Telegram으로 알림.

첫 실행: 알림 없이 가장 최신 메시지 ID만 기록 (과거 메일 폭탄 방지).
이후 실행: 기록된 ID 이후의 새 메일을 분류해서 "무관"이 아닌 것만 알림.
"""

from __future__ import annotations

import html
import os.path

from auth_gmail import get_service
from classify import classify
from send_telegram import notify

LAST_SEEN_FILE = "last_seen_id.txt"
MAX_FETCH = 20  # 한 번에 확인할 최신 메일 개수
NOTIFY_CATEGORIES = {"면접", "합격여부", "중요인물"}

CATEGORY_EMOJI = {
    "면접": "🗓️",
    "합격여부": "🎯",
    "중요인물": "⭐",
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


def format_message(m: dict, category: str, reasoning: str) -> str:
    emoji = CATEGORY_EMOJI.get(category, "📬")
    subject = html.escape(m["subject"])
    sender = html.escape(m["from"])
    snippet = html.escape(m["snippet"][:300])
    reason = html.escape(reasoning)
    return (
        f"{emoji} <b>[{category}]</b> {subject}\n"
        f"From: {sender}\n"
        f"<i>판단: {reason}</i>\n\n"
        f"{snippet}"
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

    print(f"새 메일 {len(new_ids)}개 발견. 분류 시작.")
    notified = 0
    for msg_id in reversed(new_ids):
        meta = fetch_metadata(service, msg_id)
        result = classify(meta["from"], meta["subject"], meta["snippet"])
        category = result["category"]
        reasoning = result["reasoning"]

        if category in NOTIFY_CATEGORIES:
            notify(format_message(meta, category, reasoning))
            notified += 1
            print(f"  ✅ [{category}] {meta['subject']}  →  {reasoning}")
        else:
            print(f"  ⏭️  [{category}] {meta['subject']}  →  {reasoning}")

    print(f"\n총 {len(new_ids)}개 중 {notified}개 알림 전송.")
    write_last_seen(msgs[0]["id"])


if __name__ == "__main__":
    main()
