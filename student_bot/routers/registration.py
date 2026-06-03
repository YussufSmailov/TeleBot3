from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models import Student
from shared.sheets import get_sheets
from student_bot.keyboards.inline import (
    confirm_keyboard,
    groups_keyboard,
    streams_keyboard,
)

router = Router(name="registration")


@router.message(CommandStart())
async def cmd_start(message: Message, session: AsyncSession) -> None:
    # Сбрасываем регистрацию чтобы можно было выбрать заново
    student = await session.get(Student, message.from_user.id)
    if student:
        student.group_name = None
        student.stream_name = None
        await session.flush()

    sheets = get_sheets()
    streams = sheets.get_streams()

    if not streams:
        await message.answer("😔 Пока нет активных потоков. Следи за анонсами!")
        return

    await message.answer(
        "👋 Привет! Добро пожаловать в <b>TOM 2.0</b>.\n\n"
        "Выбери свой <b>поток</b>:",
        reply_markup=streams_keyboard([s.name for s in streams]),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("stream:"))
async def on_stream_selected(call: CallbackQuery) -> None:
    stream_name = call.data.split(":", 1)[1]
    sheets = get_sheets()
    groups = sheets.get_groups_for_stream(stream_name)

    if not groups:
        await call.answer("В этом потоке нет групп.", show_alert=True)
        return

    await call.message.edit_text(
        f"✅ Поток: <b>{stream_name}</b>\n\nВыбери свою <b>группу</b>:",
        reply_markup=groups_keyboard(groups),
        parse_mode="HTML",
    )
    await call.answer()


@router.callback_query(F.data == "back:streams")
async def on_back(call: CallbackQuery) -> None:
    sheets = get_sheets()
    streams = sheets.get_streams()
    await call.message.edit_text(
        "Выбери свой <b>поток</b>:",
        reply_markup=streams_keyboard([s.name for s in streams]),
        parse_mode="HTML",
    )
    await call.answer()


@router.callback_query(F.data.startswith("group:"))
async def on_group_selected(call: CallbackQuery) -> None:
    group_name = call.data.split(":", 1)[1]

    # Достаём stream_name из текста сообщения
    text = call.message.text or ""
    stream_name = ""
    for line in text.split("\n"):
        if "Поток:" in line:
            stream_name = line.split("Поток:")[-1].strip().replace("*", "").replace("_", "")
            break

    await call.message.edit_text(
        f"Ты выбрал:\n\n"
        f"🌊 Поток: <b>{stream_name}</b>\n"
        f"👥 Группа: <b>{group_name}</b>\n\n"
        f"Всё верно?",
        reply_markup=confirm_keyboard(stream_name, group_name),
        parse_mode="HTML",
    )
    await call.answer()


@router.callback_query(F.data.startswith("confirm:"))
async def on_confirm(call: CallbackQuery, session: AsyncSession) -> None:
    parts = call.data.split(":", 2)
    stream_name = parts[1]
    group_name = parts[2]

    student = await session.get(Student, call.from_user.id)
    if student:
        student.stream_name = stream_name
        student.group_name = group_name
        student.username = call.from_user.username
        student.full_name = call.from_user.full_name
    else:
        student = Student(
            telegram_id=call.from_user.id,
            username=call.from_user.username,
            full_name=call.from_user.full_name,
            stream_name=stream_name,
            group_name=group_name,
        )
        session.add(student)

    await session.flush()

    await call.message.edit_text(
        f"🎉 <b>Регистрация завершена!</b>\n\n"
        f"🌊 Поток: <b>{stream_name}</b>\n"
        f"👥 Группа: <b>{group_name}</b>\n\n"
        f"Жди уведомлений о новых уроках и практиках. Удачи! 🚀",
        parse_mode="HTML",
    )
    await call.answer("✅ Готово!")
