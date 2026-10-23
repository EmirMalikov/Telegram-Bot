"""
middlewares/throttle.py — anti-flood (20 requests / 10 sec, 30 sec block).
"""
import time
from collections import defaultdict
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject


class ThrottleMiddleware(BaseMiddleware):
    def __init__(self, rate_limit: int = 20, window: int = 10, block_for: int = 30):
        self.rate_limit = rate_limit
        self.window = window
        self.block_for = block_for
        self._history: Dict[int, list] = defaultdict(list)
        self._blocked: Dict[int, float] = {}

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user_id = None
        if isinstance(event, (Message, CallbackQuery)):
            user_id = event.from_user.id if event.from_user else None

        if user_id is None:
            return await handler(event, data)

        now = time.monotonic()

        # Check whether the user is currently blocked
        if user_id in self._blocked:
            if now < self._blocked[user_id]:
                # Silently ignore requests while the user is blocked
                return
            else:
                del self._blocked[user_id]

        # Drop timestamps outside the sliding window
        self._history[user_id] = [
            t for t in self._history[user_id] if now - t < self.window
        ]

        # Check the rate limit
        if len(self._history[user_id]) >= self.rate_limit:
            self._blocked[user_id] = now + self.block_for
            if isinstance(event, Message):
                await event.answer("⚠️ Too many requests. Please wait 30 seconds.")
            elif isinstance(event, CallbackQuery):
                await event.answer("⚠️ Too many requests!", show_alert=True)
            return

        self._history[user_id].append(now)
        return await handler(event, data)
