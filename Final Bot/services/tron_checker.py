"""
services/tron_checker.py — background check of USDT TRC20 payments.
"""
import asyncio
import logging
from typing import Optional

import aiohttp

from config.settings import settings
from database.db import confirm_payment, expire_old_payments, get_pending_payments

logger = logging.getLogger(__name__)

CHECK_INTERVAL = 15          # seconds between loop iterations
AMOUNT_TOLERANCE = 0.01      # allowed USDT amount tolerance
USDT_CONTRACT = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"  # USDT TRC20 contract


async def get_trc20_transactions(wallet: str, session: aiohttp.ClientSession) -> list:
    """Fetch incoming TRC20 transactions from the TronGrid API."""
    url = f"https://api.trongrid.io/v1/accounts/{wallet}/transactions/trc20"
    params = {
        "contract_address": USDT_CONTRACT,
        "limit": 20,
        "only_confirmed": "true",
    }
    headers = {}
    if settings.trongrid_api_key and settings.trongrid_api_key != "your_trongrid_api_key_here":
        headers["TRON-PRO-API-KEY"] = settings.trongrid_api_key

    try:
        async with session.get(url, params=params, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data.get("data", [])
            else:
                logger.warning("TronGrid HTTP %s", resp.status)
                return []
    except asyncio.TimeoutError:
        logger.warning("TronGrid timeout")
        return []
    except Exception as e:
        logger.error("TronGrid error: %s", e)
        return []


def parse_usdt_amount(raw_amount: str) -> float:
    """Convert raw_value (6 decimals) into USDT."""
    try:
        return int(raw_amount) / 1_000_000
    except (ValueError, TypeError):
        return 0.0


async def check_payment(payment: dict, transactions: list) -> Optional[str]:
    """
    Look for a matching transaction.
    Returns tx_hash if found, otherwise None.
    """
    wallet = settings.usdt_wallet.lower()
    needed_amount = payment["amount"]

    for tx in transactions:
        to_addr = tx.get("to", "").lower()
        raw_value = tx.get("value", "0")
        tx_hash = tx.get("transaction_id", "")

        if to_addr != wallet:
            continue

        received = parse_usdt_amount(raw_value)
        if abs(received - needed_amount) <= AMOUNT_TOLERANCE:
            return tx_hash

    return None


async def payment_checker_loop(bot):
    """Background payment-checking loop. Runs as an asyncio.Task."""
    logger.info("💳 Payment checker started (interval=%ds)", CHECK_INTERVAL)
    connector = aiohttp.TCPConnector(limit=10)
    async with aiohttp.ClientSession(connector=connector) as session:
        while True:
            try:
                # First mark expired payments
                await expire_old_payments()

                pending = await get_pending_payments()
                if pending:
                    txs = await get_trc20_transactions(settings.usdt_wallet, session)
                    for payment in pending:
                        tx_hash = await check_payment(dict(payment), txs)
                        if tx_hash:
                            await confirm_payment(payment["order_id"], tx_hash)
                            logger.info(
                                "✅ Payment confirmed: order=%s tx=%s",
                                payment["order_id"], tx_hash,
                            )
                            try:
                                await bot.send_message(
                                    payment["user_id"],
                                    f"✅ <b>Payment confirmed!</b>\n\n"
                                    f"Order #{payment['order_id']} has been paid.\n"
                                    f"TX: <code>{tx_hash}</code>\n\n"
                                    f"Thank you for shopping at {settings.shop_name}! 🌸",
                                )
                            except Exception as e:
                                logger.error("Notify error: %s", e)

            except asyncio.CancelledError:
                logger.info("Payment checker stopped.")
                break
            except Exception as e:
                logger.error("Payment checker error: %s", e, exc_info=True)

            await asyncio.sleep(CHECK_INTERVAL)
