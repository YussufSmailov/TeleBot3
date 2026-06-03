from datetime import datetime

import pytz
from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from shared.models import Curator, CuratorGroup, Practice, PracticeType
from shared.sheets import get_sheets
from admin_bot.keyboards.inline import (
    confirm_practice_keyboard,
    curator_names_keyboard,
    groups_keyboard,
    main_menu_keyboard,
    practices_keyboard,
)

router = Router(name="practice")
TZ = pytz.timezone(settings.timezone)


class PracticeForm(StatesGroup):
    waiting_for_datetime = State()


@router.message(CommandStart())
async def cmd_start(message: Message, session: AsyncSession, state: FSMContext) -> None:
    await state.clear()
    curator = await session.get(Curator, message.from_user.id)
    if curator:
        await message.answer(
            f"👋 Привет, <b>{curator.full_name}</b>!\n\nДобро пожаловать в <b>TOM Admin</b>.",
            reply_markup=main_menu_keyboard(),
        )
        return

    sheets = get_sheets()
    names = sheets.get_curator_names()
    if not names:
        await message.answer("😔 Список кураторов пуст. Обратись к администратору.")
        return

    await message.answer(
        "👋 Привет! Выбери своё имя из списка:",
        reply_markup=curator_names_keyboard(names),
    )


@router.callback_query(F.data.startswith("curator_name:"))
async def on_curator_selected(call: CallbackQuery, session: AsyncSession) -> None:
    full_name = call.data.split(":", 1)[1]
    sheets = get_sheets()
    groups = sheets.get_curator_groups(full_name)

    if not groups:
        await call.answer("Имя не найдено.", show_alert=True)
        return

    existing = await session.get(Curator, call.from_user.id)
    if existing:
        await call.answer("Ты уже зарегистрирован.", show_alert=True)
        return

    session.add(Curator(
        telegram_id=call.from_user.id,
        username=call.from_user.username,
        full_name=full_name,
    ))
    await session.flush()

    for g in groups:
        session.add(CuratorGroup(
            curator_id=call.from_user.id,
            stream_name=g["stream_name"],
            group_name=g["group_name"],
        ))
    await session.flush()

    groups_text = "\n".join(f"  • {g['stream_name']} / {g['group_name']}" for g in groups)
    await call.message.edit_text(
        f"✅ <b>Регистрация завершена!</b>\n\nТвои группы:\n{groups_text}\n\nДобро пожаловать! 🎉",
        reply_markup=main_menu_keyboard(),
    )
    await call.answer()


@router.callback_query(F.data == "back:main_menu")
async def back_main(call: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await call.message.edit_text("Главное меню:", reply_markup=main_menu_keyboard())
    await call.answer()


@router.callback_query(F.data == "action:new_practice")
async def on_new_practice(
    call: CallbackQuery, session: AsyncSession, curator: Curator, state: FSMContext
) -> None:
    await state.clear()
    result = await session.execute(
        select(CuratorGroup).where(CuratorGroup.curator_id == curator.telegram_id)
    )
    curator_groups = result.scalars().all()

    if not curator_groups:
        await call.answer("У тебя нет назначенных групп.", show_alert=True)
        return

    groups = [(cg.stream_name, cg.group_name) for cg in curator_groups]
    await call.message.edit_text(
        "Выбери <b>группу</b> для практики:",
        reply_markup=groups_keyboard(groups),
    )
    await call.answer()


@router.callback_query(F.data.startswith("pg:"))
async def on_group_selected(call: CallbackQuery, state: FSMContext) -> None:
    _, stream_name, group_name = call.data.split(":", 2)
    await state.update_data(stream_name=stream_name, group_name=group_name)
    await state.set_state(PracticeForm.waiting_for_datetime)
    await call.message.edit_text(
        f"👥 Группа: <b>{group_name}</b> ({stream_name})\n\n"
        f"Введи дату и время практики:\n"
        f"<code>ДД.ММ.ГГГГ ЧЧ:ММ</code>\n\n"
        f"Например: <code>15.06.2026 18:00</code>",
    )
    await call.answer()


@router.message(PracticeForm.waiting_for_datetime)
async def on_datetime_input(message: Message, state: FSMContext) -> None:
    raw = (message.text or "").strip()
    try:
        dt = TZ.localize(datetime.strptime(raw, "%d.%m.%Y %H:%M"))
    except ValueError:
        await message.answer("❌ Неверный формат. Попробуй:\n<code>ДД.ММ.ГГГГ ЧЧ:ММ</code>")
        return

    if dt < datetime.now(TZ):
        await message.answer("❌ Эта дата уже прошла.")
        return

    fsm = await state.get_data()
    await state.update_data(scheduled_at=dt.isoformat())

    await message.answer(
        f"Проверь данные:\n\n"
        f"👥 Группа: <b>{fsm['group_name']}</b> ({fsm['stream_name']})\n"
        f"🗓 Дата: <b>{dt.strftime('%d.%m.%Y в %H:%M')}</b>\n\n"
        f"Всё верно?",
        reply_markup=confirm_practice_keyboard(),
    )


@router.callback_query(F.data == "confirm_practice")
async def on_confirm(
    call: CallbackQuery, session: AsyncSession, curator: Curator, state: FSMContext
) -> None:
    fsm = await state.get_data()
    scheduled_at = datetime.fromisoformat(fsm["scheduled_at"])

    session.add(Practice(
        group_name=fsm["group_name"],
        stream_name=fsm["stream_name"],
        curator_id=curator.telegram_id,
        practice_type=PracticeType.curator,
        scheduled_at=scheduled_at,
    ))
    await session.flush()
    await state.clear()

    dt_str = scheduled_at.astimezone(TZ).strftime("%d.%m.%Y в %H:%M")
    await call.message.edit_text(
        f"✅ <b>Практика назначена!</b>\n\n"
        f"👥 {fsm['group_name']} ({fsm['stream_name']})\n"
        f"🗓 <b>{dt_str}</b>\n\n"
        f"Ученики получат напоминание за 1 час.",
    )
    await call.answer("✅ Сохранено!")


@router.callback_query(F.data == "change_date")
async def on_change_date(call: CallbackQuery, state: FSMContext) -> None:
    fsm = await state.get_data()
    await state.set_state(PracticeForm.waiting_for_datetime)
    await call.message.edit_text(
        f"👥 Группа: <b>{fsm.get('group_name', '')}</b>\n\n"
        f"Введи новую дату:\n<code>ДД.ММ.ГГГГ ЧЧ:ММ</code>",
    )
    await call.answer()


@router.callback_query(F.data == "action:my_practices")
async def on_my_practices(
    call: CallbackQuery, session: AsyncSession, curator: Curator
) -> None:
    now = datetime.now(TZ)
    result = await session.execute(
        select(Practice)
        .where(Practice.curator_id == curator.telegram_id, Practice.scheduled_at > now)
        .order_by(Practice.scheduled_at)
        .limit(10)
    )
    practices = result.scalars().all()

    if not practices:
        await call.message.edit_text("📭 Предстоящих практик нет.", reply_markup=main_menu_keyboard())
        await call.answer()
        return

    await call.message.edit_text(
        f"📋 Предстоящие практики ({len(practices)}):",
        reply_markup=practices_keyboard(practices),
    )
    await call.answer()


@router.callback_query(F.data.startswith("cancel:"))
async def on_cancel(
    call: CallbackQuery, session: AsyncSession, curator: Curator
) -> None:
    practice_id = int(call.data.split(":")[1])
    practice = await session.get(Practice, practice_id)

    if not practice or practice.curator_id != curator.telegram_id:
        await call.answer("Практика не найдена.", show_alert=True)
        return

    await session.delete(practice)
    await session.flush()
    await call.answer("🗑 Удалено.", show_alert=True)

    now = datetime.now(TZ)
    result = await session.execute(
        select(Practice)
        .where(Practice.curator_id == curator.telegram_id, Practice.scheduled_at > now)
        .order_by(Practice.scheduled_at).limit(10)
    )
    practices = result.scalars().all()

    if not practices:
        await call.message.edit_text("📭 Практик больше нет.", reply_markup=main_menu_keyboard())
    else:
        await call.message.edit_reply_markup(reply_markup=practices_keyboard(practices))
