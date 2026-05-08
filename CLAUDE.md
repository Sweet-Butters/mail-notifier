# Mail Notifier — Claude context

## Architecture
- `./` slow version: GitHub Actions cron 10min + polling Telegram bot
- `./mail_fast/` fast version: Cloud Run + Pub/Sub + webhook bot (under construction)
- Repos: `Sweet-Butters/mail-notifier` (KR, cron active), `Sweet-Butters/mail-notifier_eng` (mirror, workflows disabled)

## State files mutated by bot (auto-committed by workflow)
`senders.txt` `watching.txt` `blocked_senders.txt` `language.txt` `last_seen_id.txt` `telegram_offset.txt` `quota.json` — running `classify()` or `tc._handle()` locally MUTATES them. Verify `git diff` before commit.

## WSL2 + OAuth
`run_local_server` browser auto-launch fails on WSL2. Use `open_browser=False` + print URL → user pastes in Windows browser; localhost callback works via port forwarding.

## Python on WSL Ubuntu 24
Stock python3 lacks pip/venv. `sudo apt install python3.12-venv python3-pip` before any venv work.

## Workflow auto-commit + git rebase
Workflow commits state every run → local `git pull --rebase` fails with "unstaged changes" if local also edited. Order: stage local → commit → pull --rebase → push. Tag-after-rebase requires delete + re-tag (else points to dead commit).

## gh CLI (v2.45) gotchas
- `gh repo edit --visibility public` — no `--accept-visibility-change-consequences` flag in this version
- `gh workflow disable` returns 403 if already disabled — state `disabled_manually` is success
- `gh repo create --remote=origin` fails if origin already exists from a clone — use `git remote set-url origin URL`

## Gemini free tier
- `gemini-2.0-flash` shows `limit: 0` on this project (moved off free tier)
- `gemini-2.5-flash` works but free-tier RPM cap is 5-10/min — smoke tests of >5 calls hit 429
- Billing enabled doesn't auto-promote to paid tier

## Telegram bot constraint
One bot uses polling OR webhook, not both. `@Gmailforme_bot` polls (slow version), `@mail_notifierBot` webhook (fast version).

## Force trigger workflow + view classification logs
```
gh workflow run check-mail.yml
RUN=$(gh run list --workflow=check-mail.yml --limit 1 --json databaseId -q '.[0].databaseId')
gh run view $RUN --log | grep -E "📨|✅|⏭|🔔|⚠️"
```
