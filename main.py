from __future__ import annotations

from flask import Flask, jsonify, request
from flask.typing import ResponseReturnValue

from webhook_handlers import TelegramWebhookHandler

app = Flask(__name__)
webhook_handler = TelegramWebhookHandler()


@app.route("/webhook", methods=["POST"])
def telegram_webhook() -> ResponseReturnValue:
    """Обрабатывает входящие обновления Telegram, пришедшие по вебхуку."""

    update = request.get_json(silent=True)
    response_payload = webhook_handler.handle_update(update)
    return jsonify(response_payload), 200


@app.route("/", methods=["GET"])
def index() -> ResponseReturnValue:
    """Возвращает простой эндпоинт для проверки работоспособности."""
    print("Health check OK")
    
    return {"status": "running"}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
