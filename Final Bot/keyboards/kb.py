"""
keyboards/kb.py — all keyboards used in the project (Inline + Reply).
"""
from typing import List, Optional

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

import aiosqlite


def remove_kb() -> ReplyKeyboardRemove:
    return ReplyKeyboardRemove()


def skip_photo_kb() -> InlineKeyboardMarkup:
    """One-button inline keyboard offered on every 'send a photo' admin step,
    so skipping the photo is a tap instead of having to type «—»."""
    b = InlineKeyboardBuilder()
    b.button(text="⏭ Skip photo", callback_data="adm_skip_photo")
    return b.as_markup()


# ══════════════════════════════════════════════════════════════════════
#  MAIN MENU
# ══════════════════════════════════════════════════════════════════════

def main_menu_kb() -> ReplyKeyboardMarkup:
    b = ReplyKeyboardBuilder()
    b.row(KeyboardButton(text="🛍 Catalog"), KeyboardButton(text="🛒 Cart"))
    b.row(KeyboardButton(text="👤 Profile"), KeyboardButton(text="⭐ Deals"))
    b.row(KeyboardButton(text="📞 Support"), KeyboardButton(text="❓ FAQ"))
    return b.as_markup(resize_keyboard=True)


# ══════════════════════════════════════════════════════════════════════
#  CITIES
# ══════════════════════════════════════════════════════════════════════

def cities_kb(cities: list) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for city in cities:
        b.button(text=city["name"], callback_data=f"city:{city['id']}")
    b.adjust(2)
    return b.as_markup()


def city_selected_kb(city_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="🛍 Catalog", callback_data=f"cat_list:{city_id}")
    b.button(text="⭐ Deals", callback_data=f"city_sales:{city_id}")
    b.button(text="🔄 Change city", callback_data="choose_city")
    b.adjust(2, 1)
    return b.as_markup()


# ══════════════════════════════════════════════════════════════════════
#  CATALOG / CATEGORIES
# ══════════════════════════════════════════════════════════════════════

def categories_kb(categories: list, city_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for cat in categories:
        b.button(text=f"{cat['emoji']} {cat['name']}", callback_data=f"cat:{cat['id']}")
    b.button(text="🔄 Change city", callback_data="choose_city")
    b.adjust(2)
    return b.as_markup()


def products_kb(products: list, cat_id: int, city_id: int, page: int = 0, per_page: int = 8) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    start = page * per_page
    chunk = products[start:start + per_page]
    for p in chunk:
        stock_icon = "✅" if p["stock"] > 0 else "❌"
        b.button(text=f"{stock_icon} {p['name']} — {p['price']} $", callback_data=f"prod:{p['id']}")
    b.adjust(1)

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀️", callback_data=f"prod_page:{cat_id}:{page-1}"))
    if start + per_page < len(products):
        nav.append(InlineKeyboardButton(text="▶️", callback_data=f"prod_page:{cat_id}:{page+1}"))
    if nav:
        b.row(*nav)

    b.row(InlineKeyboardButton(text="◀️ Categories", callback_data=f"cat_list:{city_id}"))
    return b.as_markup()


def product_detail_kb(product_id: int, cat_id: int, city_id: int, in_fav: bool = False) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="🛒 Add to cart", callback_data=f"add_cart:{product_id}")
    fav_text = "💔 Remove from favorites" if in_fav else "❤️ Add to favorites"
    b.button(text=fav_text, callback_data=f"fav:{product_id}")
    b.button(text="◀️ Back", callback_data=f"cat:{cat_id}")
    b.adjust(1)
    return b.as_markup()


# ══════════════════════════════════════════════════════════════════════
#  CART
# ══════════════════════════════════════════════════════════════════════

def cart_kb(items: list, total: float) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for item in items:
        b.button(
            text=f"❌ {item['name']} ×{item['quantity']}",
            callback_data=f"cart_del:{item['product_id']}",
        )
    b.adjust(1)
    b.row(
        InlineKeyboardButton(text="➕", callback_data="cart_add_qty"),
        InlineKeyboardButton(text="🗑 Clear", callback_data="cart_clear"),
    )
    b.row(InlineKeyboardButton(text=f"💳 Pay {total:.2f} $", callback_data="checkout"))
    return b.as_markup()


def payment_kb(order_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="✅ I've paid", callback_data=f"paid_check:{order_id}")
    b.button(text="❌ Cancel", callback_data=f"cancel_order:{order_id}")
    b.adjust(1)
    return b.as_markup()


def promo_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="🏷 Enter promo code", callback_data="enter_promo")
    b.button(text="💳 Pay without a discount", callback_data="checkout_no_promo")
    b.adjust(1)
    return b.as_markup()


# ══════════════════════════════════════════════════════════════════════
#  PROFILE
# ══════════════════════════════════════════════════════════════════════

def profile_kb(user_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="📋 My orders", callback_data="my_orders")
    b.button(text="❤️ Favorites", callback_data="my_fav")
    b.button(text="🔗 Referral link", callback_data="my_ref")
    b.button(text="🏙 Change city", callback_data="choose_city")
    b.adjust(2, 1, 1)
    return b.as_markup()


def orders_kb(orders: list) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for o in orders:
        status_icon = {"paid": "✅", "pending": "⏳", "cancelled": "❌"}.get(o["status"], "🔄")
        b.button(
            text=f"{status_icon} Order #{o['id']} — {o['total_price']:.2f}$",
            callback_data=f"order_detail:{o['id']}",
        )
    b.button(text="◀️ Profile", callback_data="back_profile")
    b.adjust(1)
    return b.as_markup()


# ══════════════════════════════════════════════════════════════════════
#  ADMIN
# ══════════════════════════════════════════════════════════════════════

def admin_main_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="📊 Statistics", callback_data="adm_stats")
    b.button(text="🏙 Cities", callback_data="adm_cities")
    b.button(text="🗂 Categories", callback_data="adm_cats")
    b.button(text="📦 Products", callback_data="adm_products")
    b.button(text="🏷 Promo codes", callback_data="adm_promos")
    b.button(text="💳 Payment methods", callback_data="adm_pay_methods")
    b.button(text="📣 Broadcast", callback_data="adm_broadcast")
    b.button(text="👥 Users", callback_data="adm_users")
    b.button(text="📋 Orders", callback_data="adm_orders")
    b.adjust(2)
    return b.as_markup()


def adm_pay_methods_kb(methods: list) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for m in methods:
        status_icon = "✅" if m["is_active"] else "❌"
        b.button(text=f"{status_icon} {m['name']}", callback_data=f"adm_pay_view:{m['id']}")
    b.button(text="➕ Add payment method", callback_data="adm_pay_add")
    b.button(text="◀️ Back", callback_data="adm_main")
    b.adjust(1)
    return b.as_markup()


def adm_pay_actions_kb(method_id: int, is_active: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    toggle_text = "❌ Disable" if is_active else "✅ Enable"
    b.button(text=toggle_text, callback_data=f"adm_pay_toggle:{method_id}")
    b.button(text="✏️ Edit", callback_data=f"adm_pay_edit:{method_id}")
    b.button(text="🗑 Delete", callback_data=f"adm_pay_delete:{method_id}")
    b.button(text="◀️ Back to payment methods", callback_data="adm_pay_methods")
    b.adjust(1)
    return b.as_markup()


def adm_pay_edit_kb(method_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="📝 Name", callback_data=f"adm_pay_edit_field:{method_id}:name")
    b.button(text="📄 Description", callback_data=f"adm_pay_edit_field:{method_id}:description")
    b.button(text="💬 Payment details", callback_data=f"adm_pay_edit_field:{method_id}:details")
    b.button(text="🔢 Sort order", callback_data=f"adm_pay_edit_field:{method_id}:sort_order")
    b.button(text="◀️ Back", callback_data=f"adm_pay_view:{method_id}")
    b.adjust(2)
    return b.as_markup()


def payment_methods_kb(methods: list, order_id: int) -> InlineKeyboardMarkup:
    """Keyboard for the customer to choose a payment method."""
    b = InlineKeyboardBuilder()
    for m in methods:
        b.button(text=m["name"], callback_data=f"select_pay_method:{order_id}:{m['id']}")
    b.button(text="❌ Cancel order", callback_data=f"cancel_order:{order_id}")
    b.adjust(1)
    return b.as_markup()


def adm_orders_kb(orders: list) -> InlineKeyboardMarkup:
    """List of orders for the admin — each button opens the detail view."""
    b = InlineKeyboardBuilder()
    status_icon = {"paid": "✅", "pending": "⏳", "cancelled": "❌"}
    for o in orders:
        icon = status_icon.get(o["status"], "🔄")
        name = o["first_name"] or o["username"] or str(o["user_id"])
        b.button(
            text=f"{icon} #{o['id']} | {name} | {o['total_price']:.2f}$",
            callback_data=f"adm_order_detail:{o['id']}",
        )
    b.button(text="◀️ Back", callback_data="adm_main")
    b.adjust(1)
    return b.as_markup()


def adm_order_detail_kb(order_id: int, status: str) -> InlineKeyboardMarkup:
    """Keyboard for the admin's order detail view."""
    b = InlineKeyboardBuilder()
    if status == "pending":
        b.button(text="✅ Confirm payment", callback_data=f"adm_confirm_pay:{order_id}")
    if status == "paid":
        b.button(text="✏️ Edit fulfillment details", callback_data=f"adm_edit_pickup:{order_id}")
    b.button(text="◀️ Back to orders", callback_data="adm_orders")
    b.adjust(1)
    return b.as_markup()


def adm_fulfill_cancel_kb(order_id: int) -> InlineKeyboardMarkup:
    """Cancel button for the current fulfillment-data step — returns to the order card."""
    b = InlineKeyboardBuilder()
    b.button(text="❌ Cancel", callback_data=f"adm_order_detail:{order_id}")
    return b.as_markup()


def location_request_kb() -> ReplyKeyboardMarkup:
    """Reply keyboard with a share-location button (for the pickup-point step)."""
    b = ReplyKeyboardBuilder()
    b.button(text="📍 Share location", request_location=True)
    return b.as_markup(resize_keyboard=True, one_time_keyboard=True)



def admin_back_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="◀️ Admin panel", callback_data="adm_main")
    return b.as_markup()


# ── Cities (admin) ──────────────────────────────────────────────────

def adm_cities_kb(cities: list) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for city in cities:
        status = "✅" if city["is_active"] else "❌"
        b.button(
            text=f"{status} {city['name']}",
            callback_data=f"adm_city_view:{city['id']}",
        )
    b.button(text="➕ Add city", callback_data="adm_city_add")
    b.button(text="◀️ Back", callback_data="adm_main")
    b.adjust(2, 1, 1)
    return b.as_markup()


def adm_city_actions_kb(city_id: int, is_active: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    toggle_text = "🔴 Disable" if is_active else "🟢 Enable"
    b.button(text="✏️ Name", callback_data=f"adm_city_edit_name:{city_id}")
    b.button(text="📝 Description", callback_data=f"adm_city_edit_desc:{city_id}")
    b.button(text="🖼 Photo", callback_data=f"adm_city_edit_photo:{city_id}")
    b.button(text="🔢 Sort order", callback_data=f"adm_city_edit_order:{city_id}")
    b.button(text=toggle_text, callback_data=f"adm_city_toggle:{city_id}")
    b.button(text="🗑 Delete", callback_data=f"adm_city_delete:{city_id}")
    b.button(text="◀️ Back to cities", callback_data="adm_cities")
    b.adjust(2, 2, 2, 1)
    return b.as_markup()


def adm_city_confirm_delete_kb(city_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="✅ Yes, delete", callback_data=f"adm_city_delete_confirm:{city_id}")
    b.button(text="❌ Cancel", callback_data=f"adm_city_view:{city_id}")
    b.adjust(2)
    return b.as_markup()


# ── Categories (admin) ────────────────────────────────────────────────

def adm_cats_select_city_kb(cities: list) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for city in cities:
        b.button(text=city["name"], callback_data=f"adm_cats_city:{city['id']}")
    b.button(text="◀️ Back", callback_data="adm_main")
    b.adjust(2, 1)
    return b.as_markup()


def adm_cats_kb(categories: list, city_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for cat in categories:
        status = "✅" if cat["is_active"] else "❌"
        b.button(
            text=f"{status} {cat['emoji']} {cat['name']}",
            callback_data=f"adm_cat_view:{cat['id']}",
        )
    b.button(text="➕ Add category", callback_data=f"adm_cat_add:{city_id}")
    b.button(text="◀️ Back to cities", callback_data="adm_cats")
    b.adjust(1)
    return b.as_markup()


def adm_cat_actions_kb(cat_id: int, city_id: int, is_active: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    toggle_text = "🔴 Disable" if is_active else "🟢 Enable"
    b.button(text="✏️ Name", callback_data=f"adm_cat_edit_name:{cat_id}")
    b.button(text="😀 Emoji", callback_data=f"adm_cat_edit_emoji:{cat_id}")
    b.button(text="🔢 Sort order", callback_data=f"adm_cat_edit_order:{cat_id}")
    b.button(text=toggle_text, callback_data=f"adm_cat_toggle:{cat_id}")
    b.button(text="🗑 Delete", callback_data=f"adm_cat_delete:{cat_id}")
    b.button(text="◀️ Back to categories", callback_data=f"adm_cats_city:{city_id}")
    b.adjust(2, 2, 1, 1)
    return b.as_markup()


# ── Products (admin) ───────────────────────────────────────────────────

def adm_products_select_city_kb(cities: list) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for city in cities:
        b.button(text=city["name"], callback_data=f"adm_prods_city:{city['id']}")
    b.button(text="◀️ Back", callback_data="adm_main")
    b.adjust(2, 1)
    return b.as_markup()


def adm_products_select_cat_kb(cats: list, city_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for cat in cats:
        b.button(text=f"{cat['emoji']} {cat['name']}", callback_data=f"adm_prods_cat:{cat['id']}:{city_id}")
    b.button(text="◀️ Back to cities", callback_data="adm_products")
    b.adjust(2, 1)
    return b.as_markup()


def adm_products_kb(products: list, cat_id: int, city_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for p in products:
        status = "✅" if p["is_active"] else "❌"
        b.button(
            text=f"{status} {p['name']} ({p['price']}$)",
            callback_data=f"adm_prod_view:{p['id']}",
        )
    b.button(text="➕ Add product", callback_data=f"adm_prod_add:{cat_id}:{city_id}")
    b.button(text="◀️ Back to categories", callback_data=f"adm_prods_city:{city_id}")
    b.adjust(1)
    return b.as_markup()


def adm_product_actions_kb(product_id: int, cat_id: int, city_id: int, is_active: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    toggle_text = "🔴 Disable" if is_active else "🟢 Enable"
    b.button(text="✏️ Name", callback_data=f"adm_prod_edit:name:{product_id}")
    b.button(text="📝 Description", callback_data=f"adm_prod_edit:desc:{product_id}")
    b.button(text="💰 Price", callback_data=f"adm_prod_edit:price:{product_id}")
    b.button(text="🏷 Old price", callback_data=f"adm_prod_edit:old_price:{product_id}")
    b.button(text="📦 Stock", callback_data=f"adm_prod_edit:stock:{product_id}")
    b.button(text="🖼 Photo", callback_data=f"adm_prod_edit:photo:{product_id}")
    b.button(text=toggle_text, callback_data=f"adm_prod_toggle:{product_id}")
    b.button(text="🗑 Delete", callback_data=f"adm_prod_delete:{product_id}:{cat_id}:{city_id}")
    b.button(text="◀️ Back to products", callback_data=f"adm_prods_cat:{cat_id}:{city_id}")
    b.adjust(2, 2, 2, 2, 1)
    return b.as_markup()


def adm_prod_confirm_delete_kb(product_id: int, cat_id: int, city_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="✅ Yes, delete", callback_data=f"adm_prod_delete_confirm:{product_id}:{cat_id}:{city_id}")
    b.button(text="❌ Cancel", callback_data=f"adm_prod_view:{product_id}")
    b.adjust(2)
    return b.as_markup()


# ── Promo codes (admin) ────────────────────────────────────────────────

def adm_promos_kb(promos: list) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for p in promos:
        status = "✅" if p["is_active"] else "❌"
        b.button(
            text=f"{status} {p['code']} ({p['discount_value']}{'%' if p['discount_type']=='percent' else '$'})",
            callback_data=f"adm_promo_view:{p['id']}",
        )
    b.button(text="➕ Add promo code", callback_data="adm_promo_add")
    b.button(text="◀️ Back", callback_data="adm_main")
    b.adjust(1)
    return b.as_markup()


def adm_promo_actions_kb(promo_id: int, is_active: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    toggle_text = "🔴 Disable" if is_active else "🟢 Enable"
    b.button(text=toggle_text, callback_data=f"adm_promo_toggle:{promo_id}")
    b.button(text="🗑 Delete", callback_data=f"adm_promo_delete:{promo_id}")
    b.button(text="◀️ Back to promo codes", callback_data="adm_promos")
    b.adjust(2, 1)
    return b.as_markup()


# ── Users (admin) ─────────────────────────────────────────────

def adm_user_actions_kb(tg_id: int, is_banned: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    toggle_text = "🔓 Unban" if is_banned else "🚫 Ban"
    b.button(text=toggle_text, callback_data=f"adm_user_ban:{tg_id}")
    b.button(text="◀️ Back to users", callback_data="adm_users")
    b.adjust(1)
    return b.as_markup()
