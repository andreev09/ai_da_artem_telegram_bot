# Telegram Flask Webhook

Это простое приложение на Flask, которое обрабатывает вебхук Telegram.

## Запуск

```bash
pip install -r requirements.txt
FLASK_APP=app.py flask run --host=0.0.0.0 --port=8000
```

Вебхук принимает POST-запросы по адресу `/webhook`. Если сообщение содержит
команду `/start`, сервер вернет ответ для отправки приветственного сообщения.
