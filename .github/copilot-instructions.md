### Quick orientation — Telegram Flask Webhook

This small repo is a Flask-based Telegram webhook bot. The primary pieces you need to know:

- `app.py` / `main.py` — Flask app exposing `/webhook` (POST) and `/` (GET health). `main.py` uses `webhook_handlers.TelegramWebhookHandler` while `app.py` contains a minimal inline handler.
- `webhook_handlers.py` — core logic for parsing incoming Telegram updates, handling `/start` and contact messages, persisting contacts to `authorized_contacts.jsonl` and returning Telegram API payloads (e.g. `{"method":"sendMessage", ...}`).
- `webhook_setup.py` — helper CLI utility to call Telegram's `setWebhook` method (reads token from `secrets/tokens.env` or `TELEGRAM_BOT_TOKEN` env var). Edit `WEBHOOK_URL` in that file or pass `--webhook-url` when running.
- `secrets/tokens.env` — project convention: a simple KEY=VALUE file. The loader `_load_env_from_file()` reads this and sets os.environ defaults. Required key: `TELEGRAM_BOT_TOKEN`. Optional: `TELEGRAM_WEBHOOK_SECRET_TOKEN`.

Why these choices
- The repo favors explicit, single-file clarity over frameworks. Webhook responses are returned as JSON matching Telegram's inline response convention (Flask returns a JSON doing the requested API call).

Developer workflows & commands
- Install deps:

```bash
python3 -m pip install -r requirements.txt
```

- Run the server locally for manual testing:

```bash
FLASK_APP=app.py flask run --host=0.0.0.0 --port=8000
# or
python3 main.py
```

- Set webhook with the helper (reads token from `secrets/tokens.env` or `TELEGRAM_BOT_TOKEN`):

```bash
python3 webhook_setup.py --webhook-url "https://aidaartem.eu.pythonanywhere.com/webhook" --secret-token "s3cr3t"
```

Project-specific conventions & patterns (for an AI agent)
- Token and secrets loader: `webhook_setup.py::_load_env_from_file(Path("secrets/tokens.env"))` — prefer using that file or `TELEGRAM_BOT_TOKEN` env var. Do not hard-code tokens in code.
- Webhook response shape: handlers return a dict with the Telegram method and parameters (e.g. `{"method":"sendMessage","chat_id":...,"text":...}`); controller wraps with `jsonify(...)` and 200.
- Contact persistence: `TelegramWebhookHandler._persist_contact_data` appends newline-delimited JSON to `authorized_contacts.jsonl` in project root. Treat it as append-only storage in tests.
- Tests & linting: none present. Add unit tests against `webhook_handlers.TelegramWebhookHandler.handle_update` for fast feedback.

Integration points
- Telegram Bot API: `webhook_setup.py` performs HTTPS POSTs to `https://api.telegram.org/bot{token}/setWebhook` and expects JSON `{"ok": true}` replies. Network errors are surfaced via `TelegramWebhookError`.
- Hosting: example domain used in code is `https://aidaartem.eu.pythonanywhere.com/webhook`. Keep TLS/HTTPS — Telegram requires it.

Files to inspect for code-gen or edits
- `webhook_handlers.py` — behavior & response format examples
- `webhook_setup.py` — credential loading, CLI args, and where to print debug info
- `app.py` / `main.py` — how Flask routes map to handlers

If you modify or add behavior
- Keep responses shaped as Telegram API payload dicts (method + args).
- Preserve `authorized_contacts.jsonl` newline-delimited append behaviour.

If anything is unclear, ask for:
- preferred webhook URL path and secret token handling policy
- whether to consolidate `app.py` and `main.py` (they are slightly different entry-points)

---
Small, focused guidance — update if you add tests, CI, or change storage.
