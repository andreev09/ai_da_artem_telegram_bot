from __future__ import annotations

from flask import Flask, jsonify, request
from flask.typing import ResponseReturnValue

_BIND_PORT = 8000
app = Flask(__name__)


@app.route("/webhook", methods=["POST"])
def telegram_webhook() -> ResponseReturnValue:
    """Handle incoming Telegram webhook updates.

    When the incoming message contains the ``/start`` command we respond with a
    greeting message. Telegram accepts returning a JSON payload describing the
    API call it should perform on behalf of the bot, so we return a response that
    will send the greeting to the originating chat. For all other updates we
    simply acknowledge the webhook.
    """
    update = request.get_json(silent=True) or {}
    message = update.get("message", {}) if isinstance(update, dict) else {}
    chat = message.get("chat", {}) if isinstance(message, dict) else {}
    chat_id = chat.get("id") if isinstance(chat, dict) else None
    text = message.get("text") if isinstance(message, dict) else None

    if isinstance(text, str) and text.startswith("/start") and chat_id is not None:
        greeting_text = "Привет! Рада познакомиться."
        return (
            jsonify(
                {
                    "method": "sendMessage",
                    "chat_id": chat_id,
                    "text": greeting_text,
                }
            ),
            200,
        )

    return jsonify({"status": "ok"}), 200


@app.route("/", methods=["GET"])
def index() -> ResponseReturnValue:
    """Provide a simple health-check endpoint."""
    return {"status": "running"}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=_BIND_PORT)
