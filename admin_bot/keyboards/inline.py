from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from shared.models import Practice


def main_menu_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📅 Назначить практику", callback_data="action:new_practice")
    builder.button(text="📋 Мои практики", callback_data="action:my_practices")
    builder.adjust(1)
    return builder.as_markup()


def curator_names_keyboard(names: list[str]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for name in names:
        builder.button(text=name, callback_data=f"curator_name:{name}")
    builder.adjust(1)
    return builder.as_markup()


def groups_keyboard(groups: list[tuple[str, str]]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for stream, group in groups:
        builder.button(
            text=f"{group} ({stream})",
            callback_data=f"pg:{stream}:{group}",
        )
    builder.button(text="‹ Назад", callback_data="back:main_menu")
    builder.adjust(1)
    return builder.as_markup()


def confirm_practice_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Подтвердить", callback_data="confirm_practice")
    builder.button(text="✏️ Изменить дату", callback_data="change_date")
    builder.button(text="‹ В меню", callback_data="back:main_menu")
    builder.adjust(1)
    return builder.as_markup()


def practices_keyboard(practices: list[Practice]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for p in practices:
        dt_str = p.scheduled_at.strftime("%d.%m %H:%M")
        builder.button(
            text=f"👤 {dt_str} {p.group_name} — отменить",
            callback_data=f"cancel:{p.id}",
        )
    builder.button(text="‹ В меню", callback_data="back:main_menu")
    builder.adjust(1)
    return builder.as_markup()
