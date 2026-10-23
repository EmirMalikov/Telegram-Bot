"""
config/settings.py — environment variable loading.
"""
import os
from dataclasses import dataclass, field
from typing import List

from dotenv import load_dotenv

load_dotenv()


def _parse_ids(raw: str) -> List[int]:
    """Parse a string like '123,456' into a list of int."""
    result = []
    for part in raw.split(","):
        part = part.strip().split("#")[0].strip()  # strip inline comments
        if part.isdigit():
            result.append(int(part))
    return result


@dataclass
class Settings:
    # Telegram
    bot_token: str = field(default_factory=lambda: os.getenv("BOT_TOKEN", ""))
    admin_ids: List[int] = field(
        default_factory=lambda: _parse_ids(os.getenv("ADMIN_IDS", ""))
    )

    # Shop
    shop_name: str = field(default_factory=lambda: os.getenv("SHOP_NAME", "Shop"))
    shop_username: str = field(default_factory=lambda: os.getenv("SHOP_USERNAME", ""))

    # Payment
    usdt_wallet: str = field(default_factory=lambda: os.getenv("USDT_WALLET", ""))
    payment_timeout_minutes: int = field(
        default_factory=lambda: int(os.getenv("PAYMENT_TIMEOUT_MINUTES", "30"))
    )
    payment_confirmations: int = field(
        default_factory=lambda: int(os.getenv("PAYMENT_CONFIRMATIONS", "1"))
    )

    # Database
    database_path: str = field(
        default_factory=lambda: os.getenv("DATABASE_PATH", "data/shop.db")
    )

    # Tron
    trongrid_api_key: str = field(
        default_factory=lambda: os.getenv("TRONGRID_API_KEY", "")
    )

    def is_admin(self, user_id: int) -> bool:
        return user_id in self.admin_ids


settings = Settings()
