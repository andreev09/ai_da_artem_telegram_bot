from __future__ import annotations

"""Загрузчик текстовых ресурсов для Telegram-бота."""

import json
from collections.abc import Iterator, Mapping
from pathlib import Path
from typing import Any, Dict

DEFAULT_TEXTS: Dict[str, str] = {
    "greeting_text": (
        "Привет! Чтобы продолжить, авторизуйтесь через отправку контакта "
        "кнопкой ниже."
    ),
    "authorize_button_text": "Авторизоваться",
    "contact_saved_template": "Спасибо! {contact_label} сохранён для авторизации.",
}


class TextResources(Mapping[str, str]):
    """Набор текстов с дефолтами и поддержкой форматирования."""

    def __init__(self, data: Mapping[str, Any] | None = None) -> None:
        sanitized: Dict[str, str] = DEFAULT_TEXTS.copy()
        if data:
            for key, value in data.items():
                if isinstance(key, str) and isinstance(value, str):
                    sanitized[key] = value
        self._texts = sanitized

    def __getitem__(self, key: str) -> str:
        return self._texts[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self._texts)

    def __len__(self) -> int:
        return len(self._texts)

    def get(self, key: str, default: str | None = None) -> str | None:
        return self._texts.get(key, default)

    def format(self, key: str, **kwargs: Any) -> str:
        template = self._texts.get(key, DEFAULT_TEXTS.get(key, ""))
        try:
            return template.format(**kwargs)
        except (KeyError, IndexError, ValueError):
            fallback = DEFAULT_TEXTS.get(key, template)
            return fallback.format(**kwargs)

    def to_dict(self) -> Dict[str, str]:
        return self._texts.copy()


def load_texts(path: Path | str | None = None) -> TextResources:
    """Загружает JSON с текстами и возвращает ресурсы с запасными значениями."""

    if path is None:
        path_obj = Path(__file__).resolve().with_name("texts.json")
    else:
        path_obj = Path(path).expanduser()

    try:
        with path_obj.open(encoding="utf-8") as file:
            loaded = json.load(file)
    except FileNotFoundError:
        return TextResources()
    except (OSError, json.JSONDecodeError):
        return TextResources()

    if not isinstance(loaded, dict):
        return TextResources()

    return TextResources(loaded)
