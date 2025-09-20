# Telegram Flask Webhook

Приложение реализует webhook для Telegram-бота. Оно обрабатывает текстовые команды, сохраняет контакты пользователей и при необходимости конвертирует присланные `.xls` файлы в `.xlsx` с помощью LibreOffice, запущенного в headless-режиме.

## Возможности

- Эндпоинт `/webhook` принимает апдейты Telegram и делегирует обработку классу `TelegramWebhookHandler`.
- Команда `/start` отвечает приветственным сообщением и отправляет клавиатуру с запросом контакта.
- Полученные контакты записываются в `authorized_contacts.jsonl` и подтверждаются ответом пользователю.
- Документы с расширением `.xls` конвертируются в `.xlsx` через вызов `soffice --headless` и пересылаются обратно отправителю.

## Требования

- Python 3.11+.
- LibreOffice 7+ с доступным бинарником `soffice` (можно установить headless-сборку).
- Токен Telegram-бота от `@BotFather` для сценариев с загрузкой и отправкой файлов.

## Установка зависимостей

### Python-пакеты

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### LibreOffice (`soffice`)

Установите LibreOffice и убедитесь, что бинарник доступен из shell:

```bash
# Debian/Ubuntu
sudo apt update && sudo apt install -y libreoffice

# macOS (Homebrew)
brew install --cask libreoffice

soffice --headless --version
```

Если `soffice` находится в нестандартном пути, добавьте директорию в `PATH` или задайте переменную окружения:

```bash
export SOFFICE_BIN=/opt/libreoffice/program/soffice
# или
export PATH="/opt/libreoffice/program:$PATH"
```

## Запуск

```bash
export TELEGRAM_BOT_TOKEN="<ваш_бот_токен>"
export FLASK_APP=main.py
flask run --host=0.0.0.0 --port=8000
```

Альтернативно можно запустить приложение напрямую:

```bash
python main.py
```

Эндпоинт `GET /` возвращает `{ "status": "running" }` для health-check. Для регистрации вебхука используйте `webhook_setup.py` в качестве примера.

## Тесты

Основной набор тестов запускается через `pytest`:

```bash
pytest
```

Тест `tests/test_xls_converter.py` вызывает LibreOffice. Если бинарник лежит вне `PATH`, укажите его явно:

```bash
SOFFICE_BIN=/opt/libreoffice/program/soffice pytest tests/test_xls_converter.py
```

## Конвертация Excel

`xls_to_xlsx.py` сохраняет входящие байты `.xls` во временную директорию и запускает `soffice --headless --convert-to xlsx`. Полученный файл считывается обратно и отправляется пользователю. При отсутствии LibreOffice бот отвечает сообщением о том, что конвертация временно недоступна.

## Настройка текстов

Тексты для приветствия и клавиатуры хранятся в `texts.json`. Если файл не найден, используются значения по умолчанию из `texts.py`. Для проверки изменений запускайте тесты после правок текстов и шаблонов.
