"""
handlers/catalog.py — catalog, categories, product cards, deals.
"""
import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from utils.helpers import safe_edit_text
from database.db import (
    get_all_cities,
    get_categories,
    get_category,
    get_city,
    get_favorites,
    get_product,
    get_products,
    get_sale_products,
    get_user,
    toggle_favorite,
)
from keyboards.kb import (
    categories_kb,
    cities_kb,
    product_detail_kb,
    products_kb,
)

logger = logging.getLogger(__name__)
router = Router()


async def _require_city(call: CallbackQuery) -> int | None:
    """Returns the user's city_id or asks them to choose one."""
    user = await get_user(call.from_user.id)
    if not user or not user["city_id"]:
        cities = await get_all_cities(active_only=True)
        await safe_edit_text(call.message, 
            "🏙 First, choose your city:",
            reply_markup=cities_kb(cities),
        )
        await call.answer()
        return None
    return user["city_id"]


# ── "Catalog" button from the main menu ──────────────────────────────

@router.message(F.text == "🛍 Catalog")
async def btn_catalog(message: Message):
    user = await get_user(message.from_user.id)
    if not user or not user["city_id"]:
        cities = await get_all_cities(active_only=True)
        if not cities:
            await message.answer("The catalog is temporarily unavailable.")
            return
        await message.answer("🏙 Choose your city:", reply_markup=cities_kb(cities))
        return

    city_id = user["city_id"]
    city = await get_city(city_id)
    cats = await get_categories(city_id)
    if not cats:
        await message.answer(f"There are no categories in <b>{city['name']}</b> yet.")
        return
    await message.answer(
        f"🛍 <b>Catalog — {city['name']}</b>\n\nChoose a category:",
        reply_markup=categories_kb(cats, city_id),
    )


# ── Category list (by city) ────────────────────────────────────────────

@router.callback_query(F.data.startswith("cat_list:"))
async def cb_cat_list(call: CallbackQuery):
    city_id = int(call.data.split(":")[1])
    city = await get_city(city_id)
    cats = await get_categories(city_id)
    if not cats:
        await call.answer("There are no categories in this city.", show_alert=True)
        return
    await safe_edit_text(call.message, 
        f"🛍 <b>Catalog — {city['name']}</b>\n\nChoose a category:",
        reply_markup=categories_kb(cats, city_id),
    )
    await call.answer()


# ── Products in a category ─────────────────────────────────────────────

@router.callback_query(F.data.startswith("cat:"))
async def cb_category(call: CallbackQuery):
    cat_id = int(call.data.split(":")[1])
    cat = await get_category(cat_id)
    if not cat:
        await call.answer("Category not found.", show_alert=True)
        return

    products = await get_products(cat_id)
    if not products:
        city = await get_city(cat["city_id"])
        await safe_edit_text(call.message, 
            f"{cat['emoji']} <b>{cat['name']}</b>\n\n🚫 No products in stock.",
            reply_markup=categories_kb(
                await get_categories(cat["city_id"]), cat["city_id"]
            ),
        )
        await call.answer()
        return

    await safe_edit_text(call.message, 
        f"{cat['emoji']} <b>{cat['name']}</b>\n\nChoose a product:",
        reply_markup=products_kb(products, cat_id, cat["city_id"]),
    )
    await call.answer()


@router.callback_query(F.data.startswith("prod_page:"))
async def cb_prod_page(call: CallbackQuery):
    _, cat_id, page = call.data.split(":")
    cat_id, page = int(cat_id), int(page)
    cat = await get_category(cat_id)
    products = await get_products(cat_id)
    await safe_edit_text(call.message, 
        f"{cat['emoji']} <b>{cat['name']}</b>\n\nChoose a product:",
        reply_markup=products_kb(products, cat_id, cat["city_id"], page=page),
    )
    await call.answer()


# ── Product card ───────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("prod:"))
async def cb_product(call: CallbackQuery):
    product_id = int(call.data.split(":")[1])
    product = await get_product(product_id)
    if not product:
        await call.answer("Product not found.", show_alert=True)
        return

    cat = await get_category(product["category_id"])

    # Check favorites
    favs = await get_favorites(call.from_user.id)
    fav_ids = {f["id"] for f in favs}
    in_fav = product_id in fav_ids

    # Build the text
    price_line = f"💰 <b>{product['price']} $</b>"
    if product["old_price"] and product["old_price"] > product["price"]:
        discount = round((1 - product["price"] / product["old_price"]) * 100)
        price_line += f" <s>{product['old_price']} $</s> 🔥 -{discount}%"

    stock_line = f"📦 In stock: {'✅ yes' if product['stock'] > 0 else '❌ no'}"
    if product["stock"] > 0:
        stock_line += f" ({product['stock']} pcs.)"

    text = (
        f"🛍 <b>{product['name']}</b>\n\n"
        f"{product['description']}\n\n"
        f"{price_line}\n"
        f"{stock_line}"
    )

    kb = product_detail_kb(product_id, cat["id"], cat["city_id"], in_fav)

    if product["photo_id"]:
        try:
            await call.message.answer_photo(photo=product["photo_id"], caption=text, reply_markup=kb)
            await call.message.delete()
        except Exception:
            await safe_edit_text(call.message, text, reply_markup=kb)
    else:
        try:
            await safe_edit_text(call.message, text, reply_markup=kb)
        except Exception:
            await call.message.answer(text, reply_markup=kb)

    await call.answer()


# ── Favorites ──────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("fav:"))
async def cb_toggle_fav(call: CallbackQuery):
    product_id = int(call.data.split(":")[1])
    added = await toggle_favorite(call.from_user.id, product_id)
    if added:
        await call.answer("❤️ Added to favorites!")
    else:
        await call.answer("💔 Removed from favorites.")


# ── Deals ──────────────────────────────────────────────────────────────

@router.message(F.text == "⭐ Deals")
async def btn_sales(message: Message):
    user = await get_user(message.from_user.id)
    if not user or not user["city_id"]:
        await message.answer("🏙 First, choose your city via /start")
        return

    products = await get_sale_products(user["city_id"])
    if not products:
        await message.answer("⭐ No deals right now. Stay tuned!")
        return

    text = "⭐ <b>Deals and discounts</b>\n\n"
    for p in products:
        discount = round((1 - p["price"] / p["old_price"]) * 100)
        text += f"• <b>{p['name']}</b> — <s>{p['old_price']}$</s> → <b>{p['price']}$</b> 🔥 -{discount}%\n"

    await message.answer(text)


@router.callback_query(F.data.startswith("city_sales:"))
async def cb_city_sales(call: CallbackQuery):
    city_id = int(call.data.split(":")[1])
    products = await get_sale_products(city_id)
    city = await get_city(city_id)

    if not products:
        await call.answer("No deals right now.", show_alert=True)
        return

    text = f"⭐ <b>Deals — {city['name']}</b>\n\n"
    for p in products:
        discount = round((1 - p["price"] / p["old_price"]) * 100)
        text += f"• <b>{p['name']}</b> — <s>{p['old_price']}$</s> → <b>{p['price']}$</b> 🔥 -{discount}%\n"

    from keyboards.kb import city_selected_kb
    await safe_edit_text(call.message, text, reply_markup=city_selected_kb(city_id))
    await call.answer()
