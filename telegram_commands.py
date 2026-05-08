"""Telegram bot 명령어 처리 (양방향).

매 cron 실행 시 main.py에서 process_commands() 호출.
- 본인 chat_id에서 온 / 명령만 처리 (다른 사람 봇 발견해도 무시)
- senders.txt를 직접 편집 (workflow가 변경분을 자동 commit)
- 처리한 update_id는 telegram_offset.txt에 저장해서 중복 처리 방지
"""

from __future__ import annotations

import os
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

SENDERS_FILE = Path("senders.txt")
OFFSET_FILE = Path("telegram_offset.txt")

API = f"https://api.telegram.org/bot{os.environ.get('TELEGRAM_TOKEN', '')}"

HELP = """🤖 <b>명령어</b>

/list — 중요 발신자 목록
/add EMAIL — 발신자 추가
/remove EMAIL — 발신자 제거
/status — 시스템 상태
/help — 이 메뉴

<i>변경 사항은 다음 cron 실행(최대 10분)에 반영됩니다.</i>"""


def _allowed_chat_id() -> int:
    return int(os.environ["TELEGRAM_CHAT_ID"])


def _send(text: str, chat_id: int) -> None:
    requests.post(
        f"{API}/sendMessage",
        json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
        timeout=10,
    )


def _read_offset() -> int:
    if not OFFSET_FILE.exists():
        return 0
    try:
        return int(OFFSET_FILE.read_text().strip() or 0)
    except ValueError:
        return 0


def _write_offset(offset: int) -> None:
    OFFSET_FILE.write_text(str(offset))


def _read_senders_lines() -> list[str]:
    if not SENDERS_FILE.exists():
        return []
    return SENDERS_FILE.read_text(encoding="utf-8").splitlines()


def _write_senders_lines(lines: list[str]) -> None:
    SENDERS_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _email_from_line(line: str) -> str | None:
    """주석/빈줄 제외하고 이메일만 추출. 'foo@bar.com  # 코멘트' → 'foo@bar.com'"""
    line = line.strip()
    if not line or line.startswith("#"):
        return None
    email_part = line.split("#")[0].strip()
    return email_part if "@" in email_part else None


def _parsed_emails(lines: list[str]) -> list[str]:
    return [e for e in (_email_from_line(line) for line in lines) if e]


def _handle(text: str) -> tuple[str, bool]:
    """명령어 처리. (응답 메시지, 파일 변경됨) 반환."""
    text = text.strip()

    if text in ("/help", "/start"):
        return HELP, False

    if text == "/list":
        lines = _read_senders_lines()
        emails = _parsed_emails(lines)
        if not emails:
            return "📋 등록된 중요 발신자가 없습니다.\n\n<code>/add EMAIL</code>로 추가하세요.", False
        body = "\n".join(f"  • <code>{e}</code>" for e in emails)
        return f"📋 <b>중요 발신자 ({len(emails)}개)</b>\n{body}", False

    if text == "/status":
        lines = _read_senders_lines()
        emails = _parsed_emails(lines)
        return (
            f"📊 <b>시스템 상태</b>\n"
            f"  중요 발신자: <b>{len(emails)}개</b>\n"
            f"  cron 주기: <b>10분</b>\n"
            f"  분류 모델: Gemini 2.5 Flash Lite\n"
            f"  Repo: <a href=\"https://github.com/Sweet-Butters/mail-notifier\">Sweet-Butters/mail-notifier</a>"
        ), False

    if text.startswith("/add "):
        email = text[5:].strip()
        if "@" not in email or " " in email:
            return f"⚠️ 이메일 형식이 아닙니다: <code>{email}</code>", False
        lines = _read_senders_lines()
        if email in _parsed_emails(lines):
            return f"ℹ️ 이미 등록된 발신자: <code>{email}</code>", False
        lines.append(email)
        _write_senders_lines(lines)
        emails = _parsed_emails(lines)
        return f"✅ 추가됨: <code>{email}</code>\n현재 총 <b>{len(emails)}개</b>", True

    if text.startswith("/remove "):
        email = text[8:].strip()
        lines = _read_senders_lines()
        new_lines = [line for line in lines if _email_from_line(line) != email]
        if len(new_lines) == len(lines):
            return f"ℹ️ 등록되지 않은 발신자: <code>{email}</code>", False
        _write_senders_lines(new_lines)
        emails = _parsed_emails(new_lines)
        return f"🗑 제거됨: <code>{email}</code>\n현재 총 <b>{len(emails)}개</b>", True

    return f"❓ 모르는 명령: <code>{text}</code>\n\n<code>/help</code> 로 도움말 확인", False


def process_commands() -> bool:
    """새 Telegram 명령들 처리. 파일이 변경됐으면 True 반환."""
    if not os.environ.get("TELEGRAM_TOKEN") or not os.environ.get("TELEGRAM_CHAT_ID"):
        print("ℹ️ Telegram 환경변수 없음, 명령 처리 건너뜀.")
        return False

    allowed = _allowed_chat_id()
    offset = _read_offset()

    params = {"timeout": 0}
    if offset:
        params["offset"] = offset + 1

    try:
        r = requests.get(f"{API}/getUpdates", params=params, timeout=15)
        r.raise_for_status()
        updates = r.json().get("result", [])
    except Exception as e:
        print(f"⚠️ getUpdates 실패: {e}")
        return False

    if not updates:
        return False

    file_changed = False
    last_id = offset
    for upd in updates:
        last_id = upd["update_id"]
        msg = upd.get("message") or upd.get("edited_message")
        if not msg:
            continue
        chat_id = msg.get("chat", {}).get("id")
        if chat_id != allowed:
            print(f"⛔ 허용 안 된 chat_id에서 메시지 무시: {chat_id}")
            continue
        text = msg.get("text", "").strip()
        if not text or not text.startswith("/"):
            continue

        reply, changed = _handle(text)
        _send(reply, chat_id)
        if changed:
            file_changed = True
        print(f"  📨 명령 처리: {text!r}  →  {reply.splitlines()[0][:50]}")

    _write_offset(last_id)
    return file_changed
