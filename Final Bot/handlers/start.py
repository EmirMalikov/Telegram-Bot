"""
handlers/start.py — /start, FAQ, support.
"""
import logging

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from config.settings import settings
from utils.helpers import safe_edit_text
from database.db import get_all_cities, get_or_create_user, get_user, set_user_city
from keyboards.kb import cities_kb, main_menu_kb

logger = logging.getLogger(__name__)
router = Router()


async def _send_city_selection(message: Message):
    cities = await get_all_cities(active_only=True)
    if not cities:
        await message.answer(
            f"🌸 Welcome to <b>{settings.shop_name}</b>!\n\n"
            "There are no cities available yet. Please contact the admin.",
            reply_markup=main_menu_kb(),
        )
        return
    await message.answer(
        f"🌸 Welcome to <b>{settings.shop_name}</b>!\n\n"
        "🏙 Choose your city:",
        reply_markup=cities_kb(cities),
    )


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    user = message.from_user

    # Referral link
    referrer_id = None
    args = message.text.split()
    if len(args) > 1 and args[1].isdigit():
        ref_id = int(args[1])
        if ref_id != user.id:
            referrer_id = ref_id

    await get_or_create_user(
        tg_id=user.id,
        username=user.username or "",
        first_name=user.first_name or "",
        last_name=user.last_name or "",
        referrer_id=referrer_id,
    )

    db_user = await get_user(user.id)
    if db_user and db_user["is_banned"]:
        await message.answer("🚫 You are blocked.")
        return

    # If the city is already set — go straight to the menu
    if db_user and db_user["city_id"]:
        await message.answer(
            f"👋 Welcome back, <b>{user.first_name}</b>!\n\n"
            f"🏙 Your shop: <b>{settings.shop_name}</b>",
            reply_markup=main_menu_kb(),
        )
    else:
        await _send_city_selection(message)


@router.callback_query(F.data == "choose_city")
async def cb_choose_city(call: CallbackQuery, state: FSMContext):
    await state.clear()
    cities = await get_all_cities(active_only=True)
    if not cities:
        await call.answer("No cities available.", show_alert=True)
        return
    await safe_edit_text(call.message, 
        "🏙 Choose your city:",
        reply_markup=cities_kb(cities),
    )
    await call.answer()


@router.callback_query(F.data.startswith("city:"))
async def cb_select_city(call: CallbackQuery, state: FSMContext):
    city_id = int(call.data.split(":")[1])
    await set_user_city(call.from_user.id, city_id)

    from database.db import get_city
    city = await get_city(city_id)
    if not city:
        await call.answer("City not found.", show_alert=True)
        return

    await call.answer(f"✅ City selected: {city['name']}")

    text = f"🏙 <b>{city['name']}</b>\n"
    if city["description"]:
        text += f"\n{city['description']}\n"
    text += "\nChoose an action:"

    from keyboards.kb import city_selected_kb
    if city["photo_id"]:
        try:
            await call.message.answer_photo(
                photo=city["photo_id"],
                caption=text,
                reply_markup=city_selected_kb(city_id),
            )
            await call.message.delete()
        except Exception:
            await safe_edit_text(call.message, text, reply_markup=city_selected_kb(city_id))
    else:
        await safe_edit_text(call.message, text, reply_markup=city_selected_kb(city_id))


# ─── FAQ ──────────────────────────────────────────────────────────────

@router.message(F.text == "❓ FAQ")
async def cmd_faq(message: Message):
    faq_text = (
        "❓ <b>Frequently asked questions</b>\n\n"
        "💳 <b>How do I pay?</b>\n"
        "We accept USDT (TRC20). After placing an order you will get a wallet address.\n\n"
        "⏱ <b>How long does confirmation take?</b>\n"
        "Usually 1-2 minutes. Maximum 30 minutes.\n\n"
        "📦 <b>How do I track my order?</b>\n"
        "Your order status is available under 👤 Profile → 📋 My orders.\n\n"
        "❌ <b>What if I overpaid?</b>\n"
        "Tolerance is ±0.01 USDT. Please contact support.\n\n"
        "🔗 <b>Referral program</b>\n"
        "Invite friends with your link under 👤 Profile."
    )
    await message.answer(faq_text)


# ─── Support ─────────────────────────────────────────────────────────

@router.message(F.text == "📞 Support")
async def cmd_support(message: Message):
    text = (
        "📞 <b>Support</b>\n\n"
        f"For any questions, message us on Telegram:\n"
        f"👉 {settings.shop_username}\n\n"
        "Hours: 10:00 – 22:00 (daily)"
    )
    await message.answer(text)
