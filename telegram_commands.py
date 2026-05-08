"""Telegram bot 명령어 처리 (양방향).

매 cron 실행 시 main.py에서 process_commands() 호출.
- 본인 chat_id에서 온 / 명령만 처리 (다른 사람 봇 발견해도 무시)
- senders.txt / watching.txt / blocked_senders.txt를 직접 편집
- 처리한 update_id는 telegram_offset.txt에 저장
"""

from __future__ import annotations

import os
from pathlib import Path

import requests
from dotenv import load_dotenv

import i18n
import quota
from i18n import t

load_dotenv()

SENDERS_FILE = Path("senders.txt")
WATCHING_FILE = Path("watching.txt")
BLOCKED_FILE = Path("blocked_senders.txt")
OFFSET_FILE = Path("telegram_offset.txt")

API = f"https://api.telegram.org/bot{os.environ.get('TELEGRAM_TOKEN', '')}"

KNOWN_COMMANDS = {
    "add", "remove", "watch", "unwatch", "block", "unblock",
    "list", "status", "help", "start", "quota", "lang",
}


def _allowed_chat_id() -> int:
    return int(os.environ["TELEGRAM_CHAT_ID"])


def _send(text: str, chat_id: int) -> None:
    requests.post(
        f"{API}/sendMessage",
        json={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        },
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


# --- senders.txt 헬퍼 ---


def _read_senders_lines() -> list[str]:
    if not SENDERS_FILE.exists():
        return []
    return SENDERS_FILE.read_text(encoding="utf-8").splitlines()


def _write_senders_lines(lines: list[str]) -> None:
    SENDERS_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _email_from_line(line: str) -> str | None:
    line = line.strip()
    if not line or line.startswith("#"):
        return None
    email_part = line.split("#")[0].strip()
    return email_part if "@" in email_part else None


def _parsed_emails(lines: list[str]) -> list[str]:
    return [e for e in (_email_from_line(line) for line in lines) if e]


# --- watching.txt 헬퍼 ---

WATCHING_HEADER = (
    "# 현재 기다리는 메일 항목 / Current watch list (한 줄에 하나 / one per line)\n"
    "# Bot이 /watch로 추가, /unwatch로 삭제 / managed by bot\n"
)


def _read_watching() -> list[str]:
    if not WATCHING_FILE.exists():
        return []
    return [
        line.strip()
        for line in WATCHING_FILE.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]


def _write_watching(items: list[str]) -> None:
    body = "\n".join(items) + "\n" if items else ""
    WATCHING_FILE.write_text(WATCHING_HEADER + "\n" + body, encoding="utf-8")


# --- blocked_senders.txt 헬퍼 ---

BLOCKED_HEADER = (
    "# 차단된 발신자 목록 / Blocked senders (분류기 호출 없이 즉시 무시 / skipped without classification)\n"
    "# Bot이 /block으로 추가, /unblock으로 해제\n"
)


def _read_blocked() -> list[str]:
    if not BLOCKED_FILE.exists():
        return []
    return [
        line.split("#")[0].strip().lower()
        for line in BLOCKED_FILE.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]


def _write_blocked(items: list[str]) -> None:
    body = "\n".join(items) + "\n" if items else ""
    BLOCKED_FILE.write_text(BLOCKED_HEADER + "\n" + body, encoding="utf-8")


# --- 명령 디스패치 ---


def _normalize(text: str) -> str | None:
    """슬래시 옵션화 + 알려진 명령만 통과. None이면 무시할 메시지."""
    text = text.strip()
    if not text:
        return None
    parts = text.split(maxsplit=1)
    cmd = parts[0].lstrip("/").lower()
    arg = parts[1] if len(parts) > 1 else ""
    if cmd not in KNOWN_COMMANDS:
        return None
    return f"/{cmd}" + (f" {arg}" if arg else "")


def _handle(text: str) -> tuple[str, bool]:
    """명령어 처리. (응답, 파일 변경됨) 반환."""
    text = text.strip()

    if text in ("/help", "/start"):
        return t("help"), False

    if text == "/quota":
        return quota.status_text(), False

    # ----- 언어 -----
    if text == "/lang":
        return t("lang_current", lang=i18n.get_lang()), False

    if text.startswith("/lang "):
        new_lang = text[6:].strip().lower()
        if i18n.set_lang(new_lang):
            return t("lang_changed", lang=new_lang), True
        return t("lang_invalid", lang=new_lang), False

    # ----- 통합 조회 -----
    if text == "/list":
        emails = _parsed_emails(_read_senders_lines())
        watch = _read_watching()
        blocked = _read_blocked()
        out = [t("list_header") + "\n"]
        out.append(t("list_senders", count=len(emails)))
        if emails:
            out.extend(f"  • <code>{e}</code>" for e in emails)
        else:
            out.append(t("list_empty"))
        out.append("")
        out.append(t("list_watching", count=len(watch)))
        if watch:
            out.extend(f"  #{i+1}. {w}" for i, w in enumerate(watch))
        else:
            out.append(t("list_empty"))
        out.append("")
        out.append(t("list_blocked", count=len(blocked)))
        if blocked:
            out.extend(f"  • <code>{e}</code>" for e in blocked)
        else:
            out.append(t("list_empty"))
        return "\n".join(out), False

    if text == "/status":
        emails = _parsed_emails(_read_senders_lines())
        watch = _read_watching()
        blocked = _read_blocked()
        return t(
            "status_message",
            senders=len(emails),
            watching=len(watch),
            blocked=len(blocked),
            lang=i18n.get_lang(),
        ), False

    # ----- 발신자 -----
    if text.startswith("/add "):
        email = text[5:].strip()
        if "@" not in email or " " in email:
            return t("add_invalid", email=email), False
        lines = _read_senders_lines()
        if email in _parsed_emails(lines):
            return t("add_exists", email=email), False
        lines.append(email)
        _write_senders_lines(lines)
        return t("add_success", email=email, count=len(_parsed_emails(lines))), True

    if text.startswith("/remove "):
        email = text[8:].strip()
        lines = _read_senders_lines()
        new_lines = [line for line in lines if _email_from_line(line) != email]
        if len(new_lines) == len(lines):
            return t("remove_not_found", email=email), False
        _write_senders_lines(new_lines)
        return t("remove_success", email=email, count=len(_parsed_emails(new_lines))), True

    # ----- 기다리는 메일 -----
    if text.startswith("/watch "):
        desc = text[7:].strip()
        if not desc:
            return t("watch_usage"), False
        if len(desc) > 300:
            return t("watch_too_long", length=len(desc), max_length=300), False
        watch = _read_watching()
        if desc in watch:
            return t("watch_exists", desc=desc), False
        watch.append(desc)
        _write_watching(watch)
        return t("watch_added", n=len(watch), desc=desc, count=len(watch)), True

    if text.startswith("/unwatch "):
        arg = text[9:].strip()
        watch = _read_watching()
        if not watch:
            return t("unwatch_empty"), False
        if arg.isdigit():
            idx = int(arg) - 1
            if 0 <= idx < len(watch):
                removed = watch.pop(idx)
                _write_watching(watch)
                return t("unwatch_by_index", n=idx + 1, desc=removed, count=len(watch)), True
            return t("unwatch_index_invalid", n=arg, max=len(watch)), False
        if arg in watch:
            watch.remove(arg)
            _write_watching(watch)
            return t("unwatch_by_text", desc=arg, count=len(watch)), True
        return t("unwatch_not_found"), False

    # ----- 차단 발신자 -----
    if text.startswith("/block "):
        email = text[7:].strip().lower()
        if "@" not in email or " " in email:
            return t("block_invalid", email=email), False
        blocked = _read_blocked()
        if email in blocked:
            return t("block_exists", email=email), False
        blocked.append(email)
        _write_blocked(blocked)
        return t("block_added", email=email, count=len(blocked)), True

    if text.startswith("/unblock "):
        email = text[9:].strip().lower()
        blocked = _read_blocked()
        if email not in blocked:
            return t("unblock_not_found", email=email), False
        blocked.remove(email)
        _write_blocked(blocked)
        return t("unblock_success", email=email, count=len(blocked)), True

    return t("unknown_command", text=text), False


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
        raw = msg.get("text", "").strip()
        normalized = _normalize(raw)
        if not normalized:
            continue

        reply, changed = _handle(normalized)
        _send(reply, chat_id)
        if changed:
            file_changed = True
        print(f"  📨 명령 처리: {raw!r}  →  {normalized}")

    _write_offset(last_id)
    return file_changed
