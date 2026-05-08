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

## Cloud Run + Pub/Sub deploy (fast version, mail_fast/)
- `gcloud run deploy --source=.` hangs without `--quiet` (interactive Y/n prompt)
- Token JSON env: use `--env-vars-file=YAML` (not `--set-env-vars` — chokes on commas/colons in JSON)
- New GCP projects need these IAM roles on Compute SA before source deploy: `roles/cloudbuild.builds.builder`, `roles/storage.objectAdmin`, `roles/artifactregistry.writer`, `roles/logging.logWriter`
- `gcloud components install X` needs `--quiet` (else interactive prompt hangs background tasks)

## Cross-project Gmail Pub/Sub
- Gmail `users.watch(topicName=...)` requires the Pub/Sub topic to be in the **same GCP project as the OAuth client** — not the user's mail-account project
- Workaround if billing blocked on owner project: create new OAuth client in a project-with-billing, user re-consents → new token.json that can reference cross-project Gmail mailbox

## OAuth flow on WSL2 (manual code exchange when localhost callback unreliable)
- PKCE requires `state` + `code_verifier` consistent across two invocations — persist via JSON to /tmp (pickle fails on OAuth2Session lambdas)
- Set `OAUTHLIB_INSECURE_TRANSPORT=1` env var to allow http://localhost in oauthlib
- Have user paste redirect URL from "site can't be reached" page; INCOGNITO browser avoids state-cache mismatches between attempts

## GCS-backed state for Cloud Run (ephemeral compute)
- Direct GCS edit (bypass bot, useful for bulk updates): `gcloud storage cp local.txt gs://bucket/path`
- Read: `gcloud storage cat gs://bucket/path`
- Cloud Run containers are ephemeral — never write state to local disk

## Cloud Scheduler for auto-renewal
- Idempotent endpoint + daily call = robust pattern (vs weekly with no buffer)
- Free tier: 3 jobs per billing account
- For Gmail watch (7-day expiration): daily call gives 6+ days buffer

## GCP Monitoring vs Telegram for alerting
- GCP Monitoring overcomplicated: new resource metrics take 10-15 min to register, `documentation` requires both `content` AND `mimeType`
- Simpler pattern we use: have endpoint Telegram on failure (e.g., `/renew-watch` does this)
- SMS notification channel mostly US/CA only — not useful for KR phone numbers

## Multi-account GCS path scheme (mail_fast/)
- `accounts.txt` — registry of registered emails
- `accounts/<email>/{senders,watching,blocked,token,last_history_id}.txt`
- `aliases.json` — short alias → full email mapping
- `onboarding/<email>.json` — transient OAuth state (state + code_verifier) between `acc add` and `acc confirm`
- Global: `language.txt`, `quota.json`

## 2-step OAuth bot flow
- `acc add EMAIL` → bot generates URL + saves state/code_verifier to GCS `onboarding/<email>.json`
- User opens URL, completes consent, copies redirect URL from "site can't be reached" page
- `acc confirm URL` → bot searches GCS `onboarding/*.json` by `state` query param to find matching email → fetch_token → save token to `accounts/<email>/token.json`
- Always set `OAUTHLIB_INSECURE_TRANSPORT=1` for `http://localhost` callback

## Sanitization checklist before public repo push
- `grep -rn -E "PII patterns" --exclude-dir=__pycache__ --exclude-dir=.venv`
- Common leaks: `*보안비번*` files (manual saves of credentials), institution emails in examples, specific event names
- `.gitignore` patterns to add: `*보안비번*`, `*client_secret*`, `*.pkl`
- Final verify: `git ls-files | grep -E "secret|cred|token"` after `git add -A`

## Cloud Run env-vars-file YAML for multi-line JSON
```yaml
GOOGLE_OAUTH_CLIENT_JSON: |
$(cat credentials.json | sed 's/^/  /')   # indent 2 spaces for YAML literal block
```
Use `--env-vars-file=YAML` instead of `--set-env-vars` when value contains `,` or `:`.

## Test bot commands without phone (webhook simulation)
```bash
curl -X POST $SERVICE_URL/telegram/$SECRET \
  -H "Content-Type: application/json" \
  -d "{\"update_id\":999,\"message\":{\"chat\":{\"id\":$CHAT_ID,\"type\":\"private\"},\"from\":{\"id\":$CHAT_ID},\"date\":1700000000,\"text\":\"acc confirm http://localhost:8080/?state=...\"}}"
```
