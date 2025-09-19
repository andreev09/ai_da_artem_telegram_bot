from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any, Dict, Optional

ChatId = int | str


class TextMessageHandler:
    """Process incoming Telegram text messages."""

    def __init__(self, greeting_text: str = "Привет! Рада познакомиться.") -> None:
        self.greeting_text = greeting_text
        self._command_handlers: Dict[str, Callable[[ChatId], Dict[str, Any]]] = {
            "/start": self._handle_start,
        }

    def handle(self, chat_id: ChatId, text: str) -> Optional[Dict[str, Any]]:
        """Return a Telegram API response for the provided text message."""
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
        }


class TelegramWebhookHandler:
    """Handle incoming Telegram webhook updates."""

    def __init__(self, text_handler: TextMessageHandler | None = None) -> None:
        self.text_handler = text_handler or TextMessageHandler()

    def handle_update(self, update: Mapping[str, Any] | None) -> Dict[str, Any]:
        """Process a Telegram webhook update and return a response payload."""
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

        return self._create_contact_acknowledgement(chat_id, contact)

    def _create_contact_acknowledgement(
        self, chat_id: ChatId, contact: Mapping[str, Any]
    ) -> Dict[str, Any]:
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
