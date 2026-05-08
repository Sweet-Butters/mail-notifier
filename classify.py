"""Gemini 2.0 Flash로 메일을 4가지 카테고리로 분류.

카테고리: 면접 / 합격여부 / 중요인물 / 무관
"무관"으로 분류된 메일은 main.py에서 알림 대상에서 제외된다.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

MODEL = "gemini-2.5-flash-lite"
SENDERS_FILE = "senders.txt"
WATCHING_FILE = "watching.txt"
CATEGORIES = ["면접", "합격여부", "중요인물", "무관"]

_client: genai.Client | None = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    return _client


def _parse_senders(raw: str) -> list[str]:
    return [
        line.strip()
        for line in raw.splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]


def _load_senders() -> list[str]:
    """senders.txt에서 발신자 목록 로드. 봇이 이 파일을 직접 편집하므로 단일 source of truth."""
    path = Path(SENDERS_FILE)
    if not path.exists():
        return []
    return _parse_senders(path.read_text(encoding="utf-8"))


def _load_watching() -> list[str]:
    """watching.txt에서 '기다리는 메일' 항목 로드. 분류기 프롬프트에 주입됨."""
    path = Path(WATCHING_FILE)
    if not path.exists():
        return []
    return _parse_senders(path.read_text(encoding="utf-8"))  # 같은 파싱 (주석/빈줄 제외)


def _system_prompt(senders: list[str], watching: list[str]) -> str:
    senders_block = "\n".join(f"- {s}" for s in senders) if senders else "(없음)"
    watching_block = "\n".join(f"- {w}" for w in watching) if watching else "(없음)"
    return f"""당신은 사용자가 놓치면 안 되는 중요한 이메일을 골라내는 분류기입니다.

다음 4가지 카테고리 중 정확히 하나를 고르세요:

- **면접**: 면접 일정 안내, 면접 결과 통보, 면접 전형 진행 안내. 회사/기관에서 사용자 본인에게 직접 보낸 면접 관련 메일.
- **합격여부**: 합격/불합격/선정/탈락 통보, 최종 결과 안내, 서류/필기/면접 전형 결과 메일. 프로그램(튜터/인턴/장학/공모전/연구원 등) 선정 결과나 오리엔테이션·OT 안내 메일도 포함.
- **중요인물**: 아래 목록의 발신자가 보낸 메일 (이메일 주소가 정확히 매칭되어야 함):
{senders_block}
- **무관**: 위 어디에도 해당하지 않는 모든 메일. 광고, 학교 공지(수강신청/장학금/도서관/시설 안내 등), 뉴스레터, 시스템 알림, 마케팅, 영수증, 자동발송 메일 등.

🎯 **사용자가 현재 기다리는 특정 메일** (이 내용·키워드와 직접 연관되면 우선적으로 면접/합격여부로 분류):
{watching_block}

판단 기준:
1. 발신자, 제목, 본문 모두를 보고 종합적으로 판단하세요.
2. "면접", "합격" 같은 키워드만 있다고 무조건 해당 카테고리가 아닙니다. 예: "면접 후기 공유 이벤트", "합격생 인터뷰 광고"는 "무관"입니다.
3. 학교/기관에서 단체 발송하는 공지(시설/도서관/장학/수강 안내 등)는 거의 항상 "무관"입니다.
4. 발신자 매칭은 `<email@domain>` 안의 이메일 주소를 보고 비교하세요. 단순 도메인 일치는 안 됩니다.
5. 위 "🎯 기다리는 메일" 항목과 매칭되는 메일은 적극적으로 적절 카테고리로 분류하고, reasoning에 어떤 watching 항목과 매칭되는지 명시하세요.
6. 위 어디에도 해당하지 않으면 "무관"으로 분류 — 노이즈 차단 우선.

응답은 반드시 다음 JSON 형식으로만 답변하세요 (다른 설명 없이):
{{"category": "<위 4개 중 하나>", "reasoning": "<한 문장 한국어 판단 근거>"}}"""


def classify(sender: str, subject: str, body: str) -> dict:
    """이메일 한 통을 분류.

    Returns:
        {"category": <CATEGORIES 중 하나>, "reasoning": <한 문장>}
    """
    senders = _load_senders()
    watching = _load_watching()
    user_msg = (
        f"[발신자] {sender}\n"
        f"[제목] {subject}\n"
        f"[본문 일부]\n{body[:1500]}"
    )

    response = _get_client().models.generate_content(
        model=MODEL,
        contents=user_msg,
        config=types.GenerateContentConfig(
            system_instruction=_system_prompt(senders, watching),
            response_mime_type="application/json",
            temperature=0.0,
        ),
    )

    result = json.loads(response.text)
    if result.get("category") not in CATEGORIES:
        # Gemini가 가끔 카테고리 외 라벨을 뱉으면 안전망: 무관 처리
        result = {
            "category": "무관",
            "reasoning": f"분류 실패 (받은 응답: {response.text[:100]})",
        }
    return result


if __name__ == "__main__":
    samples = [
        {
            "sender": '"채용팀" <hr@example.com>',
            "subject": "[example] 2차 면접 일정 안내드립니다",
            "body": "안녕하세요. 서류전형 합격을 축하드리며 2차 면접 일정을 아래와 같이 안내드립니다...",
        },
        {
            "sender": '"시설처 설비팀" <equipment@yonsei.ac.kr>',
            "subject": "2026학년도 하절기 냉방실시계획 안내",
            "body": "교내 냉방시설 가동을 다음과 같이 안내드립니다...",
        },
        {
            "sender": '"YISS" <summer@yonsei.ac.kr>',
            "subject": "2026 국제하계대학 수강안내",
            "body": "International Summer School 수강신청이 시작되었습니다...",
        },
    ]
    for s in samples:
        result = classify(**s)
        print(f"[{result['category']}] {s['subject']}")
        print(f"  → {result['reasoning']}\n")
