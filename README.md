# 📬 Mail Notifier

> **Gmail에서 면접 · 합격여부 · 중요 발신자 메일만 골라 Telegram으로 즉시 알림**
>
> AI-powered Gmail filter that classifies incoming mail and pushes only the important ones to Telegram, running 24/7 on free GitHub Actions cron.

> ⏱ **동작 시점 안내**: 본 시스템은 GitHub Actions cron(10분 주기)으로 동작합니다. 메일 알림과 봇 명령(`/add`, `/watch` 등)은 다음 cron 발화 시 처리되므로 **최대 10분 지연**될 수 있습니다. 실시간(1~5초) 알림은 Cloudflare Workers webhook 또는 Cloud Run + Gmail Pub/Sub로 확장 가능 — [Roadmap](#-limitations--roadmap) 참조.

![Version](https://img.shields.io/badge/version-1.1.0-blue)
![i18n](https://img.shields.io/badge/i18n-ko%20%7C%20en-yellow)
![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![Gemini](https://img.shields.io/badge/Gemini-2.5%20Flash-4285F4?logo=google&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)
![Cost](https://img.shields.io/badge/Cost-%240%2Fmonth-brightgreen)

---

## 🎯 Why

면접 결과나 합격 통보 같은 "놓치면 안 되는" 메일을 광고·공지 사이에 묻혀 늦게 보는 일을 없애려고 만들었습니다.

기존 Gmail 자체 필터로는 "면접" 키워드가 들어간 광고/이벤트 메일까지 잡혀버려서, **메일 본문 맥락을 이해하는 LLM 기반 분류기**가 필요했습니다.

## ✨ Features

- 🧠 **AI 분류** — Google Gemini가 메일을 `면접` / `합격여부` / `중요인물` / `무관` 4-class로 라벨링
- 🔇 **노이즈 차단** — 학교 공지, 광고, 영수증, 뉴스레터는 자동 무시
- ⏰ **24/7 무료 운영** — GitHub Actions cron 10분 주기 (PC가 꺼져있어도 동작)
- 🔐 **Secrets 분리** — 모든 토큰·credentials는 GitHub Secrets에 암호화 저장
- 🎚 **개인화 가능** — `senders.txt`에 중요 인물(교수님, 면접관 등) 등록 시 해당 발신자 메일도 알림 대상
- 📱 **Telegram 양방향** — 알림 받는 그 봇에게 `/add EMAIL`, `/list`, `/remove EMAIL` 명령으로 폰에서 직접 발신자 관리
- 🌐 **i18n (한국어 / English)** — `lang en` / `lang ko`로 봇 UI·알림·분류기 reasoning 언어 전환

## 🏗 Architecture

```
                    ┌──────────────────────────┐
                    │  GitHub Actions (10분 cron)│
                    └────────────┬─────────────┘
                                 ▼
                  ┌───────────────────────────────┐
                  │           main.py             │
                  │   (오케스트레이터, 새 메일만 처리) │
                  └───────────────────────────────┘
                          │            │            │
            ┌─────────────┘            │            └──────────────┐
            ▼                          ▼                            ▼
   ┌─────────────────┐      ┌─────────────────────┐      ┌────────────────┐
   │   Gmail API     │      │   Gemini 2.5 Flash  │      │  Telegram Bot  │
   │  (read-only)    │ ───▶ │      Lite           │ ───▶ │   (알림 발송)    │
   │                 │      │  (4-class 분류)      │      │                │
   └─────────────────┘      └─────────────────────┘      └────────────────┘
```

`last_seen_id.txt`로 중복 알림 방지. 새 메일 처리 후 Actions가 자동 commit & push로 상태 보존.

## 🛠 Tech Stack

| 영역 | 기술 |
|---|---|
| 언어 | Python 3.12 |
| LLM | **Google Gemini 2.5 Flash Lite** (free tier) — 한국어 분류 정확도 높음 |
| 메일 인입 | **Gmail API** v1 (`gmail.readonly` scope) |
| 알림 | **Telegram Bot API** |
| 자동화 | **GitHub Actions** cron + Secrets |
| 인증 | OAuth2 Installed App flow (refresh token 자동 갱신) |

## 📁 Project Structure

```
mail-notifier/
├── auth_gmail.py            # Gmail OAuth 인증 + Service 객체 생성
├── classify.py              # Gemini 호출 → 4-class 분류 결과 반환
├── send_telegram.py         # Telegram sendMessage API 래퍼
├── telegram_commands.py     # 봇 양방향 명령 처리 (/list, /add, /remove, /status)
├── main.py                  # entry point: fetch → classify → notify → 명령 처리
├── senders.txt              # 중요 발신자 목록 (봇이 자동 갱신)
├── last_seen_id.txt         # 마지막으로 처리한 메일 ID (자동 갱신)
├── telegram_offset.txt      # 마지막으로 처리한 Telegram update ID (자동 갱신)
├── requirements.txt
├── .env.example             # 환경 변수 템플릿
├── .gitignore
├── LICENSE
└── .github/workflows/
    └── check-mail.yml       # 10분 cron 워크플로우
```

## 🚀 Setup

### 1. Prerequisites

- Python 3.12+
- Google 계정 (Gmail 추적 대상)
- Telegram 계정

### 2. GCP — Gmail API 발급

1. [GCP Console](https://console.cloud.google.com)에서 새 프로젝트 생성
2. **APIs & Services → Library** → "Gmail API" Enable
3. **OAuth consent screen** → External 선택 → Test users에 본인 이메일 추가
4. **Credentials → Create Credentials → OAuth Client ID** → 타입 **Desktop app** → JSON 다운로드 → `credentials.json`로 저장

### 3. Telegram Bot 생성

```
@BotFather  →  /newbot  →  토큰 받기
봇과 대화 시작 후:
curl https://api.telegram.org/bot<TOKEN>/getUpdates  →  chat.id 추출
```

### 4. Gemini API Key

[Google AI Studio](https://aistudio.google.com/apikey) → Create API key → 복사

### 5. 로컬 셋업

```bash
git clone https://github.com/Sweet-Butters/mail-notifier.git
cd mail-notifier
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# .env 파일에 TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, GEMINI_API_KEY 입력

python auth_gmail.py    # OAuth 동의 → token.json 생성
python main.py          # 첫 실행: baseline 설정 (알림 없음)
```

### 6. GitHub Actions 자동화

```bash
gh secret set GEMINI_API_KEY          --body "$YOUR_KEY"
gh secret set TELEGRAM_TOKEN          --body "$YOUR_TOKEN"
gh secret set TELEGRAM_CHAT_ID        --body "$YOUR_CHAT_ID"
gh secret set GOOGLE_CREDENTIALS_JSON < credentials.json
gh secret set GOOGLE_TOKEN_JSON       < token.json

gh workflow run check-mail.yml   # 즉시 첫 실행
```

이후 10분마다 자동 실행. Actions 탭에서 실행 기록 확인 가능.

## 🤖 Bot Commands (Telegram에서)

알림 받는 봇에게 메시지로 명령 전송. 다음 cron 실행(최대 10분) 시 처리되어 봇이 응답 + repo에 자동 commit.

| 명령 | 동작 |
|---|---|
| `/list` | 현재 중요 발신자 목록 보기 |
| `/add EMAIL` | 발신자 추가 (예: `/add hr@somecorp.com`) |
| `/remove EMAIL` | 발신자 제거 |
| `/status` | 시스템 상태 (발신자 수, 모델, repo 링크) |
| `/help` | 명령어 목록 |

> **중요 발신자 추가 방법**: 폰의 Telegram 봇에 `/add EMAIL` 한 줄. 또는 로컬에서 `senders.txt` 직접 편집 후 push. 둘 다 가능.

## 📊 Cost Breakdown

| 항목 | 사용량 (10분 cron 기준) | 무료 한도 | 비용 |
|---|---|---|---|
| GitHub Actions (private) | ~1,440분/월 | 2,000분/월 | $0 |
| Gemini 2.5 Flash Lite | ~메일 30개/일 | ~15,000 요청/일 | $0 |
| Gmail API | 폴링 144회/일 | 1,000,000,000 quota units/일 | $0 |
| Telegram Bot | 메시지 ~5건/일 | 무제한 | $0 |
| **합계** | | | **$0/월** |

## 🔒 Security

- 모든 비밀 정보(`.env`, `credentials.json`, `token.json`)는 `.gitignore`로 차단되어 repo에 들어가지 않음
- GitHub Secrets는 암호화되어 저장되고 워크플로우 로그에서도 `***`로 마스킹
- Gmail scope는 `gmail.readonly`만 요청 — 메일 수정·삭제·발송 불가
- 워크플로우의 commit 권한은 `last_seen_id.txt` 갱신 용도로만 사용

## 🚧 Limitations & Roadmap

| 현재 한계 | 해결 방향 |
|---|---|
| 알림까지 평균 10~12분 지연 | Gmail Pub/Sub `users.watch` + Cloud Run으로 실시간(1~5초)화 |
| 분류 프롬프트 fixed | 사용자 오답 피드백 기반 in-context tuning |
| 단일 Gmail 계정만 추적 | 다중 계정 지원 (token 별도 관리) |
| 발신자 화이트리스트만 지원 | 키워드·도메인·정규식 룰 추가 |

## 📝 Implementation Notes

- **분류 프롬프트 (`classify.py`)** — "키워드만으로 판단하지 말 것" + "애매하면 무관으로" 두 룰을 명시해 노이즈를 능동적으로 떨궈냄. Gemini의 `response_mime_type="application/json"`으로 출력 형식 강제, 잘못된 카테고리는 안전망에서 `무관`으로 fallback.
- **상태 관리 (`main.py`)** — 첫 실행 시 알림 없이 baseline만 잡아 "과거 받은편지함 전체에 알림 폭탄" 사고 방지.
- **OAuth 처리 (`auth_gmail.py`)** — WSL2 환경 제약 때문에 `run_local_server`의 자동 브라우저 오픈을 끄고 콘솔에 URL 출력 → 사용자가 Windows 브라우저에서 인증하는 헤드리스 플로우.

## 📋 Changelog

버전별 변경 사항은 [CHANGELOG.md](CHANGELOG.md) 참조.

## 📄 License

MIT — 자유롭게 fork/수정 가능. 자세한 내용은 [LICENSE](LICENSE) 참조.

---

<sub>Built by [@Sweet-Butters](https://github.com/Sweet-Butters)</sub>
