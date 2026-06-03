from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from shared.database import AsyncSessionFactory
from shared.models import Curator


class CuratorAuthMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if isinstance(event, (Message, CallbackQuery)):
            user = event.from_user
        else:
            return

        is_start = isinstance(event, Message) and event.text == "/start"
        is_name_select = isinstance(event, CallbackQuery) and event.data.startswith("curator_name:")

        if is_start or is_name_select:
            async with AsyncSessionFactory() as session:
                data["session"] = session
                try:
                    result = await handler(event, data)
                    await session.commit()
                    return result
                except Exception:
                    await session.rollback()
                    raise
            return

        async with AsyncSessionFactory() as session:
            curator = await session.get(Curator, user.id)

            if not curator:
                if isinstance(event, Message):
                    await event.answer("⛔️ У тебя нет доступа.\nНапиши /start для регистрации.")
                elif isinstance(event, CallbackQuery):
                    await event.answer("⛔️ Напиши /start для регистрации.", show_alert=True)
                return

            data["session"] = session
            data["curator"] = curator

            try:
                result = await handler(event, data)
                await session.commit()
                return result
            except Exception:
                await session.rollback()
                raise
