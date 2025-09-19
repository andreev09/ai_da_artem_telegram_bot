from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from texts import DEFAULT_TEXTS, TextResources, load_texts
from webhook_handlers import TextMessageHandler, TelegramWebhookHandler


class TextsIntegrationTests(unittest.TestCase):
    def test_custom_texts_applied_to_start_command(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "texts.json"
            custom_texts = {
                "greeting_text": "Здравствуйте! Это кастомное приветствие.",
                "authorize_button_text": "Поделиться контактом",
                "contact_saved_template": "Контакт {contact_label} сохранён.",
            }
            path.write_text(json.dumps(custom_texts, ensure_ascii=False), encoding="utf-8")

            resources = load_texts(path)
            handler = TextMessageHandler(texts=resources)

            payload = handler.handle(42, "/start")
            self.assertIsNotNone(payload)
            assert payload is not None
            self.assertEqual(payload["text"], custom_texts["greeting_text"])
            button_text = payload["reply_markup"]["keyboard"][0][0]["text"]
            self.assertEqual(button_text, custom_texts["authorize_button_text"])

    def test_defaults_used_when_file_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            missing_path = Path(tmpdir) / "absent.json"
            resources = load_texts(missing_path)
            handler = TextMessageHandler(texts=resources)

            payload = handler.handle(1, "/start")
            self.assertIsNotNone(payload)
            assert payload is not None
            self.assertEqual(payload["text"], DEFAULT_TEXTS["greeting_text"])
            button_text = payload["reply_markup"]["keyboard"][0][0]["text"]
            self.assertEqual(button_text, DEFAULT_TEXTS["authorize_button_text"])

    def test_contact_saved_template_formatting(self) -> None:
        resources = TextResources({"contact_saved_template": "Сохранено: {contact_label}"})

        with tempfile.TemporaryDirectory() as tmpdir:
            storage = Path(tmpdir) / "contacts.jsonl"
            text_handler = TextMessageHandler(texts=resources)
            webhook_handler = TelegramWebhookHandler(
                text_handler=text_handler,
                contact_storage_path=storage,
            )

            message_with_name = {
                "contact": {"first_name": "Иван", "last_name": "Иванов"},
            }
            ack = webhook_handler._create_contact_acknowledgement(10, message_with_name)
            self.assertEqual(ack["text"], "Сохранено: Иван Иванов")

            message_with_phone = {
                "contact": {"phone_number": "+79991234567"},
            }
            ack = webhook_handler._create_contact_acknowledgement(11, message_with_phone)
            self.assertEqual(ack["text"], "Сохранено: +79991234567")

            message_empty = {"contact": {}}
            ack = webhook_handler._create_contact_acknowledgement(12, message_empty)
            self.assertEqual(ack["text"], "Сохранено: контакт")


if __name__ == "__main__":
    unittest.main()
