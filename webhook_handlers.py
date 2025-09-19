from __future__ import annotations


import json
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any, Dict, Optional

ChatId = int | str


class TextMessageHandler:

    """Обрабатывает входящие текстовые сообщения из Telegram. даёт ответы на команды."""

    def __init__(
        self,
        greeting_text: str | None = None,
        authorize_button_text: str = "Авторизоваться",
    ) -> None:
        self.greeting_text = (
            greeting_text
            or "Привет! Чтобы продолжить, авторизуйтесь через отправку контакта "
            "кнопкой ниже."
        )
        self.authorize_button_text = authorize_button_text
        self._command_handlers: Dict[str, Callable[[ChatId], Dict[str, Any]]] = {
            "/start": self._handle_start,
        }

    def handle(self, chat_id: ChatId, text: str) -> Optional[Dict[str, Any]]:
        """Возвращает ответ для Telegram API на переданное текстовое сообщение."""

        normalized = text.strip()
        if not normalized:
            return None

        first_token = normalized.split()[0].lower()
        handler = self._command_handlers.get(first_token)
        if handler is None:
            return None

        return handler(chat_id)

    def _handle_start(self, chat_id: ChatId) -> Dict[str, Any]:
        return {
            "method": "sendMessage",
            "chat_id": chat_id,
            "text": self.greeting_text,
            "reply_markup": {
                "keyboard": [
                    [
                        {
                            "text": self.authorize_button_text,
                            "request_contact": True,
                        }
                    ]
                ],
                "resize_keyboard": True,
                "one_time_keyboard": True,
            },

        }


DEFAULT_CONTACT_STORAGE = Path(__file__).resolve().parent / "authorized_contacts.jsonl"


class TelegramWebhookHandler:

    """Обрабатывает входящие обновления Telegram, полученные через вебхук."""

    def __init__(
        self,
        text_handler: TextMessageHandler | None = None,
        contact_storage_path: str | Path | None = None,
    ) -> None:
        self.text_handler = text_handler or TextMessageHandler()
        if contact_storage_path is None:
            storage_path = DEFAULT_CONTACT_STORAGE
        else:
            candidate = Path(contact_storage_path).expanduser()
            storage_path = (
                candidate
                if candidate.is_absolute()
                else DEFAULT_CONTACT_STORAGE.parent / candidate
            )

        self.contact_storage_path = storage_path.resolve()

    def handle_update(self, update: Mapping[str, Any] | None) -> Dict[str, Any]:
        """Обрабатывает обновление Telegram и формирует ответное сообщение."""

        if not isinstance(update, Mapping):
            return {"status": "ignored"}

        message = update.get("message")
        if isinstance(message, Mapping):
            contact_response = self._handle_contact_message(message)
            if contact_response is not None:
                return contact_response

            text_response = self._handle_text_message(message)
            if text_response is not None:
                return text_response

        return {"status": "ok"}

    def _handle_text_message(self, message: Mapping[str, Any]) -> Optional[Dict[str, Any]]:
        text = message.get("text")
        chat = message.get("chat")

        if not isinstance(text, str) or not isinstance(chat, Mapping):
            return None

        chat_id = chat.get("id")
        if not isinstance(chat_id, (int, str)):
            return None

        return self.text_handler.handle(chat_id, text)

    def _handle_contact_message(self, message: Mapping[str, Any]) -> Optional[Dict[str, Any]]:
        contact = message.get("contact")
        chat = message.get("chat")

        if not isinstance(contact, Mapping) or not isinstance(chat, Mapping):
            return None

        chat_id = chat.get("id")
        if not isinstance(chat_id, (int, str)):
            return None


        return self._create_contact_acknowledgement(chat_id, message)

    def _create_contact_acknowledgement(
        self, chat_id: ChatId, message: Mapping[str, Any]
    ) -> Dict[str, Any]:
        contact = message.get("contact")
        contact_payload = self._prepare_contact_payload(chat_id, message)
        if contact_payload is not None:
            self._print_contact_data(contact_payload)
            self._persist_contact_data(contact_payload)
        first_name = contact.get("first_name")
        last_name = contact.get("last_name")
        phone = contact.get("phone_number")

        name_parts = [
            part.strip()
            for part in (first_name, last_name)
            if isinstance(part, str) and part.strip()
        ]
        if name_parts:
            contact_label = " ".join(name_parts)
        elif isinstance(phone, str) and phone.strip():
            contact_label = phone.strip()
        else:
            contact_label = "контакт"

        text = f"Спасибо! {contact_label} сохранён для авторизации."
        return {
            "method": "sendMessage",
            "chat_id": chat_id,
            "text": text,
        }

    def _prepare_contact_payload(
        self, chat_id: ChatId, message: Mapping[str, Any]
    ) -> Optional[Dict[str, Any]]:
        contact = message.get("contact")
        if not isinstance(contact, Mapping):
            return None

        contact_dict = {
            key: value
            for key, value in contact.items()
            if isinstance(key, str)
        }

        author = message.get("from")
        author_dict: Optional[Dict[str, Any]] = None
        if isinstance(author, Mapping):
            author_dict = {
                key: value
                for key, value in author.items()
                if isinstance(key, str)
            }

        payload: Dict[str, Any] = {
            "chat_id": chat_id,
            "contact": contact_dict,
        }
        message_id = message.get("message_id")
        if isinstance(message_id, int):
            payload["message_id"] = message_id

        date = message.get("date")
        if isinstance(date, int):
            payload["date"] = date

        if author_dict is not None:
            payload["from"] = author_dict

        return payload

    def _print_contact_data(self, payload: Mapping[str, Any]) -> None:
        formatted = json.dumps(payload, ensure_ascii=False)
        print(f"Получены данные авторизации: {formatted}")

    def _persist_contact_data(self, payload: Mapping[str, Any]) -> None:
        self.contact_storage_path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(payload, ensure_ascii=False)
        with self.contact_storage_path.open("a", encoding="utf-8") as file:
            file.write(line + "\n")
