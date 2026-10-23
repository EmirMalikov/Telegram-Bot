"""
handlers/profile.py — profile, order history, favorites, referrals.
"""
import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from config.settings import settings
from utils.helpers import safe_edit_text
from database.db import (
    get_favorites,
    get_order,
    get_order_items,
    get_referrals_count,
    get_user,
    get_user_orders,
)
from keyboards.kb import orders_kb, profile_kb

logger = logging.getLogger(__name__)
router = Router()


@router.message(F.text == "👤 Profile")
async def btn_profile(message: Message):
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer("User not found. /start")
        return

    refs = await get_referrals_count(message.from_user.id)
    city_name = "not set"
    if user["city_id"]:
        from database.db import get_city
        city = await get_city(user["city_id"])
        if city:
            city_name = city["name"]

    text = (
        f"👤 <b>Profile</b>\n\n"
        f"🆔 ID: <code>{user['tg_id']}</code>\n"
        f"👤 Name: {user['first_name']} {user['last_name'] or ''}\n"
        f"🏙 City: {city_name}\n"
        f"🔗 Referrals: {refs}\n"
        f"📅 Joined: {user['created_at'][:10]}"
    )
    await message.answer(text, reply_markup=profile_kb(user["tg_id"]))


@router.callback_query(F.data == "back_profile")
async def cb_back_profile(call: CallbackQuery):
    user = await get_user(call.from_user.id)
    refs = await get_referrals_count(call.from_user.id)
    city_name = "not set"
    if user["city_id"]:
        from database.db import get_city
        city = await get_city(user["city_id"])
        if city:
            city_name = city["name"]

    text = (
        f"👤 <b>Profile</b>\n\n"
        f"🆔 ID: <code>{user['tg_id']}</code>\n"
        f"👤 Name: {user['first_name']} {user['last_name'] or ''}\n"
        f"🏙 City: {city_name}\n"
        f"🔗 Referrals: {refs}\n"
        f"📅 Joined: {user['created_at'][:10]}"
    )
    await safe_edit_text(call.message, text, reply_markup=profile_kb(user["tg_id"]))
    await call.answer()


@router.callback_query(F.data == "my_orders")
async def cb_my_orders(call: CallbackQuery):
    orders = await get_user_orders(call.from_user.id, limit=10)
    if not orders:
        await safe_edit_text(call.message, 
            "📋 You don't have any orders yet.\n\nGo to the catalog and make your first purchase!",
            reply_markup=orders_kb([]),
        )
        await call.answer()
        return
    await safe_edit_text(call.message, 
        f"📋 <b>Your orders</b> (last {len(orders)}):",
        reply_markup=orders_kb(orders),
    )
    await call.answer()


@router.callback_query(F.data.startswith("order_detail:"))
async def cb_order_detail(call: CallbackQuery):
    order_id = int(call.data.split(":")[1])
    order = await get_order(order_id)
    if not order or order["user_id"] != call.from_user.id:
        await call.answer("Order not found.", show_alert=True)
        return

    items = await get_order_items(order_id)
    status_map = {
        "pending": "⏳ Awaiting payment",
        "paid": "✅ Paid",
        "cancelled": "❌ Cancelled",
    }
    status = status_map.get(order["status"], order["status"])

    text = (
        f"📦 <b>Order #{order_id}</b>\n\n"
        f"Status: {status}\n"
        f"Date: {order['created_at'][:16]}\n\n"
        f"<b>Items:</b>\n"
    )
    for item in items:
        text += f"• {item['name']} × {item['quantity']} = {item['price'] * item['quantity']:.2f}$\n"

    if order["discount"] > 0:
        text += f"\nDiscount: -{order['discount']:.2f}$"
    text += f"\n\n💰 <b>Total: {order['total_price']:.2f}$</b>"

    from aiogram.utils.keyboard import InlineKeyboardBuilder
    b = InlineKeyboardBuilder()
    b.button(text="◀️ My orders", callback_data="my_orders")

    await safe_edit_text(call.message, text, reply_markup=b.as_markup())
    await call.answer()


@router.callback_query(F.data == "my_fav")
async def cb_my_fav(call: CallbackQuery):
    favs = await get_favorites(call.from_user.id)
    if not favs:
        from aiogram.utils.keyboard import InlineKeyboardBuilder
        b = InlineKeyboardBuilder()
        b.button(text="◀️ Profile", callback_data="back_profile")
        await safe_edit_text(call.message, "❤️ You have no favorite products.", reply_markup=b.as_markup())
        await call.answer()
        return

    text = "❤️ <b>Favorites:</b>\n\n"
    for p in favs:
        text += f"• <b>{p['name']}</b> — {p['price']}$\n"

    from aiogram.utils.keyboard import InlineKeyboardBuilder
    b = InlineKeyboardBuilder()
    b.button(text="◀️ Profile", callback_data="back_profile")
    await safe_edit_text(call.message, text, reply_markup=b.as_markup())
    await call.answer()


@router.callback_query(F.data == "my_ref")
async def cb_my_ref(call: CallbackQuery):
    bot_username = settings.shop_username.lstrip("@")
    ref_link = f"https://t.me/{bot_username}?start={call.from_user.id}"
    refs = await get_referrals_count(call.from_user.id)

    from aiogram.utils.keyboard import InlineKeyboardBuilder
    b = InlineKeyboardBuilder()
    b.button(text="◀️ Profile", callback_data="back_profile")

    await safe_edit_text(call.message, 
        f"🔗 <b>Referral program</b>\n\n"
        f"Your link:\n<code>{ref_link}</code>\n\n"
        f"Friends invited: <b>{refs}</b>",
        reply_markup=b.as_markup(),
    )
    await call.answer()
