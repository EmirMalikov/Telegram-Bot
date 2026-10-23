"""
utils/helpers.py — small shared helpers used across handlers.
"""
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import Message


async def safe_edit_text(message: Message, text: str, reply_markup=None):
    """Edit a message's text.

    Telegram refuses to edit the *text* of a message that was sent as a
    photo (it only has a caption) — that raises TelegramBadRequest
    ("there is no text in the message to edit"). This happens whenever the
    bot navigates away from a city/product card that has a photo.

    In that case, delete the old (photo) message and send a fresh text
    message instead, so navigation never crashes.
    """
    try:
        await message.edit_text(text, reply_markup=reply_markup)
    except TelegramBadRequest as e:
        if "there is no text in the message to edit" not in str(e):
            raise
        await message.delete()
        await message.answer(text, reply_markup=reply_markup)
