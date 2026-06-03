# TOM Bot System

## Локальный запуск

```bash
pip install -r requirements.txt
python main.py
```

## Деплой на Railway

### Переменные окружения (Variables)

```
STUDENT_BOT_TOKEN=токен_бота_учеников
ADMIN_BOT_TOKEN=токен_бота_кураторов
DATABASE_URL=postgresql+asyncpg://...neon.tech/neondb?ssl=require
GOOGLE_SHEET_ID=110nGftUk-uLbXtMOuqWO5OitKbOcqBkFe3x9I03dyX4
GOOGLE_SHEETS_KEY_FILE=/tmp/credentials.json
GOOGLE_CREDENTIALS_BASE64=<base64 от credentials.json>
TIMEZONE=Asia/Almaty
```

Для GOOGLE_CREDENTIALS_BASE64 на маке:
```bash
base64 -i credentials.json | tr -d '\n'
```

### Start Command
```
python main.py
```

## Google Sheets — структура

| Лист | Колонки |
|------|---------|
| Streams | name, start_date (YYYY-MM-DD) |
| Groups | stream_name, group_name |
| Lessons | lesson_number, week_number, title |
| Tests | week_number, title |
| Facts | week_number, stream_name, text |
| Quotes | week_number, author, text |
| Practices | stream_name, datetime (ДД.ММ.ГГГГ ЧЧ:ММ), group_name |
| Curators | full_name, stream_name, group_name |

## Расписание уведомлений

| Время | Событие |
|-------|---------|
| Пн 12:00 | Новые уроки + тест если есть |
| Вт/Чт 18:00 | Напоминание смотреть уроки |
| Ср 12:00 | Цитата великого казаха |
| Пт 19:00 | Исторический факт |
| Сб 18:00 | Напоминание сдать конспекты/тест |
| Вс 11:00 | Последнее напоминание |
| Пн 12:30 | Интерактивка (последний пн месяца) |
| Каждые 5 мин | Практики кураторов и Томирис |
