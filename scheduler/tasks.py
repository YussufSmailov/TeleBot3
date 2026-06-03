import logging
import random
from datetime import datetime, timedelta

import pytz
from aiogram import Bot
from sqlalchemy import and_, select

from config import settings
from shared.database import AsyncSessionFactory
from shared.models import Practice, Student, TomirisReminderSent
from shared.sheets import get_sheets

logger = logging.getLogger(__name__)
TZ = pytz.timezone(settings.timezone)


async def _students_in_stream(session, stream_name: str) -> list[int]:
    result = await session.execute(
        select(Student.telegram_id).where(Student.stream_name == stream_name)
    )
    return [r[0] for r in result.all()]


async def _students_in_group(session, stream_name: str, group_name: str) -> list[int]:
    result = await session.execute(
        select(Student.telegram_id).where(
            Student.stream_name == stream_name,
            Student.group_name == group_name,
        )
    )
    return [r[0] for r in result.all()]


async def _broadcast(bot: Bot, tg_ids: list[int], text: str) -> None:
    for tg_id in tg_ids:
        try:
            await bot.send_message(tg_id, text, parse_mode="HTML")
        except Exception as e:
            logger.warning(f"Send failed {tg_id}: {e}")


# ---------------------------------------------------------------------------
# Пн 12:00 — новые уроки + тест если есть
# ---------------------------------------------------------------------------

async def notify_new_lessons(bot: Bot) -> None:
    logger.info("Task: notify_new_lessons")
    sheets = get_sheets()
    async with AsyncSessionFactory() as session:
        for stream in sheets.get_streams():
            week = stream.current_week
            lessons = sheets.get_lessons(week)
            if not lessons:
                continue

            lessons_text = "\n".join(f"  №{l.lesson_number} — {l.title}" for l in lessons)
            deadline_str = stream.deadline_for_week(week).strftime("%d.%m.%Y")
            test = sheets.get_test(week)
            test_line = f"\n\n📊 <b>Контрольный тест этой недели:</b>\n  {test.title}" if test else ""

            text = (
                f"📚 <b>Неделя {week} началась!</b>\n\n"
                f"Новые уроки:\n{lessons_text}"
                f"{test_line}\n\n"
                f"📌 Дедлайн: <b>воскресенье {deadline_str} в 12:00</b> 🚀"
            )
            ids = await _students_in_stream(session, stream.name)
            await _broadcast(bot, ids, text)


# ---------------------------------------------------------------------------
# Вт и Чт 18:00 — напоминание смотреть уроки
# ---------------------------------------------------------------------------

async def remind_watch_lessons(bot: Bot) -> None:
    logger.info("Task: remind_watch_lessons")
    sheets = get_sheets()
    async with AsyncSessionFactory() as session:
        for stream in sheets.get_streams():
            text = (
                f"👀 <b>Не забывай смотреть уроки!</b>\n\n"
                f"Дедлайн — воскресенье в 12:00 ⏰"
            )
            ids = await _students_in_stream(session, stream.name)
            await _broadcast(bot, ids, text)


# ---------------------------------------------------------------------------
# Ср 12:00 — цитата
# ---------------------------------------------------------------------------

async def send_midweek_quote(bot: Bot) -> None:
    logger.info("Task: send_midweek_quote")
    sheets = get_sheets()
    async with AsyncSessionFactory() as session:
        for stream in sheets.get_streams():
            quotes = sheets.get_quotes(stream.current_week)
            if not quotes:
                continue
            q = random.choice(quotes)
            text = f"💡 <b>Мысль дня</b>\n\n«{q.text}»\n\n— <i>{q.author}</i>"
            ids = await _students_in_stream(session, stream.name)
            await _broadcast(bot, ids, text)


# ---------------------------------------------------------------------------
# Пт 19:00 — исторический факт
# ---------------------------------------------------------------------------

async def send_historical_fact(bot: Bot) -> None:
    logger.info("Task: send_historical_fact")
    sheets = get_sheets()
    async with AsyncSessionFactory() as session:
        for stream in sheets.get_streams():
            facts = sheets.get_facts(stream.current_week, stream.name)
            if not facts:
                continue
            f = random.choice(facts)
            text = (
                f"🏆 <b>Факт недели!</b>\n\n"
                f"{f.text}\n\n"
                f"<i>История Казахстана — это сила 💛</i>"
            )
            ids = await _students_in_stream(session, stream.name)
            await _broadcast(bot, ids, text)


# ---------------------------------------------------------------------------
# Сб 18:00 — напоминание сдать конспекты
# ---------------------------------------------------------------------------

async def remind_saturday(bot: Bot) -> None:
    logger.info("Task: remind_saturday")
    sheets = get_sheets()
    async with AsyncSessionFactory() as session:
        for stream in sheets.get_streams():
            week = stream.current_week
            test = sheets.get_test(week)
            deadline_str = stream.deadline_for_week(week).strftime("%d.%m в %H:%M")
            test_line = f"\n📊 {test.title}" if test else ""
            text = (
                f"⏰ <b>Напоминание!</b>\n\n"
                f"Завтра дедлайн в {deadline_str}:\n"
                f"📝 Конспекты недели {week}"
                f"{test_line}\n\n"
                f"Не откладывай! 😉"
            )
            ids = await _students_in_stream(session, stream.name)
            await _broadcast(bot, ids, text)


# ---------------------------------------------------------------------------
# Вс 11:00 — последнее напоминание
# ---------------------------------------------------------------------------

async def remind_sunday(bot: Bot) -> None:
    logger.info("Task: remind_sunday")
    sheets = get_sheets()
    async with AsyncSessionFactory() as session:
        for stream in sheets.get_streams():
            week = stream.current_week
            test = sheets.get_test(week)
            test_line = f"\n📊 {test.title}" if test else ""
            text = (
                f"🚨 <b>Остался 1 час!</b>\n\n"
                f"Дедлайн в 12:00:\n"
                f"📝 Конспекты недели {week}"
                f"{test_line}\n\n"
                f"Срочно сдавай! ⚡️"
            )
            ids = await _students_in_stream(session, stream.name)
            await _broadcast(bot, ids, text)


# ---------------------------------------------------------------------------
# Последний пн месяца 12:30 — интерактивка
# ---------------------------------------------------------------------------

async def remind_interactive(bot: Bot) -> None:
    from calendar import monthcalendar
    today = datetime.now(TZ).date()
    mondays = [w[0] for w in monthcalendar(today.year, today.month) if w[0] != 0]
    if today.day != mondays[-1]:
        return

    logger.info("Task: remind_interactive")
    sheets = get_sheets()
    async with AsyncSessionFactory() as session:
        result = await session.execute(select(Student.telegram_id))
        ids = [r[0] for r in result.all()]
        text = (
            f"🎮 <b>Напоминание об интерактивке!</b>\n\n"
            f"Сегодня последний понедельник месяца.\n"
            f"Не забудь пройти интерактивное задание! 💪"
        )
        await _broadcast(bot, ids, text)


# ---------------------------------------------------------------------------
# Каждые 5 мин — напоминание о практике куратора за 1 час
# ---------------------------------------------------------------------------

async def remind_practices(bot: Bot) -> None:
    now = datetime.now(TZ)
    window_from = now + timedelta(minutes=55)
    window_to = now + timedelta(minutes=65)

    async with AsyncSessionFactory() as session:
        result = await session.execute(
            select(Practice).where(
                and_(
                    Practice.scheduled_at >= window_from,
                    Practice.scheduled_at <= window_to,
                    Practice.reminder_sent == False,
                )
            )
        )
        practices = result.scalars().all()

        for practice in practices:
            dt_str = practice.scheduled_at.astimezone(TZ).strftime("%H:%M")
            text = (
                f"🔔 <b>Через 1 час — практика с куратором!</b>\n\n"
                f"⏰ Начало в <b>{dt_str}</b> 🎯"
            )
            ids = await _students_in_group(session, practice.stream_name, practice.group_name)
            if ids:
                await _broadcast(bot, ids, text)
                practice.reminder_sent = True

        await session.commit()


# ---------------------------------------------------------------------------
# Каждые 5 мин — напоминания о практике Томирис (за день, за 4ч, за 1ч)
# ---------------------------------------------------------------------------

async def remind_tomiris_practice_scheduled(bot: Bot) -> None:
    sheets = get_sheets()
    now = datetime.now(TZ)

    windows = [
        (timedelta(hours=23, minutes=30), timedelta(hours=24, minutes=30), "day",  "завтра"),
        (timedelta(hours=3,  minutes=30), timedelta(hours=4,  minutes=30), "4h",   "через 4 часа"),
        (timedelta(minutes=30),           timedelta(hours=1,  minutes=30), "1h",   "через 1 час"),
    ]

    async with AsyncSessionFactory() as session:
        for p in sheets.get_tomiris_practices():
            for w_from, w_to, label, label_text in windows:
                if not (now + w_from <= p.scheduled_at <= now + w_to):
                    continue

                # Проверяем не отправляли ли уже
                result = await session.execute(
                    select(TomirisReminderSent).where(
                        and_(
                            TomirisReminderSent.stream_name == p.stream_name,
                            TomirisReminderSent.scheduled_at == p.scheduled_at,
                            TomirisReminderSent.label == label,
                        )
                    )
                )
                if result.scalar_one_or_none():
                    continue

                dt_str = p.scheduled_at.strftime("%d.%m.%Y в %H:%M")
                text = (
                    f"👑 <b>Практика с Томирис {label_text}!</b>\n\n"
                    f"🗓 <b>{dt_str}</b>\n\n"
                    f"Готовься! 💪"
                )

                if p.group_name:
                    ids = await _students_in_group(session, p.stream_name, p.group_name)
                else:
                    ids = await _students_in_stream(session, p.stream_name)

                await _broadcast(bot, ids, text)

                session.add(TomirisReminderSent(
                    stream_name=p.stream_name,
                    scheduled_at=p.scheduled_at,
                    label=label,
                ))

        await session.commit()
