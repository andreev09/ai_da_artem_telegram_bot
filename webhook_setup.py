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

# URL вебхука указываем прямо здесь, чтобы можно было быстро обновлять.
# Замените значение на ваш реальный HTTPS-адрес перед запуском скрипта.
WEBHOOK_URL = "https://aidaartem.eu.pythonanywhere.com/webhook"

# Файл с секретами в формате KEY=VALUE, например TELEGRAM_BOT_TOKEN=...
SECRETS_FILE = Path("secrets/tokens.env")

_INSECURE_ENV = "TELEGRAM_WEBHOOK_INSECURE"
_CA_BUNDLE_ENV = "TELEGRAM_WEBHOOK_CA_BUNDLE"


@dataclass(slots=True)
class WebhookConfig:
    """Описывает все параметры, необходимые для запроса setWebhook."""

    webhook_url: str
    token: str
    secret_token: Optional[str]
    drop_pending_updates: bool
    allowed_updates: Optional[list[str]]
    verify: bool | str

    def to_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "url": self.webhook_url,
            "drop_pending_updates": self.drop_pending_updates,
        }

        if self.secret_token:
            payload["secret_token"] = self.secret_token

        if self.allowed_updates is not None:
            payload["allowed_updates"] = list(self.allowed_updates)

        return payload


class TelegramWebhookError(RuntimeError):
    """Сигнализирует об ошибке при обращении к Telegram API."""


def _load_env_from_file(path: Path) -> None:
    """Загружает пары KEY=VALUE из файла с секретами в переменные окружения."""

    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        if "=" not in line:
            continue

        key, raw_value = line.split("=", 1)
        key = key.strip()
        if not key:
            continue

        value = raw_value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        os.environ.setdefault(key, value)


def _ensure_no_proxy() -> None:
    """Добавляет api.telegram.org в NO_PROXY/no_proxy, чтобы обойти системные прокси."""

    domain = "api.telegram.org"
    for key in ("NO_PROXY", "no_proxy"):
        current = os.environ.get(key, "")
        normalized = {item.strip() for item in current.split(",") if item.strip()}
        if domain in normalized:
            continue
        normalized.add(domain)
        os.environ[key] = ",".join(sorted(normalized))


def _call_telegram(
    method: str,
    token: str,
    payload: Mapping[str, Any],
    *,
    verify: bool | str,
) -> Mapping[str, Any]:
    """Отправляет JSON-запрос к Telegram Bot API и возвращает разобранный ответ."""

    # Формируем полный URL к методу Telegram Bot API
    endpoint = f"{_TELEGRAM_API_ROOT}/bot{token}/{method}"

    _ensure_no_proxy()

    masked_token = f"{token[:5]}...{token[-2:]}" if len(token) > 7 else "***"
    sanitized_endpoint = endpoint.replace(token, masked_token)
    print(f"Отправляем запрос к Telegram: {sanitized_endpoint}")
    print(
        "Тело запроса:",
        json.dumps(payload, ensure_ascii=False, indent=2),
    )

    try:
        response = requests.post(
            endpoint,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10,
            verify=verify,
            proxies={"http": None, "https": None},
        )
        response.raise_for_status()
    except RequestException as exc:
        raise TelegramWebhookError(f"Не удалось обратиться к Telegram API: {exc}") from exc

    try:
        parsed = response.json()
    except ValueError as exc:
        raise TelegramWebhookError("Telegram API вернул некорректный JSON") from exc

    if not parsed.get("ok", False):
        # Telegram вернул валидный JSON, но с флагом ok=False
        description = parsed.get("description", "неизвестная ошибка")
        raise TelegramWebhookError(f"Telegram API сообщил об ошибке: {description}")

    return parsed


def set_telegram_webhook(config: WebhookConfig) -> Mapping[str, Any]:
    """Отправляет запрос setWebhook с параметрами из конфигурации."""

    if not config.webhook_url:
        raise ValueError("URL вебхука не может быть пустым.")

    if not config.token:
        raise ValueError("Токен бота не задан.")

    payload = config.to_payload()
    return _call_telegram("setWebhook", config.token, payload, verify=config.verify)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Настройка вебхука Telegram через Bot API",
    )
    parser.add_argument(
        "--webhook-url",
        dest="webhook_url",
        help="Опциональный override для URL вебхука (по умолчанию WEBHOOK_URL из файла).",
    )
    parser.add_argument(
        "--secret-token",
        dest="secret_token",
        help="Передаёт secret_token для проверки входящих запросов Telegram.",
    )
    parser.add_argument(
        "--ca-bundle",
        dest="ca_bundle",
        help="Путь к PEM-файлу с доверенными корневыми сертификатами.",
    )
    parser.add_argument(
        "--insecure",
        action="store_true",
        help="Отключить проверку TLS-сертификата (используйте только для отладки).",
    )
    parser.add_argument(
        "--drop-pending-updates",
        action="store_true",
        help="Удаляет накопленные обновления перед применением нового вебхука.",
    )
    parser.add_argument(
        "--allowed-update",
        dest="allowed_updates",
        action="append",
        help="Перечень типов обновлений (можно указывать несколько раз).",
    )
    return parser.parse_args()


def main() -> None:
    _load_env_from_file(SECRETS_FILE)
    args = _parse_args()

    webhook_url = args.webhook_url or WEBHOOK_URL
    if webhook_url == "https://example.com/webhook/secret":
        raise SystemExit(
            "Укажите реальный адрес вебхука в WEBHOOK_URL или передайте его через --webhook-url."
        )

    ca_bundle_raw = args.ca_bundle or os.getenv(_CA_BUNDLE_ENV)
    ca_bundle: Optional[str] = None
    if ca_bundle_raw:
        bundle_path = Path(ca_bundle_raw).expanduser()
        if not bundle_path.is_file():
            raise SystemExit(f"Файл с корневыми сертификатами не найден: {bundle_path}")
        ca_bundle = str(bundle_path)

    insecure_env = os.getenv(_INSECURE_ENV, "").strip().lower()
    insecure_requested = args.insecure or insecure_env in {"1", "true", "yes", "on"}
    verify_option: bool | str
    if insecure_requested:
        verify_option = False
    elif ca_bundle:
        verify_option = ca_bundle
    else:
        verify_option = True

    if insecure_requested:
        print(
            "Проверка TLS отключена. Используйте этот режим только для отладки.",
            file=sys.stderr,
        )

    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise SystemExit(
            "Не найден TELEGRAM_BOT_TOKEN. Укажите его в secrets/tokens.env перед запуском."
        )

    config = WebhookConfig(
        webhook_url=webhook_url,
        token=token,
        secret_token=args.secret_token or os.getenv("TELEGRAM_WEBHOOK_SECRET_TOKEN"),
        drop_pending_updates=args.drop_pending_updates,
        allowed_updates=args.allowed_updates,
        verify=verify_option,
    )

    try:
        # Склеиваем аргументы CLI и отправляем запрос к Telegram
        result = set_telegram_webhook(config)
    except (TelegramWebhookError, ValueError) as exc:
        # Печатаем понятное сообщение, чтобы не прятать причину ошибки
        raise SystemExit(f"Не удалось настроить вебхук: {exc}")

    formatted = json.dumps(result, ensure_ascii=False, indent=2)
    # Выводим ответ Telegram, чтобы удобно проверять результат
    print(f"Вебхук успешно обновлён. Ответ Telegram:\n{formatted}")


if __name__ == "__main__":
    main()
