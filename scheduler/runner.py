import asyncio
import logging

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import settings
from shared.database import init_db
from scheduler.tasks import (
    notify_new_lessons,
    remind_watch_lessons,
    send_midweek_quote,
    send_historical_fact,
    remind_saturday,
    remind_sunday,
    remind_interactive,
    remind_practices,
    remind_tomiris_practice_scheduled,
    remind_curators_scores,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


def build_scheduler(bot: Bot) -> AsyncIOScheduler:
    s = AsyncIOScheduler(timezone=settings.timezone)

    # Пн 12:00 — новые уроки
    s.add_job(notify_new_lessons, "cron", day_of_week="mon", hour=12, minute=0, kwargs={"bot": bot}, id="new_lessons")
    # Вт 18:00 — напоминание уроки
    s.add_job(remind_watch_lessons, "cron", day_of_week="tue", hour=18, minute=0, kwargs={"bot": bot}, id="watch_tue")
    # Чт 18:00 — напоминание уроки
    s.add_job(remind_watch_lessons, "cron", day_of_week="thu", hour=18, minute=0, kwargs={"bot": bot}, id="watch_thu")
    # Ср 12:00 — цитата
    s.add_job(send_midweek_quote, "cron", day_of_week="wed", hour=12, minute=0, kwargs={"bot": bot}, id="quote")
    # Пт 19:00 — исторический факт
    s.add_job(send_historical_fact, "cron", day_of_week="fri", hour=19, minute=0, kwargs={"bot": bot}, id="fact")
    # Сб 18:00 — напоминание конспекты
    s.add_job(remind_saturday, "cron", day_of_week="sat", hour=18, minute=0, kwargs={"bot": bot}, id="remind_sat")
    # Вс 11:00 — последнее напоминание
    s.add_job(remind_sunday, "cron", day_of_week="sun", hour=11, minute=0, kwargs={"bot": bot}, id="remind_sun")
    # Пн 12:30 — интерактивка (последний пн месяца)
    s.add_job(remind_interactive, "cron", day_of_week="mon", hour=12, minute=30, kwargs={"bot": bot}, id="interactive")
    # Каждые 5 мин — практики кураторов
    s.add_job(remind_practices, "interval", minutes=5, kwargs={"bot": bot}, id="remind_practices")
    # Каждые 5 мин — практики Томирис
    s.add_job(remind_tomiris_practice_scheduled, "interval", minutes=5, kwargs={"bot": bot}, id="tomiris_reminders")
    #for ENT
    s.add_job(remind_curators_scores, "cron", hour=18, minute=0, kwargs={"bot": bot}, id="curator_scores")
    return s


async def main() -> None:
    await init_db()

    bot = Bot(
        token=settings.student_bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    scheduler = build_scheduler(bot)
    scheduler.start()

    logger.info("⏰ Scheduler started:")
    for job in scheduler.get_jobs():
        logger.info(f"  {job.id} → {job.next_run_time}")

    try:
        while True:
            await asyncio.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
