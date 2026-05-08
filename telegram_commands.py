"""Telegram bot 명령어 처리 (양방향).

매 cron 실행 시 main.py에서 process_commands() 호출.
- 본인 chat_id에서 온 / 명령만 처리 (다른 사람 봇 발견해도 무시)
- senders.txt / watching.txt를 직접 편집 (workflow가 변경분을 자동 commit)
- 처리한 update_id는 telegram_offset.txt에 저장해서 중복 처리 방지
"""

from __future__ import annotations

import os
from pathlib import Path

import requests
from dotenv import load_dotenv

import quota

load_dotenv()

SENDERS_FILE = Path("senders.txt")
WATCHING_FILE = Path("watching.txt")
BLOCKED_FILE = Path("blocked_senders.txt")
OFFSET_FILE = Path("telegram_offset.txt")

API = f"https://api.telegram.org/bot{os.environ.get('TELEGRAM_TOKEN', '')}"

HELP = """🤖 <b>명령어</b> (슬래시 <code>/</code> 생략 가능)

<b>중요 발신자</b>
<code>add EMAIL</code> — 추가
<code>remove EMAIL</code> — 제거

<b>기다리는 메일</b>
<code>watch DESCRIPTION</code> — 추가 (예: <code>watch 회사X 인턴 합격 안내</code>)
<code>unwatch N</code> — 제거 (#번호 또는 정확한 텍스트)

<b>차단 발신자</b>
<code>block EMAIL</code> — 차단
<code>unblock EMAIL</code> — 해제

<b>조회</b>
<code>list</code> — 모든 설정
<code>status</code> — 시스템 상태
<code>quota</code> — Gemini 사용량
<code>help</code> — 이 메뉴

<i>변경 사항은 다음 cron 실행(최대 10분)에 반영됩니다.</i>"""

KNOWN_COMMANDS = {
    "add", "remove", "watch", "unwatch", "block", "unblock",
    "list", "status", "help", "start", "quota",
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
    "# 현재 기다리는 메일 항목 (한 줄에 하나)\n"
    "# Bot이 /watch로 추가, /unwatch로 삭제\n"
    "# 분류기가 이 내용/키워드를 적극적으로 매칭하여 면접/합격여부로 분류함\n"
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
    "# 차단된 발신자 목록 (이 주소에서 오는 메일은 분류기 호출 없이 무시)\n"
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
        return HELP, False

    if text == "/quota":
        return quota.status_text(), False

    # ----- 통합 조회 -----
    if text == "/list":
        emails = _parsed_emails(_read_senders_lines())
        watch = _read_watching()
        blocked = _read_blocked()
        out = []
        out.append(f"📋 <b>현재 추적 설정</b>\n")
        out.append(f"<b>👤 중요 발신자 ({len(emails)})</b>")
        if emails:
            out.extend(f"  • <code>{e}</code>" for e in emails)
        else:
            out.append("  <i>(없음)</i>")
        out.append("")
        out.append(f"<b>👀 기다리는 메일 ({len(watch)})</b>")
        if watch:
            out.extend(f"  #{i+1}. {w}" for i, w in enumerate(watch))
        else:
            out.append("  <i>(없음)</i>")
        out.append("")
        out.append(f"<b>🚫 차단 발신자 ({len(blocked)})</b>")
        if blocked:
            out.extend(f"  • <code>{e}</code>" for e in blocked)
        else:
            out.append("  <i>(없음)</i>")
        return "\n".join(out), False

    if text == "/status":
        emails = _parsed_emails(_read_senders_lines())
        watch = _read_watching()
        blocked = _read_blocked()
        return (
            f"📊 <b>시스템 상태</b>\n"
            f"  중요 발신자: <b>{len(emails)}개</b>\n"
            f"  기다리는 메일: <b>{len(watch)}개</b>\n"
            f"  차단 발신자: <b>{len(blocked)}개</b>\n"
            f"  cron 주기: <b>10분</b>\n"
            f"  분류 모델: Gemini 2.5 Flash Lite\n"
            f"  Repo: <a href=\"https://github.com/Sweet-Butters/mail-notifier\">Sweet-Butters/mail-notifier</a>"
        ), False

    # ----- 발신자 -----
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
        return f"✅ 발신자 추가: <code>{email}</code>\n현재 총 <b>{len(emails)}개</b>", True

    if text.startswith("/remove "):
        email = text[8:].strip()
        lines = _read_senders_lines()
        new_lines = [line for line in lines if _email_from_line(line) != email]
        if len(new_lines) == len(lines):
            return f"ℹ️ 등록되지 않은 발신자: <code>{email}</code>", False
        _write_senders_lines(new_lines)
        emails = _parsed_emails(new_lines)
        return f"🗑 발신자 제거: <code>{email}</code>\n현재 총 <b>{len(emails)}개</b>", True

    # ----- 기다리는 메일 -----
    if text.startswith("/watch "):
        desc = text[7:].strip()
        if not desc:
            return "⚠️ 사용법: <code>/watch 기다리는 메일 설명</code>", False
        if len(desc) > 300:
            return f"⚠️ 너무 깁니다 ({len(desc)}자, 최대 300자)", False
        watch = _read_watching()
        if desc in watch:
            return f"ℹ️ 이미 등록됨: <i>{desc}</i>", False
        watch.append(desc)
        _write_watching(watch)
        return f"✅ #{len(watch)} 추가: <i>{desc}</i>\n현재 총 <b>{len(watch)}개</b>", True

    if text.startswith("/unwatch "):
        arg = text[9:].strip()
        watch = _read_watching()
        if not watch:
            return "ℹ️ 등록된 항목이 없습니다.", False
        # 1) 숫자 #N
        if arg.isdigit():
            idx = int(arg) - 1
            if 0 <= idx < len(watch):
                removed = watch.pop(idx)
                _write_watching(watch)
                return f"🗑 #{idx+1} 제거: <i>{removed}</i>\n현재 총 <b>{len(watch)}개</b>", True
            return f"⚠️ #{arg} 없음 (현재 1~{len(watch)})", False
        # 2) 정확한 텍스트
        if arg in watch:
            watch.remove(arg)
            _write_watching(watch)
            return f"🗑 제거: <i>{arg}</i>\n현재 총 <b>{len(watch)}개</b>", True
        return f"ℹ️ 매칭되는 항목 없음. <code>/list</code>로 #번호 확인하세요.", False

    # ----- 차단 발신자 -----
    if text.startswith("/block "):
        email = text[7:].strip().lower()
        if "@" not in email or " " in email:
            return f"⚠️ 이메일 형식이 아닙니다: <code>{email}</code>", False
        blocked = _read_blocked()
        if email in blocked:
            return f"ℹ️ 이미 차단됨: <code>{email}</code>", False
        blocked.append(email)
        _write_blocked(blocked)
        return f"🚫 차단 추가: <code>{email}</code>\n이 발신자의 메일은 분류기 호출 없이 즉시 무시됩니다.\n현재 총 <b>{len(blocked)}개</b>", True

    if text.startswith("/unblock "):
        email = text[9:].strip().lower()
        blocked = _read_blocked()
        if email not in blocked:
            return f"ℹ️ 차단 목록에 없음: <code>{email}</code>", False
        blocked.remove(email)
        _write_blocked(blocked)
        return f"♻️ 차단 해제: <code>{email}</code>\n현재 총 <b>{len(blocked)}개</b>", True

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
