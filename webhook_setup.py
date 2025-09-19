from __future__ import annotations

"""Утилита для настройки URL вебхука Telegram-бота."""

import argparse
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Optional

import requests
from requests.exceptions import RequestException

_TELEGRAM_API_ROOT = "https://api.telegram.org"
WEBHOOK_URL = "https://aidaartem.eu.pythonanywhere.com/webhook"
SECRETS_FILE = Path("secrets/tokens.env")
_INSECURE_ENV = "TELEGRAM_WEBHOOK_INSECURE"
_CA_BUNDLE_ENV = "TELEGRAM_WEBHOOK_CA_BUNDLE"


@dataclass(slots=True)
class WebhookConfig:
    webhook_url: str
    token: str
    secret_token: Optional[str]
    drop_pending_updates: bool
    allowed_updates: Optional[list[str]]
    verify: bool | str

    def to_payload(self) -> dict[str, Any]:
        payload = {"url": self.webhook_url, "drop_pending_updates": self.drop_pending_updates}
        if self.secret_token:
            payload["secret_token"] = self.secret_token
        if self.allowed_updates is not None:
            payload["allowed_updates"] = list(self.allowed_updates)
        return payload


class TelegramWebhookError(RuntimeError):
    pass


def _load_env_from_file(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip()
        if not k:
            continue
        v = v.strip()
        if len(v) >= 2 and v[0] == v[-1] and v[0] in {'"', "'"}:
            v = v[1:-1]
        os.environ.setdefault(k, v)


def _ensure_no_proxy() -> None:
    domain = "api.telegram.org"
    for key in ("NO_PROXY", "no_proxy"):
        cur = os.environ.get(key, "")
        parts = {p.strip() for p in cur.split(",") if p.strip()}
        if domain not in parts:
            parts.add(domain)
            os.environ[key] = ",".join(sorted(parts))


def _call_telegram(method: str, token: str, payload: Mapping[str, Any], *, verify: bool | str) -> Mapping[str, Any]:
    endpoint = f"{_TELEGRAM_API_ROOT}/bot{token}/{method}"
    _ensure_no_proxy()
    masked = f"{token[:5]}...{token[-2:]}" if len(token) > 7 else "***"
    print("Отправляем запрос:", endpoint.replace(token, masked))
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    try:
        r = requests.post(endpoint, json=payload, headers={"Content-Type": "application/json"}, timeout=10, verify=verify, proxies={"http": None, "https": None})
        r.raise_for_status()
        data = r.json()
    except RequestException as exc:
        raise TelegramWebhookError(str(exc)) from exc
    except ValueError as exc:
        raise TelegramWebhookError("Invalid JSON from Telegram") from exc
    if not data.get("ok"):
        raise TelegramWebhookError(data.get("description", "unknown error"))
    return data


def set_telegram_webhook(config: WebhookConfig) -> Mapping[str, Any]:
    if not config.webhook_url or not config.token:
        raise ValueError("webhook_url and token are required")
    return _call_telegram("setWebhook", config.token, config.to_payload(), verify=config.verify)


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Setup Telegram webhook")
    p.add_argument("--webhook-url", dest="webhook_url")
    p.add_argument("--secret-token", dest="secret_token")
    p.add_argument("--ca-bundle", dest="ca_bundle")
    p.add_argument("--insecure", action="store_true")
    p.add_argument("--drop-pending-updates", action="store_true")
    p.add_argument("--allowed-update", dest="allowed_updates", action="append")
    return p.parse_args()


def main() -> None:
    _load_env_from_file(SECRETS_FILE)
    args = _parse_args()
    webhook_url = args.webhook_url or WEBHOOK_URL
    if webhook_url == "https://example.com/webhook/secret":
        raise SystemExit("Specify a real webhook URL")
    ca_bundle_raw = args.ca_bundle or os.getenv(_CA_BUNDLE_ENV)
    verify: bool | str = False if (args.insecure or os.getenv(_INSECURE_ENV, "").lower() in {"1", "true", "yes", "on"}) else (str(Path(ca_bundle_raw).expanduser()) if ca_bundle_raw and Path(ca_bundle_raw).is_file() else True)
    if isinstance(verify, str) and not Path(verify).is_file():
        raise SystemExit(f"CA bundle not found: {verify}")
    if args.insecure:
        print("TLS verification disabled", file=sys.stderr)
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise SystemExit("TELEGRAM_BOT_TOKEN not set")
    cfg = WebhookConfig(webhook_url=webhook_url, token=token, secret_token=(args.secret_token or os.getenv("TELEGRAM_WEBHOOK_SECRET_TOKEN")), drop_pending_updates=args.drop_pending_updates, allowed_updates=args.allowed_updates, verify=verify)
    try:
        res = set_telegram_webhook(cfg)
    except (TelegramWebhookError, ValueError) as exc:
        raise SystemExit(f"Failed to set webhook: {exc}")
    print("Webhook updated:", json.dumps(res, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
