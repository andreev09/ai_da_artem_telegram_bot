````instructions
### Quick orientation — Telegram Flask webhook (this repo)

Всегда отвечай на русском языке.
Ты - экспрет по сервису pythonanywhere.com, Flask и Telegram Bot API.

Short: this is a tiny Flask-based Telegram webhook bot intended to run behind a TLS endpoint. Handlers return Telegram API payloads as dicts which the Flask endpoint returns as JSON (so no separate API call is required).

Architecture & main components
- `app.py` / `main.py` — HTTP entrypoints. Both expose `/webhook` (POST) and `/` (GET health). `main.py` delegates to `webhook_handlers.TelegramWebhookHandler`; `app.py` contains a minimal inline handler useful for quick local testing.
- `webhook_handlers.py` — core update parsing and business logic. Key method: `TelegramWebhookHandler.handle_update(update: dict)` — returns a Telegram API payload dict (e.g. `{"method":"sendMessage", "chat_id":..., "text":...}`). Persistence of authorized contacts is handled by `_persist_contact_data` which appends newline-delimited JSON to `authorized_contacts.jsonl`.
- `webhook_setup.py` — CLI helper to call Telegram `setWebhook` (reads `secrets/tokens.env` or `TELEGRAM_BOT_TOKEN` environment variable). Uses `requests` and supports custom CA bundle / disabling verification for environments like local tunnels.

Why this layout
- Simplicity and inspectability: each file is deliberately small and explicit. Webhook logic returns payloads instead of sending requests so tests can assert returned dicts without network calls.

Developer workflows (quick commands)
- Install dependencies:

```bash
python3 -m pip install -r requirements.txt
```

- Run server locally (two options):

```bash
FLASK_APP=app.py flask run --host=0.0.0.0 --port=8000
# or
python3 main.py
```

- Set webhook from CLI helper (reads `secrets/tokens.env` or `TELEGRAM_BOT_TOKEN`):

```bash
python3 webhook_setup.py --webhook-url "https://example.com/webhook" --secret-token "your-secret"
```

Project-specific conventions (important for AI agents)
- Secrets: `secrets/tokens.env` is the canonical place for `TELEGRAM_BOT_TOKEN` (format KEY=VALUE). The loader `_load_env_from_file()` in `webhook_setup.py` calls `os.environ.setdefault` — prefer writing to that file rather than editing code.
- Response shape: Handlers must return a Telegram API payload dict (method + args). Example: `{"method":"sendMessage","chat_id":12345,"text":"Привет"}`. The Flask controller will `jsonify` and return HTTP 200.
- Contact storage: `authorized_contacts.jsonl` is append-only newline-delimited JSON. Tests should treat it as append-only and can create temporary copies when asserting persistence.
- No external DB: persistence is file-based and intentionally minimal.

Testing and autofix guidance
- There are no tests besides `tests/test_texts.py`. When adding tests, prefer unit tests that call `TelegramWebhookHandler.handle_update` with sample update dicts and assert returned payloads and side-effects (file append). Mock network calls if needed.

Integration points & external dependencies
- Telegram Bot API: `webhook_setup.py` posts to `https://api.telegram.org/bot{token}/setWebhook`. The helper expects Telegram's `{ "ok": true }` response. Network errors raise `TelegramWebhookError`.
- Hosting: webhook must be reachable over HTTPS. The repo uses `WEBHOOK_URL` in `webhook_setup.py` as an example — do not hardcode production tokens or URLs in committed files.

Files to inspect when working on features
- `webhook_handlers.py` — main logic & return shapes
- `webhook_setup.py` — token loading and `setWebhook` CLI
- `app.py` / `main.py` — how handlers are wired to Flask routes
- `authorized_contacts.jsonl` — append-only contact store

Examples from the codebase
- Creating a reply payload (from `webhook_handlers.py`):

```py
return {"method": "sendMessage", "chat_id": chat_id, "text": "Привет"}
```

- Persisting a contact (append-only): implementation writes newline-delimited JSON; tests should create a temp file or mock filesystem.

Editing & PR guidance for AI agents
- Keep changes minimal and focused: this project favors small, single-file edits.
- Preserve the handler return-shape: if you change handler behavior, update or add unit tests asserting returned payloads.
- Do not commit tokens or secrets. Use `secrets/tokens.env` for local testing.

Edge cases AI should check when editing code
- Missing `TELEGRAM_BOT_TOKEN` (startup should exit with clear message) — `webhook_setup.py` already raises SystemExit.
- `authorized_contacts.jsonl` race conditions (append-only pattern); keep writes atomic where possible.
- `setWebhook` network errors and invalid JSON responses are wrapped in `TelegramWebhookError`.

If you need clarification
- Ask what webhook URL and secret token policy should be for new changes, and whether to unify `app.py` and `main.py` entrypoints.

---
Small, focused guidance — update this file if you add tests, CI, or change storage.



````
