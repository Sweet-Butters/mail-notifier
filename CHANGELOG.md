# Changelog

이 프로젝트의 모든 주요 변경 사항을 기록합니다.

[Keep a Changelog](https://keepachangelog.com/ko/1.1.0/) 형식을 따르며, [Semantic Versioning](https://semver.org/lang/ko/)을 준수합니다.

---

## [1.1.0] — 2026-05-08

### Added
- 🌐 **i18n (한국어 / English) 지원** — Telegram bot UI, 알림 메시지, 분류기 reasoning 모두 다국어
  - 새 명령 `lang ko|en` — 폰에서 즉시 언어 전환
  - 기본값: `ko`. 영어 사용자는 `lang en` 한 번만 입력하면 모든 응답이 영어로
- 📁 `i18n.py` — 단일 source-of-truth 문자열 모듈, 새 언어 추가 쉬움
- 📁 `language.txt` — 현재 언어 저장 (자동 commit)

### Changed
- README badge: Version 1.0.0 → 1.1.0
- HELP 메시지에 `lang` 명령 추가
- `/status`에 현재 언어 표시

---

## [1.0.0] — 2026-05-08

첫 안정 릴리스. 폰에서 Telegram 봇만으로 모든 운영이 가능합니다.

### Added
- 🤖 **Telegram bot 양방향 명령 (9종)** — 폰에서 직접 발신자/키워드/차단 관리
  - `add` / `remove` — 중요 발신자 관리
  - `watch` / `unwatch` — 기다리는 메일 키워드 관리
  - `block` / `unblock` — 스팸 발신자 차단
  - `list` / `status` / `quota` — 조회
  - 슬래시(`/`) 생략 가능 (`add foo@bar.com`)
- 🚫 **차단 발신자 시스템** — `/block <email>` 1-tap 차단. 분류기 호출 없이 즉시 무시 → API 비용 절감
- 👀 **기다리는 메일 추적** — 키워드/내용 기반 LOOSE 매칭. 발신자 모를 때도 잡음
- 📈 **Quota 모니터링** — Gemini 일일 사용량 progress bar (`/quota`). 한도 도달 시 1회 자동 알림. UTC 자정 자동 리셋

### Changed
- ♻️ **분류 schema 단순화** — 4-class 카테고리 (`면접`/`합격여부`/`중요인물`/`무관`) → `notify` boolean + reasoning 한 문장
  - 사용자 입장에선 카테고리 라벨이 노이즈. 알림 받을지 말지가 본질
  - reasoning이 자연어로 trigger(발신자 / 키워드 / 패턴) 설명
- ⚡ **모델 업그레이드** — `gemini-2.5-flash-lite` → `gemini-2.5-flash`. RPM 한도 증가, 한국어 분류 정확도 향상
- 🎯 **Watching 매칭 LOOSE화** — 키워드 일부 일치만으로도 알림. 단, 광고/이벤트/리뷰 모집 맥락은 명시적 배제
- 📨 **알림 형식 정리** — `🔔 [제목] / From / 판단 / [본문] / /block 힌트`. 한 화면에 모든 결정 근거 가시화

### Fixed
- 🛡 **Quota 도달 시 부분 진행 보존** — 미처리 메일은 다음 cron에서 재시도 (중복 알림 방지). `last_seen_id`는 마지막 성공한 메일까지만 갱신
- 🔁 **알림 메시지 1-tap 차단** — 모든 알림에 `/block <email>` 자동 첨부 → 잘못 잡힌 발신자 즉시 영구 차단

### Security
- 모든 비밀 정보 (`credentials.json`, `token.json`, `.env`)는 `.gitignore` 차단 → repo에 절대 commit 안 됨
- GitHub Secrets에 5개 토큰 암호화 저장 (워크플로우 로그도 `***` 마스킹)
- Telegram bot은 등록된 본인 `chat_id`에서 온 명령만 처리

---

## [0.5.0] — 2026-05-07

### Added
- ⏰ **GitHub Actions 24/7 cron** — 10분 주기 자동 실행. PC가 꺼져있어도 동작
- 🔐 **GitHub Secrets 통합** — 토큰 5종을 암호화 저장. 코드에 하드코딩 0
- 💾 **상태 commit 자동화** — `last_seen_id.txt` 등 상태 파일을 워크플로우가 자동 갱신
- 🤖 **Telegram bot 1-way 명령** (이후 v1.0에서 양방향 확장)

### Changed
- Public repo 전환 + Topics 추가 → 검색 가능
- README, LICENSE (MIT) — 프로페셔널 문서화

---

## [0.4.0] — 2026-05-07

### Added
- 🧠 **Gemini 분류기 도입** — 4-class (`면접` / `합격여부` / `중요인물` / `무관`)
- 📋 **`senders.txt`** — 중요 발신자 목록 관리
- 🔇 **노이즈 차단** — 학교 공지, 광고, 영수증, 뉴스레터 자동 무시

### Changed
- 분류 모델: `Anthropic Claude` 검토 → `Google Gemini 2.5 Flash Lite`로 결정 (free tier, 한국어 품질 충분)

---

## [0.3.0] — 2026-05-07

### Added
- 📨 **Telegram bot 알림 발신** — 새 메일 감지 시 봇이 메시지 전송
- 📌 **중복 방지** — `last_seen_id.txt`로 처리한 메일 ID 추적
- ▶️ **수동 실행 모드** — `python main.py`로 즉시 체크

---

## [0.2.0] — 2026-05-07

### Added
- 🤖 **Telegram bot 생성 + 토큰 관리**
- 📞 `send_telegram.py` — sendMessage API 래퍼

---

## [0.1.0] — 2026-05-07

### Added
- 🎬 프로젝트 초기 셋업 (Python 3.12 + venv)
- 🔑 **Gmail OAuth** — Installed App flow, `gmail.readonly` scope
- 📥 **`auth_gmail.py`** — 받은편지함 최근 5개 메일 출력 검증

---

[1.1.0]: https://github.com/Sweet-Butters/mail-notifier/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/Sweet-Butters/mail-notifier/releases/tag/v1.0.0
[0.5.0]: https://github.com/Sweet-Butters/mail-notifier/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/Sweet-Butters/mail-notifier/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/Sweet-Butters/mail-notifier/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/Sweet-Butters/mail-notifier/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/Sweet-Butters/mail-notifier/releases/tag/v0.1.0
