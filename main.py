"""
main.py — единая точка входа для Railway.
Запускает student_bot, admin_bot и scheduler в одном процессе.
"""

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import settings
from shared.database import init_db
from student_bot.middlewares.db import DbSessionMiddleware
from admin_bot.middlewares.curator_auth import CuratorAuthMiddleware
from student_bot.routers.registration import router as reg_router
from admin_bot.routers.practice import router as practice_router
from scheduler.runner import build_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


async def main() -> None:
    await init_db()

    # Student bot
    student_bot = Bot(
        token=settings.student_bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    student_dp = Dispatcher()
    student_dp.update.middleware(DbSessionMiddleware())
    student_dp.include_router(reg_router)

    # Admin bot
    admin_bot = Bot(
        token=settings.admin_bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    admin_dp = Dispatcher(storage=MemoryStorage())
    admin_dp.message.middleware(CuratorAuthMiddleware())
    admin_dp.callback_query.middleware(CuratorAuthMiddleware())
    admin_dp.include_router(practice_router)

    # Scheduler (рассылки через student_bot)
    scheduler = build_scheduler(student_bot)
    scheduler.start()
    logger.info("⏰ Scheduler started")

    await student_bot.delete_webhook(drop_pending_updates=True)
    await admin_bot.delete_webhook(drop_pending_updates=True)

    logger.info("🚀 All services started")

    await asyncio.gather(
        student_dp.start_polling(student_bot),
        admin_dp.start_polling(admin_bot),
    )


if __name__ == "__main__":
    asyncio.run(main())
