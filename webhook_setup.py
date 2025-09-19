from __future__ import annotations

"""Utility for configuring the Telegram webhook endpoint for the bot."""

import argparse
import json
import os
from typing import Any, Mapping
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

_TELEGRAM_API_ROOT = "https://api.telegram.org"


class TelegramWebhookError(RuntimeError):
    """Raised when the Telegram API returns an error response."""


def _call_telegram(method: str, token: str, payload: Mapping[str, Any]) -> Mapping[str, Any]:
    """Sends a JSON request to the Telegram Bot API and returns the parsed body."""

    # Формируем полный URL к методу Telegram Bot API
    endpoint = f"{_TELEGRAM_API_ROOT}/bot{token}/{method}"

    # Telegram допускает JSON-тело запроса, поэтому кодируем словарь в UTF-8
    data = json.dumps(payload).encode("utf-8")
    request = Request(endpoint, data=data, headers={"Content-Type": "application/json"})

    try:
        # Отправляем HTTP-запрос и читаем ответ от Telegram
        with urlopen(request) as response:
            body = response.read().decode("utf-8")
    except HTTPError as exc:
        # Telegram вернул код ошибки HTTP — читаем тело и прокидываем пользователю
        message = exc.read().decode("utf-8", errors="replace")
        raise TelegramWebhookError(
            f"Telegram API error {exc.code}: {message or exc.reason}"
        ) from exc
    except URLError as exc:
        # Ошибки уровня сети (DNS, таймауты и т.д.)
        raise TelegramWebhookError(f"Failed to reach Telegram API: {exc.reason}") from exc

    parsed = json.loads(body)
    if not parsed.get("ok", False):
        # Telegram вернул валидный JSON, но с флагом ok=False
        description = parsed.get("description", "unknown error")
        raise TelegramWebhookError(f"Telegram API returned failure: {description}")

    return parsed


def set_telegram_webhook(
    webhook_url: str,
    *,
    token: str | None = None,
    secret_token: str | None = None,
    drop_pending_updates: bool = False,
    allowed_updates: list[str] | None = None,
) -> Mapping[str, Any]:
    """Registers or updates the webhook URL for the Telegram bot."""

    resolved_token = token or os.getenv("TELEGRAM_BOT_TOKEN")
    if not resolved_token:
        raise ValueError(
            "Bot token is required. Pass it explicitly or set TELEGRAM_BOT_TOKEN."
        )

    if not webhook_url:
        raise ValueError("Webhook URL must be a non-empty string.")

    # Базовый набор параметров, обязательный для setWebhook
    payload: dict[str, Any] = {
        "url": webhook_url,
        "drop_pending_updates": drop_pending_updates,
    }

    if secret_token:
        # Дополнительная защита входящих вебхуков
        payload["secret_token"] = secret_token

    if allowed_updates is not None:
        # Фильтруем типы обновлений, которые Telegram будет присылать
        payload["allowed_updates"] = allowed_updates

    return _call_telegram("setWebhook", resolved_token, payload)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Set the Telegram webhook using the Bot API",
    )
    parser.add_argument(
        "webhook_url",
        help="Absolute HTTPS URL that Telegram should use to deliver updates.",
    )
    parser.add_argument(
        "--token",
        help="Telegram bot token. Falls back to TELEGRAM_BOT_TOKEN environment variable.",
    )
    parser.add_argument(
        "--secret-token",
        dest="secret_token",
        help="Optional secret token for securing incoming webhook requests.",
    )
    parser.add_argument(
        "--drop-pending-updates",
        action="store_true",
        help="Drop updates that were queued before the webhook was changed.",
    )
    parser.add_argument(
        "--allowed-update",
        dest="allowed_updates",
        action="append",
        help="Whitelist of update types. Can be passed multiple times.",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()

    try:
        # Склеиваем аргументы CLI и отправляем запрос к Telegram
        result = set_telegram_webhook(
            args.webhook_url,
            token=args.token,
            secret_token=args.secret_token,
            drop_pending_updates=args.drop_pending_updates,
            allowed_updates=args.allowed_updates,
        )
    except (TelegramWebhookError, ValueError) as exc:
        # Печатаем понятное сообщение, чтобы не прятать причину ошибки
        raise SystemExit(f"Failed to set webhook: {exc}")

    formatted = json.dumps(result, ensure_ascii=False, indent=2)
    # Выводим ответ Telegram, чтобы удобно проверять результат
    print(f"Webhook successfully set. Telegram response:\n{formatted}")


if __name__ == "__main__":
    main()
