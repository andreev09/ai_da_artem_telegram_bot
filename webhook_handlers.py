from __future__ import annotations


import json
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any, Dict, Optional
import os
import requests
from pathlib import Path

from texts import DEFAULT_TEXTS, TextResources, load_texts
try:
    # optional runtime import for integration example
    from xls_to_xlsx import convert_xls_bytes_to_xlsx_bytes  # type: ignore
except Exception:
    convert_xls_bytes_to_xlsx_bytes = None  # type: ignore

ChatId = int | str


class TextMessageHandler:

    """Обрабатывает входящие текстовые сообщения из Telegram. даёт ответы на команды."""

    def __init__(
        self,
        greeting_text: str | None = None,
        authorize_button_text: str | None = None,
        *,
        texts: Mapping[str, str] | TextResources | None = None,
        contact_saved_template: str | None = None,
    ) -> None:
        if texts is None:
            resources = load_texts()
        elif isinstance(texts, TextResources):
            resources = texts
        else:
            resources = TextResources(texts)

        self.texts = resources

        default_greeting = resources.get("greeting_text", DEFAULT_TEXTS["greeting_text"])
        default_button = resources.get(
            "authorize_button_text", DEFAULT_TEXTS["authorize_button_text"]
        )
        default_template = resources.get(
            "contact_saved_template", DEFAULT_TEXTS["contact_saved_template"]
        )

        self.greeting_text = greeting_text if greeting_text is not None else default_greeting
        self.authorize_button_text = (
            authorize_button_text if authorize_button_text is not None else default_button
        )
        self.contact_saved_template = (
            contact_saved_template if contact_saved_template is not None else default_template
        )
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
            # prioritize document handling
            doc_response = self._handle_document_message(message)
            if doc_response is not None:
                return doc_response

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

        # If update contains a document (file) we may want to convert it.
        # Telegram provides files via getFile API; this project keeps handlers
        # pure (returns payloads) so actual file download is done externally.
        # Below is an example of how you could integrate conversion once you
        # have raw bytes of an incoming .xls file:
        #
        # if convert_xls_bytes_to_xlsx_bytes is not None and message.get("document"):
        #     # fetch file bytes using Telegram getFile and requests (not shown here)
        #     xls_bytes = fetch_file_bytes_somehow(file_path)
        #     xlsx_bytes = convert_xls_bytes_to_xlsx_bytes(xls_bytes)
        #     # then store/send xlsx_bytes as needed

        return self._create_contact_acknowledgement(chat_id, message)

    def _handle_document_message(self, message: Mapping[str, Any]) -> Optional[Dict[str, Any]]:
        """If message contains a document (.xls), download, convert and send back.

        Returns a payload dict for Telegram API response if action was performed,
        otherwise None.
        """
        document = message.get("document")
        chat = message.get("chat")
        if not isinstance(document, Mapping) or not isinstance(chat, Mapping):
            return None

        chat_id = chat.get("id")
        if not isinstance(chat_id, (int, str)):
            return None

        file_id = document.get("file_id")
        file_name = document.get("file_name") or document.get("file_name")
        file_size = document.get("file_size") or document.get("file_size")

        # Only process .xls files
        if not isinstance(file_id, str) or not isinstance(document.get("mime_type"), str):
            return None

        mime = document.get("mime_type", "")
        if not (mime in ("application/vnd.ms-excel",) or (isinstance(file_name, str) and file_name.lower().endswith(".xls"))):
            return None

        # Enforce maximum file size: 1 MB
        MAX_BYTES = 1 * 1024 * 1024
        if isinstance(file_size, int) and file_size > MAX_BYTES:
            return {"method": "sendMessage", "chat_id": chat_id, "text": "Файл слишком большой (макс 1МБ)."}

        # Need TELEGRAM_BOT_TOKEN to download/upload files
        token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not token:
            return {"method": "sendMessage", "chat_id": chat_id, "text": "Сервис не настроен (нет токена)."}

        # 1) getFile to obtain path
        getfile_url = f"https://api.telegram.org/bot{token}/getFile"
        try:
            r = requests.get(getfile_url, params={"file_id": file_id}, timeout=10, proxies={"http": None, "https": None})
            r.raise_for_status()
            data = r.json()
        except Exception:
            return {"method": "sendMessage", "chat_id": chat_id, "text": "Не удалось получить файл от Telegram."}

        result = data.get("result") or {}
        file_path = result.get("file_path")
        if not isinstance(file_path, str):
            return {"method": "sendMessage", "chat_id": chat_id, "text": "Неверный ответ Telegram при получении файла."}

        file_url = f"https://api.telegram.org/file/bot{token}/{file_path}"

        try:
            r2 = requests.get(file_url, timeout=20, proxies={"http": None, "https": None})
            r2.raise_for_status()
            xls_bytes = r2.content
        except Exception:
            return {"method": "sendMessage", "chat_id": chat_id, "text": "Не удалось скачать файл."}

        if len(xls_bytes) > MAX_BYTES:
            return {"method": "sendMessage", "chat_id": chat_id, "text": "Файл слишком большой (макс 1МБ)."}

        # Convert
        if convert_xls_bytes_to_xlsx_bytes is None:
            return {"method": "sendMessage", "chat_id": chat_id, "text": "Конвертер не доступен на сервере."}

        try:
            xlsx_bytes = convert_xls_bytes_to_xlsx_bytes(xls_bytes)
        except Exception:
            return {"method": "sendMessage", "chat_id": chat_id, "text": "Ошибка при конвертации файла."}

        # Upload back to Telegram via sendDocument (multipart/form-data)
        send_url = f"https://api.telegram.org/bot{token}/sendDocument"
        files = {
            "document": ( (file_name or "converted.xlsx"), xlsx_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" ),
        }
        data = {"chat_id": str(chat_id)}
        try:
            resp = requests.post(send_url, data=data, files=files, timeout=30, proxies={"http": None, "https": None})
            resp.raise_for_status()
            # return ack to webhook caller
            return {"status": "sent"}
        except Exception:
            return {"method": "sendMessage", "chat_id": chat_id, "text": "Не удалось отправить конвертированный файл обратно."}

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

        template_source = getattr(
            self.text_handler, "contact_saved_template", DEFAULT_TEXTS["contact_saved_template"]
        )
        template = template_source or DEFAULT_TEXTS["contact_saved_template"]
        try:
            text = template.format(contact_label=contact_label)
        except (KeyError, IndexError, ValueError):
            text = DEFAULT_TEXTS["contact_saved_template"].format(
                contact_label=contact_label
            )
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
