from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def streams_keyboard(stream_names: list[str]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for name in stream_names:
        builder.button(text=name, callback_data=f"stream:{name}")
    builder.adjust(1)
    return builder.as_markup()


def groups_keyboard(group_names: list[str]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for name in group_names:
        builder.button(text=name, callback_data=f"group:{name}")
    builder.button(text="‹ Назад", callback_data="back:streams")
    builder.adjust(1)
    return builder.as_markup()


def confirm_keyboard(stream: str, group: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Подтвердить", callback_data=f"confirm:{stream}:{group}")
    builder.button(text="‹ Изменить", callback_data="back:streams")
    builder.adjust(1)
    return builder.as_markup()
