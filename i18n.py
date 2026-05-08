"""다국어 메시지 모음 / Bilingual i18n strings.

봇 응답·알림·분류기 출력 언어를 전환합니다. 새 언어는 STRINGS dict에 추가하면 됨.
"""

from __future__ import annotations

from pathlib import Path

LANG_FILE = Path("language.txt")
DEFAULT_LANG = "ko"
SUPPORTED_LANGS = {"ko", "en"}


def get_lang() -> str:
    if not LANG_FILE.exists():
        return DEFAULT_LANG
    lang = LANG_FILE.read_text().strip().lower()
    return lang if lang in SUPPORTED_LANGS else DEFAULT_LANG


def set_lang(lang: str) -> bool:
    if lang not in SUPPORTED_LANGS:
        return False
    LANG_FILE.write_text(lang + "\n")
    return True


def t(key: str, **kwargs) -> str:
    lang = get_lang()
    template = STRINGS.get(lang, {}).get(key)
    if template is None:
        template = STRINGS[DEFAULT_LANG].get(key, f"[missing:{key}]")
    return template.format(**kwargs) if kwargs else template


STRINGS: dict[str, dict[str, str]] = {
    # ───────────────────────────── 한국어 ─────────────────────────────
    "ko": {
        "help": """🤖 <b>명령어</b> (슬래시 <code>/</code> 생략 가능)

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
<code>lang ko|en</code> — 언어 전환 (현재: 한국어)
<code>help</code> — 이 메뉴

<i>변경 사항은 다음 cron 실행(최대 10분)에 반영됩니다.</i>""",

        # /list
        "list_header": "📋 <b>현재 추적 설정</b>",
        "list_senders": "<b>👤 중요 발신자 ({count})</b>",
        "list_watching": "<b>👀 기다리는 메일 ({count})</b>",
        "list_blocked": "<b>🚫 차단 발신자 ({count})</b>",
        "list_empty": "  <i>(없음)</i>",

        # /status
        "status_message": (
            "📊 <b>시스템 상태</b>\n"
            "  중요 발신자: <b>{senders}개</b>\n"
            "  기다리는 메일: <b>{watching}개</b>\n"
            "  차단 발신자: <b>{blocked}개</b>\n"
            "  cron 주기: <b>10분</b>\n"
            "  분류 모델: Gemini 2.5 Flash\n"
            "  언어: <b>{lang}</b>\n"
            "  Repo: <a href=\"https://github.com/Sweet-Butters/mail-notifier\">Sweet-Butters/mail-notifier</a>"
        ),

        # /lang
        "lang_current": "🌐 현재 언어: <b>{lang}</b>\n\n사용법: <code>lang ko</code> 또는 <code>lang en</code>",
        "lang_invalid": "⚠️ 지원하지 않는 언어: <code>{lang}</code>\n사용 가능: <code>ko</code>, <code>en</code>",
        "lang_changed": "✅ 언어 변경: <b>{lang}</b>\n다음 응답부터 적용됩니다.",

        # /add /remove
        "add_invalid": "⚠️ 이메일 형식이 아닙니다: <code>{email}</code>",
        "add_exists": "ℹ️ 이미 등록된 발신자: <code>{email}</code>",
        "add_success": "✅ 발신자 추가: <code>{email}</code>\n현재 총 <b>{count}개</b>",
        "remove_not_found": "ℹ️ 등록되지 않은 발신자: <code>{email}</code>",
        "remove_success": "🗑 발신자 제거: <code>{email}</code>\n현재 총 <b>{count}개</b>",

        # /watch /unwatch
        "watch_usage": "⚠️ 사용법: <code>watch 기다리는 메일 설명</code>",
        "watch_too_long": "⚠️ 너무 깁니다 ({length}자, 최대 {max_length}자)",
        "watch_exists": "ℹ️ 이미 등록됨: <i>{desc}</i>",
        "watch_added": "✅ #{n} 추가: <i>{desc}</i>\n현재 총 <b>{count}개</b>",
        "unwatch_empty": "ℹ️ 등록된 항목이 없습니다.",
        "unwatch_index_invalid": "⚠️ #{n} 없음 (현재 1~{max})",
        "unwatch_by_index": "🗑 #{n} 제거: <i>{desc}</i>\n현재 총 <b>{count}개</b>",
        "unwatch_by_text": "🗑 제거: <i>{desc}</i>\n현재 총 <b>{count}개</b>",
        "unwatch_not_found": "ℹ️ 매칭되는 항목 없음. <code>list</code>로 #번호 확인하세요.",

        # /block /unblock
        "block_invalid": "⚠️ 이메일 형식이 아닙니다: <code>{email}</code>",
        "block_exists": "ℹ️ 이미 차단됨: <code>{email}</code>",
        "block_added": (
            "🚫 차단 추가: <code>{email}</code>\n"
            "이 발신자의 메일은 분류기 호출 없이 즉시 무시됩니다.\n"
            "현재 총 <b>{count}개</b>"
        ),
        "unblock_not_found": "ℹ️ 차단 목록에 없음: <code>{email}</code>",
        "unblock_success": "♻️ 차단 해제: <code>{email}</code>\n현재 총 <b>{count}개</b>",

        # /quota
        "quota_message": (
            "📈 <b>Gemini 사용량 (UTC 오늘)</b>\n"
            "  <code>{bar}</code>  {pct:.0f}%\n"
            "  사용: <b>{used}</b>회 / 한도: ~<b>{limit}</b>회\n"
            "  남은 추정: <b>{remaining}</b>회\n"
            "  <i>(UTC 00:00 자동 리셋)</i>"
        ),
        "quota_alert": (
            "⚠️ <b>Gemini API 한도 도달</b>\n\n"
            "{status}\n\n"
            "남은 메일은 다음 cron에서 재시도됩니다. UTC 00:00에 자동 리셋."
        ),

        # Mail alert
        "alert_judgment": "판단: {reason}",
        "alert_block_hint": "잘못 잡혔으면 발신자 차단:",

        # Errors
        "unknown_command": "❓ 모르는 명령: <code>{text}</code>\n\n<code>help</code> 로 도움말 확인",

        # Classifier prompt language directive
        "classifier_lang_directive": "reasoning은 한국어 한 문장으로 작성하세요.",
    },

    # ───────────────────────────── English ─────────────────────────────
    "en": {
        "help": """🤖 <b>Commands</b> (slash <code>/</code> optional)

<b>Important Senders</b>
<code>add EMAIL</code> — add
<code>remove EMAIL</code> — remove

<b>Watch List</b> (expected mail keywords)
<code>watch DESCRIPTION</code> — add (e.g. <code>watch CompanyX intern offer</code>)
<code>unwatch N</code> — remove (by #index or exact text)

<b>Blocked Senders</b>
<code>block EMAIL</code> — block
<code>unblock EMAIL</code> — unblock

<b>Info</b>
<code>list</code> — all settings
<code>status</code> — system status
<code>quota</code> — Gemini usage
<code>lang ko|en</code> — switch language (current: English)
<code>help</code> — this menu

<i>Changes apply on the next cron run (within 10 min).</i>""",

        # /list
        "list_header": "📋 <b>Current Tracking</b>",
        "list_senders": "<b>👤 Important Senders ({count})</b>",
        "list_watching": "<b>👀 Watch List ({count})</b>",
        "list_blocked": "<b>🚫 Blocked Senders ({count})</b>",
        "list_empty": "  <i>(none)</i>",

        # /status
        "status_message": (
            "📊 <b>System Status</b>\n"
            "  Important senders: <b>{senders}</b>\n"
            "  Watch list: <b>{watching}</b>\n"
            "  Blocked senders: <b>{blocked}</b>\n"
            "  Cron interval: <b>10 min</b>\n"
            "  Classifier: Gemini 2.5 Flash\n"
            "  Language: <b>{lang}</b>\n"
            "  Repo: <a href=\"https://github.com/Sweet-Butters/mail-notifier\">Sweet-Butters/mail-notifier</a>"
        ),

        # /lang
        "lang_current": "🌐 Current language: <b>{lang}</b>\n\nUsage: <code>lang ko</code> or <code>lang en</code>",
        "lang_invalid": "⚠️ Unsupported language: <code>{lang}</code>\nAvailable: <code>ko</code>, <code>en</code>",
        "lang_changed": "✅ Language changed to: <b>{lang}</b>\nApplies from next response.",

        # /add /remove
        "add_invalid": "⚠️ Not a valid email: <code>{email}</code>",
        "add_exists": "ℹ️ Already registered: <code>{email}</code>",
        "add_success": "✅ Sender added: <code>{email}</code>\nTotal: <b>{count}</b>",
        "remove_not_found": "ℹ️ Sender not found: <code>{email}</code>",
        "remove_success": "🗑 Sender removed: <code>{email}</code>\nTotal: <b>{count}</b>",

        # /watch /unwatch
        "watch_usage": "⚠️ Usage: <code>watch DESCRIPTION OF EXPECTED MAIL</code>",
        "watch_too_long": "⚠️ Too long ({length} chars, max {max_length})",
        "watch_exists": "ℹ️ Already exists: <i>{desc}</i>",
        "watch_added": "✅ #{n} added: <i>{desc}</i>\nTotal: <b>{count}</b>",
        "unwatch_empty": "ℹ️ No items registered.",
        "unwatch_index_invalid": "⚠️ #{n} not found (current 1~{max})",
        "unwatch_by_index": "🗑 #{n} removed: <i>{desc}</i>\nTotal: <b>{count}</b>",
        "unwatch_by_text": "🗑 Removed: <i>{desc}</i>\nTotal: <b>{count}</b>",
        "unwatch_not_found": "ℹ️ No matching item. Use <code>list</code> to check #index.",

        # /block /unblock
        "block_invalid": "⚠️ Not a valid email: <code>{email}</code>",
        "block_exists": "ℹ️ Already blocked: <code>{email}</code>",
        "block_added": (
            "🚫 Blocked: <code>{email}</code>\n"
            "Mail from this sender will be skipped (no classifier call).\n"
            "Total: <b>{count}</b>"
        ),
        "unblock_not_found": "ℹ️ Not in block list: <code>{email}</code>",
        "unblock_success": "♻️ Unblocked: <code>{email}</code>\nTotal: <b>{count}</b>",

        # /quota
        "quota_message": (
            "📈 <b>Gemini Usage (today UTC)</b>\n"
            "  <code>{bar}</code>  {pct:.0f}%\n"
            "  Used: <b>{used}</b> / Limit: ~<b>{limit}</b>\n"
            "  Estimated remaining: <b>{remaining}</b>\n"
            "  <i>(auto-reset at UTC 00:00)</i>"
        ),
        "quota_alert": (
            "⚠️ <b>Gemini API Quota Reached</b>\n\n"
            "{status}\n\n"
            "Remaining mail will be retried on the next cron. Auto-resets at UTC 00:00."
        ),

        # Mail alert
        "alert_judgment": "Why: {reason}",
        "alert_block_hint": "If wrong, block sender:",

        # Errors
        "unknown_command": "❓ Unknown command: <code>{text}</code>\n\nUse <code>help</code> to see available commands",

        # Classifier prompt language directive
        "classifier_lang_directive": "Write reasoning as one short English sentence.",
    },
}
