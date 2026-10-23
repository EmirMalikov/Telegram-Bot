"""
handlers/admin.py — the full admin panel.
CRUD: cities, categories, products, promo codes, broadcast, users.
"""
import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from config.settings import settings
from database.db import (
    ban_user,
    create_category,
    create_city,
    create_product,
    create_promo,
    delete_category,
    delete_city,
    delete_product,
    delete_promo,
    get_admin_stats,
    get_all_cities,
    get_all_orders,
    get_all_promos,
    get_all_users,
    get_categories,
    get_category,
    get_city,
    get_product,
    get_products,
    save_broadcast,
    toggle_city,
    toggle_product,
    toggle_promo,
    unban_user,
    update_category,
    update_city,
    update_product,
    get_all_payment_methods,
    get_payment_method,
    create_payment_method,
    update_payment_method,
    delete_payment_method,
    toggle_payment_method,
    get_order,
    get_order_items,
    get_payment_by_order,
    confirm_payment,
    update_order_pickup_info,
)
from keyboards.kb import (
    adm_cat_actions_kb,
    adm_cats_kb,
    adm_cats_select_city_kb,
    adm_cities_kb,
    adm_city_actions_kb,
    adm_city_confirm_delete_kb,
    adm_prod_confirm_delete_kb,
    adm_product_actions_kb,
    adm_products_kb,
    adm_products_select_cat_kb,
    adm_products_select_city_kb,
    adm_promo_actions_kb,
    adm_promos_kb,
    adm_user_actions_kb,
    admin_back_kb,
    admin_main_kb,
    adm_pay_methods_kb,
    adm_pay_actions_kb,
    adm_pay_edit_kb,
    adm_orders_kb,
    adm_order_detail_kb,
    adm_fulfill_cancel_kb,
    location_request_kb,
    remove_kb,
    skip_photo_kb,
)
from states.states import (
    AdminBroadcastState,
    AdminCategoryState,
    AdminCityState,
    AdminProductState,
    AdminPromoState,
    AdminUserState,
    AdminPaymentMethodState,
    AdminOrderFulfillState,
)

logger = logging.getLogger(__name__)
router = Router()


def is_admin(user_id: int) -> bool:
    return settings.is_admin(user_id)


# ══════════════════════════════════════════════════════════════════════
#  ACCESS FILTER
# ══════════════════════════════════════════════════════════════════════

@router.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("❌ No access.")
        return
    await state.clear()
    await message.answer("👮 <b>Admin panel</b>", reply_markup=admin_main_kb())


@router.callback_query(F.data == "adm_main")
async def cb_adm_main(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        await call.answer("❌ No access.", show_alert=True)
        return
    await state.clear()
    await call.message.edit_text("👮 <b>Admin panel</b>", reply_markup=admin_main_kb())
    await call.answer()


# ══════════════════════════════════════════════════════════════════════
#  STATISTICS
# ══════════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "adm_stats")
async def cb_adm_stats(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return await call.answer("❌")
    stats = await get_admin_stats()
    text = (
        f"📊 <b>Shop statistics</b>\n\n"
        f"👥 Users: <b>{stats['users']}</b>\n"
        f"🏙 Active cities: <b>{stats['cities']}</b>\n"
        f"📦 Products in stock: <b>{stats['products']}</b>\n"
        f"📋 Total orders: <b>{stats['orders_total']}</b>\n"
        f"✅ Paid: <b>{stats['orders_paid']}</b>\n"
        f"📅 Orders today: <b>{stats['today_orders']}</b>\n"
        f"💰 Revenue: <b>{stats['revenue']:.2f} $</b>"
    )
    await call.message.edit_text(text, reply_markup=admin_back_kb())
    await call.answer()


# ══════════════════════════════════════════════════════════════════════
#  CITIES
# ══════════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "adm_cities")
async def cb_adm_cities(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return await call.answer("❌")
    await state.clear()
    cities = await get_all_cities()
    text = f"🏙 <b>Cities</b> (total: {len(cities)})\n\nChoose a city to edit:"
    await call.message.edit_text(text, reply_markup=adm_cities_kb(cities))
    await call.answer()


@router.callback_query(F.data.startswith("adm_city_view:"))
async def cb_adm_city_view(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return await call.answer("❌")
    await state.clear()
    city_id = int(call.data.split(":")[1])
    city = await get_city(city_id)
    if not city:
        await call.answer("City not found.", show_alert=True)
        return

    cats = await get_categories(city_id, active_only=False)
    from database.db import get_products_by_city
    products = await get_products_by_city(city_id, active_only=False)

    status = "✅ Active" if city["is_active"] else "❌ Disabled"
    text = (
        f"🏙 <b>{city['name']}</b>\n\n"
        f"Status: {status}\n"
        f"Description: {city['description'] or '—'}\n"
        f"Sort order: {city['sort_order']}\n"
        f"Categories: {len(cats)}\n"
        f"Products: {len(products)}\n"
        f"Created: {city['created_at'][:10]}"
    )
    await call.message.edit_text(text, reply_markup=adm_city_actions_kb(city_id, city["is_active"]))
    await call.answer()


# ── Add city ──────────────────────────────────────────────────────────

@router.callback_query(F.data == "adm_city_add")
async def cb_adm_city_add(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return await call.answer("❌")
    await state.set_state(AdminCityState.waiting_name)
    await call.message.edit_text("🏙 Enter the <b>name</b> of the new city:")
    await call.answer()


@router.message(AdminCityState.waiting_name)
async def adm_city_name(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    name = message.text.strip()
    if not name or len(name) > 100:
        await message.answer("❌ The name must be between 1 and 100 characters.")
        return
    await state.update_data(city_name=name)
    await state.set_state(AdminCityState.waiting_description)
    await message.answer(f"✅ Name: <b>{name}</b>\n\n📝 Enter a city description (or «—» to skip):")


@router.message(AdminCityState.waiting_description)
async def adm_city_desc(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    desc = "" if message.text.strip() == "—" else message.text.strip()
    await state.update_data(city_desc=desc)
    await state.set_state(AdminCityState.waiting_photo)
    await message.answer("🖼 Send a photo of the city, or tap the button to skip it:", reply_markup=skip_photo_kb())


@router.message(AdminCityState.waiting_photo)
async def adm_city_photo(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    photo_id = ""
    if message.photo:
        photo_id = message.photo[-1].file_id
    elif message.text and message.text.strip() == "—":
        photo_id = ""
    else:
        await message.answer("Send a photo or type «—».")
        return

    await state.update_data(city_photo=photo_id)
    await state.set_state(AdminCityState.waiting_sort_order)
    await message.answer("🔢 Enter the display order (a number, e.g. 0 = first):")


@router.message(AdminCityState.waiting_sort_order)
async def adm_city_sort(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    if not message.text.strip().lstrip("-").isdigit():
        await message.answer("❌ Enter a whole number.")
        return
    sort_order = int(message.text.strip())
    data = await state.get_data()
    # Guard against an "orphaned" FSM state (the bot restarted mid-flow)
    if not data.get("city_name"):
        await state.clear()
        await message.answer(
            "⚠️ The city-creation session has expired. Start again:\n/admin → 🏙 Cities → ➕ Add city.",
            reply_markup=admin_main_kb(),
        )
        return
    city_id = await create_city(
        name=data["city_name"],
        description=data.get("city_desc", ""),
        photo_id=data.get("city_photo", ""),
        sort_order=sort_order,
    )
    await state.clear()
    await message.answer(
        f"✅ City <b>{data['city_name']}</b> created (ID: {city_id})!",
        reply_markup=admin_main_kb(),
    )


# ── Editing city fields ───────────────────────────────────────────────

@router.callback_query(F.data.startswith("adm_city_edit_name:"))
async def cb_city_edit_name(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return await call.answer("❌")
    city_id = int(call.data.split(":")[1])
    await state.set_state(AdminCityState.editing_value)
    await state.update_data(city_id=city_id, edit_field="name")
    await call.message.edit_text("✏️ Enter the new city name:")
    await call.answer()


@router.callback_query(F.data.startswith("adm_city_edit_desc:"))
async def cb_city_edit_desc(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return await call.answer("❌")
    city_id = int(call.data.split(":")[1])
    await state.set_state(AdminCityState.editing_value)
    await state.update_data(city_id=city_id, edit_field="description")
    await call.message.edit_text("📝 Enter the new city description:")
    await call.answer()


@router.callback_query(F.data.startswith("adm_city_edit_photo:"))
async def cb_city_edit_photo(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return await call.answer("❌")
    city_id = int(call.data.split(":")[1])
    await state.set_state(AdminCityState.waiting_photo)
    await state.update_data(city_id=city_id, edit_field="photo_id", mode="edit")
    await call.message.edit_text(
        "🖼 Send a new photo of the city, or tap the button to remove it:", reply_markup=skip_photo_kb()
    )
    await call.answer()


@router.callback_query(F.data.startswith("adm_city_edit_order:"))
async def cb_city_edit_order(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return await call.answer("❌")
    city_id = int(call.data.split(":")[1])
    await state.set_state(AdminCityState.editing_value)
    await state.update_data(city_id=city_id, edit_field="sort_order")
    await call.message.edit_text("🔢 Enter the new display order (a number):")
    await call.answer()


@router.message(AdminCityState.editing_value)
async def adm_city_edit_value(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    data = await state.get_data()
    city_id = data["city_id"]
    field = data["edit_field"]
    value = message.text.strip()

    if field == "sort_order":
        if not value.lstrip("-").isdigit():
            await message.answer("❌ Enter a whole number.")
            return
        value = int(value)

    await update_city(city_id, **{field: value})
    await state.clear()
    city = await get_city(city_id)
    await message.answer(f"✅ City updated!", reply_markup=adm_city_actions_kb(city_id, city["is_active"]))


# Handle a photo while EDITING (mode=edit in state)
@router.message(AdminCityState.waiting_photo, F.photo | F.text)
async def adm_city_photo_edit(message: Message, state: FSMContext):
    """Intercepts a photo while editing an existing city."""
    if not is_admin(message.from_user.id):
        return
    data = await state.get_data()
    if data.get("mode") != "edit":
        # Standard add-flow handler — skip here, it's handled above
        # (aiogram calls the first matching handler, so this shouldn't fire — but just in case)
        return

    city_id = data["city_id"]
    photo_id = ""
    if message.photo:
        photo_id = message.photo[-1].file_id
    elif message.text and message.text.strip() == "—":
        photo_id = ""
    else:
        await message.answer("Send a photo or type «—».")
        return

    await update_city(city_id, photo_id=photo_id)
    await state.clear()
    city = await get_city(city_id)
    await message.answer("✅ City photo updated!", reply_markup=adm_city_actions_kb(city_id, city["is_active"]))


@router.callback_query(AdminCityState.waiting_photo, F.data == "adm_skip_photo")
async def cb_skip_city_photo(call: CallbackQuery, state: FSMContext):
    """Handles the 'Skip photo' button for both adding and editing a city."""
    if not is_admin(call.from_user.id):
        return await call.answer("❌")
    data = await state.get_data()

    if data.get("mode") == "edit":
        city_id = data["city_id"]
        await update_city(city_id, photo_id="")
        await state.clear()
        city = await get_city(city_id)
        await call.message.edit_text(
            "✅ City photo removed!", reply_markup=adm_city_actions_kb(city_id, city["is_active"])
        )
    else:
        if not data.get("city_name"):
            await state.clear()
            await call.message.edit_text(
                "⚠️ The city-creation session has expired. Start again:\n/admin → 🏙 Cities → ➕ Add city.",
                reply_markup=admin_main_kb(),
            )
            return await call.answer()
        await state.update_data(city_photo="")
        await state.set_state(AdminCityState.waiting_sort_order)
        await call.message.edit_text("🔢 Enter the display order (a number, e.g. 0 = first):")
    await call.answer("Photo skipped")


# ── Enable/Disable city ───────────────────────────────────────────────

@router.callback_query(F.data.startswith("adm_city_toggle:"))
async def cb_city_toggle(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return await call.answer("❌")
    city_id = int(call.data.split(":")[1])
    await toggle_city(city_id)
    city = await get_city(city_id)
    status = "✅ enabled" if city["is_active"] else "❌ disabled"
    await call.answer(f"City {status}.")
    await cb_adm_city_view.__wrapped__(call, None) if hasattr(cb_adm_city_view, '__wrapped__') else None

    # Refresh the view
    cats = await get_categories(city_id, active_only=False)
    from database.db import get_products_by_city
    products = await get_products_by_city(city_id, active_only=False)
    status_txt = "✅ Active" if city["is_active"] else "❌ Disabled"
    text = (
        f"🏙 <b>{city['name']}</b>\n\n"
        f"Status: {status_txt}\n"
        f"Description: {city['description'] or '—'}\n"
        f"Sort order: {city['sort_order']}\n"
        f"Categories: {len(cats)}\n"
        f"Products: {len(products)}\n"
        f"Created: {city['created_at'][:10]}"
    )
    await call.message.edit_text(text, reply_markup=adm_city_actions_kb(city_id, city["is_active"]))


# ── Delete city ───────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("adm_city_delete:"))
async def cb_city_delete(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return await call.answer("❌")
    city_id = int(call.data.split(":")[1])
    city = await get_city(city_id)
    await call.message.edit_text(
        f"⚠️ <b>Delete city «{city['name']}»?</b>\n\n"
        "All categories and products in this city will be deleted!\n"
        "This action cannot be undone.",
        reply_markup=adm_city_confirm_delete_kb(city_id),
    )
    await call.answer()


@router.callback_query(F.data.startswith("adm_city_delete_confirm:"))
async def cb_city_delete_confirm(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return await call.answer("❌")
    city_id = int(call.data.split(":")[1])
    city = await get_city(city_id)
    if not city:
        await call.answer("City not found.", show_alert=True)
        return
    name = city["name"]
    await delete_city(city_id)
    await call.answer(f"🗑 City «{name}» deleted.")
    cities = await get_all_cities()
    await call.message.edit_text(
        f"🏙 <b>Cities</b> (total: {len(cities)})",
        reply_markup=adm_cities_kb(cities),
    )


# ══════════════════════════════════════════════════════════════════════
#  CATEGORIES
# ══════════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "adm_cats")
async def cb_adm_cats(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return await call.answer("❌")
    await state.clear()
    cities = await get_all_cities(active_only=False)
    await call.message.edit_text("🗂 <b>Choose a city:</b>", reply_markup=adm_cats_select_city_kb(cities))
    await call.answer()


@router.callback_query(F.data.startswith("adm_cats_city:"))
async def cb_adm_cats_city(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return await call.answer("❌")
    await state.clear()
    city_id = int(call.data.split(":")[1])
    city = await get_city(city_id)
    cats = await get_categories(city_id, active_only=False)
    await call.message.edit_text(
        f"🗂 <b>Categories — {city['name']}</b> (total: {len(cats)})",
        reply_markup=adm_cats_kb(cats, city_id),
    )
    await call.answer()


@router.callback_query(F.data.startswith("adm_cat_view:"))
async def cb_adm_cat_view(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return await call.answer("❌")
    await state.clear()
    cat_id = int(call.data.split(":")[1])
    cat = await get_category(cat_id)
    if not cat:
        await call.answer("Category not found.", show_alert=True)
        return
    products = await get_products(cat_id, active_only=False)
    status = "✅ Active" if cat["is_active"] else "❌ Disabled"
    text = (
        f"{cat['emoji']} <b>{cat['name']}</b>\n\n"
        f"Status: {status}\n"
        f"Sort order: {cat['sort_order']}\n"
        f"Products: {len(products)}"
    )
    await call.message.edit_text(text, reply_markup=adm_cat_actions_kb(cat_id, cat["city_id"], cat["is_active"]))
    await call.answer()


# ── Add category ──────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("adm_cat_add:"))
async def cb_adm_cat_add(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return await call.answer("❌")
    city_id = int(call.data.split(":")[1])
    await state.set_state(AdminCategoryState.waiting_name)
    await state.update_data(city_id=city_id)
    await call.message.edit_text("🗂 Enter the category <b>name</b>:")
    await call.answer()


@router.message(AdminCategoryState.waiting_name)
async def adm_cat_name(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    name = message.text.strip()
    await state.update_data(cat_name=name)
    await state.set_state(AdminCategoryState.waiting_emoji)
    await message.answer(f"✅ Name: <b>{name}</b>\n\n😀 Enter a category emoji:")


@router.message(AdminCategoryState.waiting_emoji)
async def adm_cat_emoji(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    emoji = message.text.strip()
    await state.update_data(cat_emoji=emoji)
    await state.set_state(AdminCategoryState.waiting_sort_order)
    await message.answer(f"✅ Emoji: {emoji}\n\n🔢 Enter the display order (a number):")


@router.message(AdminCategoryState.waiting_sort_order)
async def adm_cat_sort(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    if not message.text.strip().lstrip("-").isdigit():
        await message.answer("❌ Enter a whole number.")
        return
    sort_order = int(message.text.strip())
    data = await state.get_data()
    if not data.get("cat_name") or not data.get("city_id"):
        await state.clear()
        await message.answer(
            "⚠️ The category-creation session has expired. Start again via /admin → 🗂 Categories.",
            reply_markup=admin_main_kb(),
        )
        return
    cat_id = await create_category(
        city_id=data["city_id"],
        name=data["cat_name"],
        emoji=data.get("cat_emoji", "🏷"),
        sort_order=sort_order,
    )
    await state.clear()
    await message.answer(f"✅ Category <b>{data['cat_name']}</b> created!", reply_markup=admin_main_kb())


# ── Editing a category ────────────────────────────────────────────────

@router.callback_query(F.data.startswith("adm_cat_edit_name:"))
async def cb_cat_edit_name(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return await call.answer("❌")
    cat_id = int(call.data.split(":")[1])
    await state.set_state(AdminCategoryState.editing_value)
    await state.update_data(cat_id=cat_id, edit_field="name")
    await call.message.edit_text("✏️ Enter the new category name:")
    await call.answer()


@router.callback_query(F.data.startswith("adm_cat_edit_emoji:"))
async def cb_cat_edit_emoji(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return await call.answer("❌")
    cat_id = int(call.data.split(":")[1])
    await state.set_state(AdminCategoryState.editing_value)
    await state.update_data(cat_id=cat_id, edit_field="emoji")
    await call.message.edit_text("😀 Enter the new emoji:")
    await call.answer()


@router.callback_query(F.data.startswith("adm_cat_edit_order:"))
async def cb_cat_edit_order(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return await call.answer("❌")
    cat_id = int(call.data.split(":")[1])
    await state.set_state(AdminCategoryState.editing_value)
    await state.update_data(cat_id=cat_id, edit_field="sort_order")
    await call.message.edit_text("🔢 Enter the new sort order:")
    await call.answer()


@router.message(AdminCategoryState.editing_value)
async def adm_cat_edit_value(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    data = await state.get_data()
    cat_id = data["cat_id"]
    field = data["edit_field"]
    value = message.text.strip()
    if field == "sort_order":
        if not value.lstrip("-").isdigit():
            await message.answer("❌ Enter a whole number.")
            return
        value = int(value)
    await update_category(cat_id, **{field: value})
    await state.clear()
    cat = await get_category(cat_id)
    await message.answer("✅ Category updated!", reply_markup=adm_cat_actions_kb(cat_id, cat["city_id"], cat["is_active"]))


@router.callback_query(F.data.startswith("adm_cat_toggle:"))
async def cb_cat_toggle(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return await call.answer("❌")
    cat_id = int(call.data.split(":")[1])
    cat = await get_category(cat_id)
    new_state = 0 if cat["is_active"] else 1
    await update_category(cat_id, is_active=new_state)
    cat = await get_category(cat_id)
    status = "enabled" if cat["is_active"] else "disabled"
    await call.answer(f"Category {status}.")
    await call.message.edit_text(
        f"{cat['emoji']} <b>{cat['name']}</b>\n\nStatus: {'✅ Active' if cat['is_active'] else '❌ Disabled'}",
        reply_markup=adm_cat_actions_kb(cat_id, cat["city_id"], cat["is_active"]),
    )


@router.callback_query(F.data.startswith("adm_cat_delete:"))
async def cb_cat_delete(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return await call.answer("❌")
    cat_id = int(call.data.split(":")[1])
    cat = await get_category(cat_id)
    city_id = cat["city_id"]
    await delete_category(cat_id)
    await call.answer("🗑 Category deleted.")
    cats = await get_categories(city_id, active_only=False)
    city = await get_city(city_id)
    await call.message.edit_text(
        f"🗂 <b>Categories — {city['name']}</b>",
        reply_markup=adm_cats_kb(cats, city_id),
    )


# ══════════════════════════════════════════════════════════════════════
#  PRODUCTS
# ══════════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "adm_products")
async def cb_adm_products(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return await call.answer("❌")
    await state.clear()
    cities = await get_all_cities(active_only=False)
    await call.message.edit_text("📦 <b>Choose a city:</b>", reply_markup=adm_products_select_city_kb(cities))
    await call.answer()


@router.callback_query(F.data.startswith("adm_prods_city:"))
async def cb_adm_prods_city(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return await call.answer("❌")
    await state.clear()
    city_id = int(call.data.split(":")[1])
    city = await get_city(city_id)
    cats = await get_categories(city_id, active_only=False)
    if not cats:
        await call.answer("There are no categories in this city. Create a category first.", show_alert=True)
        return
    await call.message.edit_text(
        f"📦 <b>Products — {city['name']}</b>\n\nChoose a category:",
        reply_markup=adm_products_select_cat_kb(cats, city_id),
    )
    await call.answer()


@router.callback_query(F.data.startswith("adm_prods_cat:"))
async def cb_adm_prods_cat(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return await call.answer("❌")
    await state.clear()
    _, cat_id, city_id = call.data.split(":")
    cat_id, city_id = int(cat_id), int(city_id)
    cat = await get_category(cat_id)
    products = await get_products(cat_id, active_only=False)
    await call.message.edit_text(
        f"📦 <b>Products — {cat['emoji']} {cat['name']}</b> ({len(products)} pcs.)",
        reply_markup=adm_products_kb(products, cat_id, city_id),
    )
    await call.answer()


@router.callback_query(F.data.startswith("adm_prod_view:"))
async def cb_adm_prod_view(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return await call.answer("❌")
    await state.clear()
    product_id = int(call.data.split(":")[1])
    product = await get_product(product_id)
    if not product:
        await call.answer("Product not found.", show_alert=True)
        return
    cat = await get_category(product["category_id"])
    status = "✅ Active" if product["is_active"] else "❌ Disabled"
    text = (
        f"📦 <b>{product['name']}</b>\n\n"
        f"Status: {status}\n"
        f"Description: {product['description'] or '—'}\n"
        f"Price: {product['price']} $\n"
        f"Old price: {product['old_price'] or '—'} $\n"
        f"Stock: {product['stock']} pcs.\n"
        f"Category: {cat['emoji']} {cat['name']}\n"
        f"Added: {product['created_at'][:10]}"
    )
    await call.message.edit_text(
        text,
        reply_markup=adm_product_actions_kb(product_id, cat["id"], product["city_id"], product["is_active"]),
    )
    await call.answer()


# ── Add product ───────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("adm_prod_add:"))
async def cb_adm_prod_add(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return await call.answer("❌")
    _, cat_id, city_id = call.data.split(":")
    await state.set_state(AdminProductState.waiting_name)
    await state.update_data(cat_id=int(cat_id), city_id=int(city_id))
    await call.message.edit_text("📦 Enter the product <b>name</b>:")
    await call.answer()


@router.message(AdminProductState.waiting_name)
async def adm_prod_name(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.update_data(prod_name=message.text.strip())
    await state.set_state(AdminProductState.waiting_description)
    await message.answer("📝 Enter a product <b>description</b> (or «—» to skip):")


@router.message(AdminProductState.waiting_description)
async def adm_prod_desc(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    desc = "" if message.text.strip() == "—" else message.text.strip()
    await state.update_data(prod_desc=desc)
    await state.set_state(AdminProductState.waiting_price)
    await message.answer("💰 Enter the <b>price</b> (a number, e.g. 9.99):")


@router.message(AdminProductState.waiting_price)
async def adm_prod_price(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    try:
        price = float(message.text.strip().replace(",", "."))
        if price <= 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Enter a valid price (a positive number).")
        return
    await state.update_data(prod_price=price)
    await state.set_state(AdminProductState.waiting_old_price)
    await message.answer("🏷 Enter the <b>old price</b> to show a discount (or «0» to skip):")


@router.message(AdminProductState.waiting_old_price)
async def adm_prod_old_price(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    try:
        old_price = float(message.text.strip().replace(",", "."))
    except ValueError:
        await message.answer("❌ Enter a number.")
        return
    await state.update_data(prod_old_price=old_price)
    await state.set_state(AdminProductState.waiting_stock)
    await message.answer("📦 Enter the <b>quantity</b> in stock (a whole number):")


@router.message(AdminProductState.waiting_stock)
async def adm_prod_stock(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    if not message.text.strip().isdigit():
        await message.answer("❌ Enter a whole number.")
        return
    await state.update_data(prod_stock=int(message.text.strip()))
    await state.set_state(AdminProductState.waiting_photo)
    await message.answer(
        "🖼 Send a photo of the product, or tap the button to skip it:", reply_markup=skip_photo_kb()
    )


@router.message(AdminProductState.waiting_photo)
async def adm_prod_photo(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    photo_id = ""
    if message.photo:
        photo_id = message.photo[-1].file_id
    elif message.text and message.text.strip() == "—":
        photo_id = ""
    else:
        await message.answer("Send a photo or type «—».")
        return

    data = await state.get_data()
    product_id = await create_product(
        city_id=data["city_id"],
        category_id=data["cat_id"],
        name=data["prod_name"],
        description=data.get("prod_desc", ""),
        price=data["prod_price"],
        stock=data["prod_stock"],
        photo_id=photo_id,
        old_price=data.get("prod_old_price", 0),
    )
    await state.clear()
    await message.answer(
        f"✅ Product <b>{data['prod_name']}</b> added (ID: {product_id})!",
        reply_markup=admin_main_kb(),
    )


# ── Editing a product ─────────────────────────────────────────────────

PROD_EDIT_PROMPTS = {
    "name": "✏️ Enter the new product name:",
    "desc": "📝 Enter the new description:",
    "price": "💰 Enter the new price:",
    "old_price": "🏷 Enter the new old price (0 = remove it):",
    "stock": "📦 Enter the new stock amount:",
    "photo": "🖼 Send a new photo, or tap the button to remove it:",
}

PROD_EDIT_FIELD_MAP = {
    "name": "name",
    "desc": "description",
    "price": "price",
    "old_price": "old_price",
    "stock": "stock",
    "photo": "photo_id",
}


@router.callback_query(F.data.startswith("adm_prod_edit:"))
async def cb_adm_prod_edit(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return await call.answer("❌")
    _, field, product_id = call.data.split(":")
    product_id = int(product_id)

    if field == "photo":
        await state.set_state(AdminProductState.waiting_photo)
        await state.update_data(edit_product_id=product_id, mode="edit")
    else:
        await state.set_state(AdminProductState.editing_value)
        await state.update_data(edit_product_id=product_id, edit_field=field)

    kb = skip_photo_kb() if field == "photo" else None
    await call.message.edit_text(PROD_EDIT_PROMPTS.get(field, "Enter the value:"), reply_markup=kb)
    await call.answer()


@router.message(AdminProductState.editing_value)
async def adm_prod_edit_value(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    data = await state.get_data()
    product_id = data["edit_product_id"]
    field = data["edit_field"]
    db_field = PROD_EDIT_FIELD_MAP.get(field, field)
    value = message.text.strip()

    if field in ("price", "old_price"):
        try:
            value = float(value.replace(",", "."))
        except ValueError:
            await message.answer("❌ Enter a valid number.")
            return
    elif field == "stock":
        if not value.isdigit():
            await message.answer("❌ Enter a whole number.")
            return
        value = int(value)

    await update_product(product_id, **{db_field: value})
    await state.clear()
    product = await get_product(product_id)
    cat = await get_category(product["category_id"])
    await message.answer(
        "✅ Product updated!",
        reply_markup=adm_product_actions_kb(product_id, cat["id"], product["city_id"], product["is_active"]),
    )


# Handling a photo while editing a product
@router.message(AdminProductState.waiting_photo)
async def adm_prod_photo_dispatch(message: Message, state: FSMContext):
    """Dispatcher for photos: adding a new product or editing an existing one."""
    if not is_admin(message.from_user.id):
        return
    data = await state.get_data()

    if data.get("mode") == "edit":
        product_id = data["edit_product_id"]
        photo_id = ""
        if message.photo:
            photo_id = message.photo[-1].file_id
        elif message.text and message.text.strip() == "—":
            photo_id = ""
        else:
            await message.answer("Send a photo or type «—».")
            return
        await update_product(product_id, photo_id=photo_id)
        await state.clear()
        product = await get_product(product_id)
        cat = await get_category(product["category_id"])
        await message.answer(
            "✅ Product photo updated!",
            reply_markup=adm_product_actions_kb(product_id, cat["id"], product["city_id"], product["is_active"]),
        )
    else:
        # Standard add flow — already handled above in adm_prod_photo
        # But aiogram also calls this (later) handler. Duplicating the logic:
        photo_id = ""
        if message.photo:
            photo_id = message.photo[-1].file_id
        elif message.text and message.text.strip() == "—":
            photo_id = ""
        else:
            await message.answer("Send a photo or type «—».")
            return

        if not data.get("prod_name") or not data.get("city_id") or not data.get("cat_id"):
            await state.clear()
            await message.answer(
                "⚠️ The product-creation session has expired. Start again via /admin → 📦 Products.",
                reply_markup=admin_main_kb(),
            )
            return
        product_id = await create_product(
            city_id=data["city_id"],
            category_id=data["cat_id"],
            name=data["prod_name"],
            description=data.get("prod_desc", ""),
            price=data["prod_price"],
            stock=data["prod_stock"],
            photo_id=photo_id,
            old_price=data.get("prod_old_price", 0),
        )
        await state.clear()
        await message.answer(
            f"✅ Product <b>{data['prod_name']}</b> added (ID: {product_id})!",
            reply_markup=admin_main_kb(),
        )


@router.callback_query(AdminProductState.waiting_photo, F.data == "adm_skip_photo")
async def cb_skip_prod_photo(call: CallbackQuery, state: FSMContext):
    """Handles the 'Skip photo' button for both adding and editing a product."""
    if not is_admin(call.from_user.id):
        return await call.answer("❌")
    data = await state.get_data()

    if data.get("mode") == "edit":
        product_id = data["edit_product_id"]
        await update_product(product_id, photo_id="")
        await state.clear()
        product = await get_product(product_id)
        cat = await get_category(product["category_id"])
        await call.message.edit_text(
            "✅ Product photo removed!",
            reply_markup=adm_product_actions_kb(product_id, cat["id"], product["city_id"], product["is_active"]),
        )
    else:
        if not data.get("prod_name") or not data.get("city_id") or not data.get("cat_id"):
            await state.clear()
            await call.message.edit_text(
                "⚠️ The product-creation session has expired. Start again via /admin → 📦 Products.",
                reply_markup=admin_main_kb(),
            )
            return await call.answer()
        product_id = await create_product(
            city_id=data["city_id"],
            category_id=data["cat_id"],
            name=data["prod_name"],
            description=data.get("prod_desc", ""),
            price=data["prod_price"],
            stock=data["prod_stock"],
            photo_id="",
            old_price=data.get("prod_old_price", 0),
        )
        await state.clear()
        await call.message.edit_text(
            f"✅ Product <b>{data['prod_name']}</b> added (ID: {product_id})!",
            reply_markup=admin_main_kb(),
        )
    await call.answer("Photo skipped")


@router.callback_query(F.data.startswith("adm_prod_toggle:"))
async def cb_adm_prod_toggle(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return await call.answer("❌")
    product_id = int(call.data.split(":")[1])
    await toggle_product(product_id)
    product = await get_product(product_id)
    cat = await get_category(product["category_id"])
    status = "enabled" if product["is_active"] else "disabled"
    await call.answer(f"Product {status}.")
    status_txt = "✅ Active" if product["is_active"] else "❌ Disabled"
    text = (
        f"📦 <b>{product['name']}</b>\n\n"
        f"Status: {status_txt}\n"
        f"Price: {product['price']} $\n"
        f"Stock: {product['stock']} pcs."
    )
    await call.message.edit_text(
        text,
        reply_markup=adm_product_actions_kb(product_id, cat["id"], product["city_id"], product["is_active"]),
    )


@router.callback_query(F.data.startswith("adm_prod_delete:"))
async def cb_adm_prod_delete(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return await call.answer("❌")
    parts = call.data.split(":")
    product_id, cat_id, city_id = int(parts[1]), int(parts[2]), int(parts[3])
    product = await get_product(product_id)
    await call.message.edit_text(
        f"⚠️ <b>Delete product «{product['name']}»?</b>\n\nThis action cannot be undone.",
        reply_markup=adm_prod_confirm_delete_kb(product_id, cat_id, city_id),
    )
    await call.answer()


@router.callback_query(F.data.startswith("adm_prod_delete_confirm:"))
async def cb_adm_prod_delete_confirm(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return await call.answer("❌")
    parts = call.data.split(":")
    product_id, cat_id, city_id = int(parts[1]), int(parts[2]), int(parts[3])
    product = await get_product(product_id)
    name = product["name"] if product else f"#{product_id}"
    await delete_product(product_id)
    await call.answer(f"🗑 Product «{name}» deleted.")
    products = await get_products(cat_id, active_only=False)
    cat = await get_category(cat_id)
    await call.message.edit_text(
        f"📦 <b>Products — {cat['emoji']} {cat['name']}</b> ({len(products)} pcs.)",
        reply_markup=adm_products_kb(products, cat_id, city_id),
    )


# ══════════════════════════════════════════════════════════════════════
#  PROMO CODES
# ══════════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "adm_promos")
async def cb_adm_promos(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return await call.answer("❌")
    await state.clear()
    promos = await get_all_promos()
    await call.message.edit_text(f"🏷 <b>Promo codes</b> (total: {len(promos)})", reply_markup=adm_promos_kb(promos))
    await call.answer()


@router.callback_query(F.data.startswith("adm_promo_view:"))
async def cb_adm_promo_view(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return await call.answer("❌")
    promo_id = int(call.data.split(":")[1])
    from database.db import fetchone
    promo = await fetchone("SELECT * FROM promo_codes WHERE id=?", (promo_id,))
    if not promo:
        await call.answer("Promo code not found.", show_alert=True)
        return
    status = "✅ Active" if promo["is_active"] else "❌ Disabled"
    uses = "∞" if promo["uses_left"] == -1 else str(promo["uses_left"])
    discount_str = f"{promo['discount_value']}{'%' if promo['discount_type'] == 'percent' else ' $'}"
    text = (
        f"🏷 <b>{promo['code']}</b>\n\n"
        f"Status: {status}\n"
        f"Type: {'Percent' if promo['discount_type'] == 'percent' else 'Fixed'}\n"
        f"Discount: {discount_str}\n"
        f"Uses left: {uses}"
    )
    await call.message.edit_text(text, reply_markup=adm_promo_actions_kb(promo_id, promo["is_active"]))
    await call.answer()


@router.callback_query(F.data == "adm_promo_add")
async def cb_adm_promo_add(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return await call.answer("❌")
    await state.set_state(AdminPromoState.waiting_code)
    await call.message.edit_text("🏷 Enter the promo <b>code</b> (Latin letters, digits):")
    await call.answer()


@router.message(AdminPromoState.waiting_code)
async def adm_promo_code(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    code = message.text.strip().upper()
    await state.update_data(promo_code=code)
    await state.set_state(AdminPromoState.waiting_type)
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    b = InlineKeyboardBuilder()
    b.button(text="% Percent", callback_data="promo_type:percent")
    b.button(text="$ Fixed", callback_data="promo_type:fixed")
    await message.answer("Choose the discount type:", reply_markup=b.as_markup())


@router.callback_query(F.data.startswith("promo_type:"), AdminPromoState.waiting_type)
async def adm_promo_type(call: CallbackQuery, state: FSMContext):
    promo_type = call.data.split(":")[1]
    await state.update_data(promo_type=promo_type)
    await state.set_state(AdminPromoState.waiting_value)
    hint = "% (e.g. 10 = 10%)" if promo_type == "percent" else "$ (e.g. 5 = 5$)"
    await call.message.edit_text(f"Enter the discount value {hint}:")
    await call.answer()


@router.message(AdminPromoState.waiting_value)
async def adm_promo_value(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    try:
        value = float(message.text.strip().replace(",", "."))
    except ValueError:
        await message.answer("❌ Enter a number.")
        return
    await state.update_data(promo_value=value)
    await state.set_state(AdminPromoState.waiting_uses)
    await message.answer("🔢 How many times can it be used? (enter a number, or «-1» for ∞):")


@router.message(AdminPromoState.waiting_uses)
async def adm_promo_uses(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    try:
        uses = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Enter a whole number.")
        return
    data = await state.get_data()
    await create_promo(data["promo_code"], data["promo_type"], data["promo_value"], uses)
    await state.clear()
    await message.answer(f"✅ Promo code <b>{data['promo_code']}</b> created!", reply_markup=admin_main_kb())


@router.callback_query(F.data.startswith("adm_promo_toggle:"))
async def cb_adm_promo_toggle(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return await call.answer("❌")
    promo_id = int(call.data.split(":")[1])
    await toggle_promo(promo_id)
    await call.answer("Promo code status changed.")
    # refresh the view
    from database.db import fetchone
    promo = await fetchone("SELECT * FROM promo_codes WHERE id=?", (promo_id,))
    status = "✅ Active" if promo["is_active"] else "❌ Disabled"
    uses = "∞" if promo["uses_left"] == -1 else str(promo["uses_left"])
    discount_str = f"{promo['discount_value']}{'%' if promo['discount_type'] == 'percent' else ' $'}"
    text = (
        f"🏷 <b>{promo['code']}</b>\n\n"
        f"Status: {status}\n"
        f"Type: {'Percent' if promo['discount_type'] == 'percent' else 'Fixed'}\n"
        f"Discount: {discount_str}\n"
        f"Uses left: {uses}"
    )
    await call.message.edit_text(text, reply_markup=adm_promo_actions_kb(promo_id, promo["is_active"]))


@router.callback_query(F.data.startswith("adm_promo_delete:"))
async def cb_adm_promo_delete(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return await call.answer("❌")
    promo_id = int(call.data.split(":")[1])
    await delete_promo(promo_id)
    await call.answer("🗑 Promo code deleted.")
    promos = await get_all_promos()
    await call.message.edit_text(f"🏷 <b>Promo codes</b>", reply_markup=adm_promos_kb(promos))


# ══════════════════════════════════════════════════════════════════════
#  BROADCAST
# ══════════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "adm_broadcast")
async def cb_adm_broadcast(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return await call.answer("❌")
    await state.set_state(AdminBroadcastState.waiting_text)
    await call.message.edit_text(
        "📣 <b>Broadcast</b>\n\nEnter the message text.\nHTML formatting is supported."
    )
    await call.answer()


@router.message(AdminBroadcastState.waiting_text)
async def adm_broadcast_send(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    text = message.text or message.caption or ""
    await state.clear()

    users = await get_all_users()
    sent, failed = 0, 0
    for user in users:
        if user["is_banned"]:
            continue
        try:
            await message.bot.send_message(user["tg_id"], text)
            sent += 1
        except Exception:
            failed += 1

    await save_broadcast(text, sent)
    await message.answer(
        f"📣 Broadcast finished!\n✅ Sent: {sent}\n❌ Failed: {failed}",
        reply_markup=admin_main_kb(),
    )


# ══════════════════════════════════════════════════════════════════════
#  USERS
# ══════════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "adm_users")
async def cb_adm_users(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return await call.answer("❌")
    await state.set_state(AdminUserState.waiting_id)
    await call.message.edit_text(
        "👥 <b>User management</b>\n\nEnter the user's Telegram ID:"
    )
    await call.answer()


@router.message(AdminUserState.waiting_id)
async def adm_user_by_id(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    if not message.text.strip().lstrip("-").isdigit():
        await message.answer("❌ Enter a numeric ID.")
        return
    tg_id = int(message.text.strip())
    from database.db import get_user
    user = await get_user(tg_id)
    await state.clear()
    if not user:
        await message.answer("User not found.", reply_markup=admin_main_kb())
        return
    status = "🚫 Banned" if user["is_banned"] else "✅ Active"
    text = (
        f"👤 <b>User</b>\n\n"
        f"ID: <code>{user['tg_id']}</code>\n"
        f"Username: @{user['username'] or '—'}\n"
        f"Name: {user['first_name']} {user['last_name'] or ''}\n"
        f"Status: {status}\n"
        f"Joined: {user['created_at'][:10]}"
    )
    await message.answer(text, reply_markup=adm_user_actions_kb(tg_id, user["is_banned"]))


@router.callback_query(F.data.startswith("adm_user_ban:"))
async def cb_adm_user_ban(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return await call.answer("❌")
    tg_id = int(call.data.split(":")[1])
    from database.db import get_user
    user = await get_user(tg_id)
    if user["is_banned"]:
        await unban_user(tg_id)
        await call.answer("✅ User unbanned.")
    else:
        await ban_user(tg_id)
        await call.answer("🚫 User banned.")
    user = await get_user(tg_id)
    status = "🚫 Banned" if user["is_banned"] else "✅ Active"
    await call.message.edit_text(
        f"👤 <b>User</b> <code>{tg_id}</code>\nStatus: {status}",
        reply_markup=adm_user_actions_kb(tg_id, user["is_banned"]),
    )


# ── Ban/Unban via commands ────────────────────────────────────────────

@router.message(Command("ban"))
async def cmd_ban(message: Message):
    if not is_admin(message.from_user.id):
        return
    parts = message.text.split()
    if len(parts) < 2 or not parts[1].isdigit():
        await message.answer("Usage: /ban &lt;id&gt;")
        return
    await ban_user(int(parts[1]))
    await message.answer(f"🚫 User {parts[1]} banned.")


@router.message(Command("unban"))
async def cmd_unban(message: Message):
    if not is_admin(message.from_user.id):
        return
    parts = message.text.split()
    if len(parts) < 2 or not parts[1].isdigit():
        await message.answer("Usage: /unban &lt;id&gt;")
        return
    await unban_user(int(parts[1]))
    await message.answer(f"✅ User {parts[1]} unbanned.")


# ══════════════════════════════════════════════════════════════════════
#  ORDERS
# ══════════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "adm_orders")
async def cb_adm_orders(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return await call.answer("❌")
    await state.clear()
    orders = await get_all_orders(limit=15)
    if not orders:
        await call.message.edit_text("📋 There are no orders yet.", reply_markup=admin_back_kb())
        await call.answer()
        return

    text = "📋 <b>Last 15 orders:</b>\n\nChoose an order to view:"
    await call.message.edit_text(text, reply_markup=adm_orders_kb(orders))
    await call.answer()


@router.callback_query(F.data.startswith("adm_order_detail:"))
async def cb_adm_order_detail(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return await call.answer("❌")
    await state.clear()
    order_id = int(call.data.split(":")[1])
    result = await _build_order_detail_text(order_id)
    if not result:
        await call.answer("Order not found.", show_alert=True)
        return
    text, status = result
    await call.message.edit_text(text, reply_markup=adm_order_detail_kb(order_id, status))
    await call.answer()


async def _build_order_detail_text(order_id: int):
    """Builds the order card text. Returns (text, status), or None if the order is not found."""
    order = await get_order(order_id)
    if not order:
        return None

    items = await get_order_items(order_id)
    payment = await get_payment_by_order(order_id)

    status_map = {"paid": "✅ Paid", "pending": "⏳ Awaiting payment", "cancelled": "❌ Cancelled"}
    status_text = status_map.get(order["status"], order["status"])

    text = (
        f"📋 <b>Order #{order['id']}</b>\n\n"
        f"Status: {status_text}\n"
        f"Customer: <code>{order['user_id']}</code>\n"
        f"Date: {order['created_at']}\n\n"
        f"<b>Order items:</b>\n"
    )
    for it in items:
        text += f"• {it['name']} ×{it['quantity']} — {it['price']:.2f}$\n"

    text += f"\nAmount: <b>{order['total_price']:.2f}$</b>"
    if order["discount"]:
        text += f"\nDiscount: {order['discount']:.2f}$"
    if order["promo_code"]:
        text += f"\nPromo code: {order['promo_code']}"

    if payment:
        text += f"\n\n💳 Method/details: <code>{payment['wallet']}</code>"
        if payment["status"] == "confirmed":
            text += f"\nConfirmed: {payment['confirmed_at']}"

    if order["pickup_address"]:
        text += f"\n\n📦 <b>Fulfillment details:</b>\nAddress: {order['pickup_address']}"
        if order["pickup_lat"] is not None and order["pickup_lon"] is not None:
            text += (
                f"\n<a href=\"https://maps.google.com/?q="
                f"{order['pickup_lat']},{order['pickup_lon']}\">📍 Open location on map</a>"
            )
        if order["pickup_comment"]:
            text += f"\nComment: {order['pickup_comment']}"

    return text, order["status"]


# ── Confirming payment: step 1 — start collecting fulfillment data ─────

@router.callback_query(F.data.startswith("adm_confirm_pay:"))
async def cb_adm_confirm_payment(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return await call.answer("❌")
    order_id = int(call.data.split(":")[1])

    order = await get_order(order_id)
    if not order:
        await call.answer("Order not found.", show_alert=True)
        return
    if order["status"] != "pending":
        await call.answer("This order has already been processed.", show_alert=True)
        return

    await state.update_data(fulfill_order_id=order_id, fulfill_mode="confirm")
    await state.set_state(AdminOrderFulfillState.waiting_address)
    await call.message.edit_text(
        f"✅ <b>Confirming payment for order #{order_id}</b>\n\n"
        f"Step 1/3. Enter the <b>pickup address</b> for the order (as text):",
        reply_markup=adm_fulfill_cancel_kb(order_id),
    )
    await call.answer()


# ── Editing already-saved fulfillment data (for paid orders) ───────────

@router.callback_query(F.data.startswith("adm_edit_pickup:"))
async def cb_adm_edit_pickup(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return await call.answer("❌")
    order_id = int(call.data.split(":")[1])

    order = await get_order(order_id)
    if not order:
        await call.answer("Order not found.", show_alert=True)
        return
    if order["status"] != "paid":
        await call.answer("Fulfillment details can only be edited for a paid order.", show_alert=True)
        return

    await state.update_data(fulfill_order_id=order_id, fulfill_mode="edit")
    await state.set_state(AdminOrderFulfillState.waiting_address)
    current = f"\n\nCurrent address: <code>{order['pickup_address']}</code>" if order["pickup_address"] else ""
    await call.message.edit_text(
        f"✏️ <b>Editing fulfillment details for order #{order_id}</b>\n\n"
        f"Step 1/3. Enter the new <b>pickup address</b>:{current}",
        reply_markup=adm_fulfill_cancel_kb(order_id),
    )
    await call.answer()


# ── Step 1: address ───────────────────────────────────────────────────

@router.message(AdminOrderFulfillState.waiting_address)
async def adm_order_fulfill_address(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    address = message.text.strip() if message.text else ""
    if not address or len(address) > 500:
        await message.answer("❌ Enter the address as text (up to 500 characters).")
        return

    await state.update_data(fulfill_address=address)
    await state.set_state(AdminOrderFulfillState.waiting_location)
    await message.answer(
        "Step 2/3. Send the <b>location</b> of the pickup point — tap the button below "
        "or attach it manually via 📎 → Location:",
        reply_markup=location_request_kb(),
    )


# ── Step 2: location ──────────────────────────────────────────────────

@router.message(AdminOrderFulfillState.waiting_location, F.location)
async def adm_order_fulfill_location(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.update_data(
        fulfill_lat=message.location.latitude,
        fulfill_lon=message.location.longitude,
    )
    data = await state.get_data()
    await state.set_state(AdminOrderFulfillState.waiting_comment)
    await message.answer("✅ Location received.", reply_markup=remove_kb())
    await message.answer(
        "Step 3/3. Enter a <b>comment or instructions</b> for the customer, "
        "or send «—» to skip:",
        reply_markup=adm_fulfill_cancel_kb(data["fulfill_order_id"]),
    )


@router.message(AdminOrderFulfillState.waiting_location)
async def adm_order_fulfill_location_invalid(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await message.answer(
        "📍 You need to send an actual location — tap the button below "
        "or attach it manually via 📎 → Location.",
        reply_markup=location_request_kb(),
    )


# ── Step 3: comment → save and notify the customer ─────────────────────

@router.message(AdminOrderFulfillState.waiting_comment)
async def adm_order_fulfill_comment(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    raw = (message.text or "").strip()
    if len(raw) > 1000:
        await message.answer("❌ The comment is too long (maximum 1000 characters).")
        return
    comment = "" if raw == "—" else raw

    data = await state.get_data()
    order_id = data.get("fulfill_order_id")
    address = data.get("fulfill_address")
    lat = data.get("fulfill_lat")
    lon = data.get("fulfill_lon")
    mode = data.get("fulfill_mode", "confirm")

    if not order_id or not address or lat is None or lon is None:
        await state.clear()
        await message.answer(
            "⚠️ The data-entry session has expired. Start again via 📋 Orders.",
            reply_markup=admin_main_kb(),
        )
        return

    order = await get_order(order_id)
    if not order:
        await state.clear()
        await message.answer("Order not found.", reply_markup=admin_main_kb())
        return

    await update_order_pickup_info(order_id, address, lat, lon, comment)
    if mode == "confirm":
        await confirm_payment(order_id, "manual_admin_confirm")
    await state.clear()

    # ── notify the customer ──
    try:
        if mode == "confirm":
            user_text = (
                f"✅ <b>Payment confirmed!</b>\n\n"
                f"Order #{order_id} has been paid.\n\n"
                f"📍 <b>Pickup address:</b>\n{address}\n"
            )
        else:
            user_text = (
                f"ℹ️ <b>Pickup details for order #{order_id} have been updated</b>\n\n"
                f"📍 <b>New pickup address:</b>\n{address}\n"
            )
        if comment:
            user_text += f"\n💬 <b>Comment:</b>\n{comment}\n"
        if mode == "confirm":
            user_text += f"\nThank you for shopping at {settings.shop_name}! 🌸"

        await message.bot.send_message(order["user_id"], user_text)
        await message.bot.send_location(order["user_id"], latitude=lat, longitude=lon)
    except Exception as e:
        logger.error("Notify error: %s", e)

    result = await _build_order_detail_text(order_id)
    if result:
        text, status = result
        await message.answer(text, reply_markup=adm_order_detail_kb(order_id, status))
    else:
        await message.answer("✅ Done.", reply_markup=admin_main_kb())


# ══════════════════════════════════════════════════════════════════════
#  PAYMENT METHODS
# ══════════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "adm_pay_methods")
async def cb_adm_pay_methods(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return await call.answer("❌")
    await state.clear()
    methods = await get_all_payment_methods()
    text = f"💳 <b>Payment methods</b> (total: {len(methods)})\n\nChoose a method to edit, or add a new one:"
    await call.message.edit_text(text, reply_markup=adm_pay_methods_kb(methods))
    await call.answer()


@router.callback_query(F.data.startswith("adm_pay_view:"))
async def cb_adm_pay_view(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return await call.answer("❌")
    await state.clear()
    method_id = int(call.data.split(":")[1])
    method = await get_payment_method(method_id)
    if not method:
        await call.answer("Payment method not found.", show_alert=True)
        return
    status = "✅ Active" if method["is_active"] else "❌ Disabled"
    text = (
        f"💳 <b>{method['name']}</b>\n\n"
        f"Status: {status}\n"
        f"Description: {method['description'] or '—'}\n"
        f"Details:\n<code>{method['details'] or '—'}</code>\n"
        f"Sort order: {method['sort_order']}"
    )
    await call.message.edit_text(text, reply_markup=adm_pay_actions_kb(method_id, method["is_active"]))
    await call.answer()


@router.callback_query(F.data == "adm_pay_add")
async def cb_adm_pay_add(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return await call.answer("❌")
    await state.set_state(AdminPaymentMethodState.waiting_name)
    await call.message.edit_text("💳 Enter the <b>name</b> of the payment method (e.g. USDT TRC20, Card, Cash):")
    await call.answer()


@router.message(AdminPaymentMethodState.waiting_name)
async def adm_pay_name(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    name = message.text.strip()
    if not name or len(name) > 100:
        await message.answer("❌ The name must be between 1 and 100 characters.")
        return
    await state.update_data(pay_name=name)
    await state.set_state(AdminPaymentMethodState.waiting_description)
    await message.answer(f"✅ Name: <b>{name}</b>\n\n📝 Enter a short description (or «—» to skip):")


@router.message(AdminPaymentMethodState.waiting_description)
async def adm_pay_description(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    desc = "" if message.text.strip() == "—" else message.text.strip()
    await state.update_data(pay_desc=desc)
    await state.set_state(AdminPaymentMethodState.waiting_details)
    await message.answer("💬 Enter the payment details (wallet address, card number, etc.) or «—» to skip:")


@router.message(AdminPaymentMethodState.waiting_details)
async def adm_pay_details(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    details = "" if message.text.strip() == "—" else message.text.strip()
    await state.update_data(pay_details=details)
    await state.set_state(AdminPaymentMethodState.waiting_sort_order)
    await message.answer("🔢 Enter the sort order (a number, e.g. 0):")


@router.message(AdminPaymentMethodState.waiting_sort_order)
async def adm_pay_sort_order(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    try:
        sort_order = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Enter a whole number.")
        return
    data = await state.get_data()
    await create_payment_method(
        name=data["pay_name"],
        description=data.get("pay_desc", ""),
        details=data.get("pay_details", ""),
        sort_order=sort_order,
    )
    await state.clear()
    await message.answer(
        f"✅ Payment method <b>{data['pay_name']}</b> added!",
        reply_markup=admin_main_kb()
    )


@router.callback_query(F.data.startswith("adm_pay_toggle:"))
async def cb_adm_pay_toggle(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return await call.answer("❌")
    method_id = int(call.data.split(":")[1])
    await toggle_payment_method(method_id)
    await call.answer("Payment method status changed.")
    method = await get_payment_method(method_id)
    status = "✅ Active" if method["is_active"] else "❌ Disabled"
    text = (
        f"💳 <b>{method['name']}</b>\n\n"
        f"Status: {status}\n"
        f"Description: {method['description'] or '—'}\n"
        f"Details:\n<code>{method['details'] or '—'}</code>\n"
        f"Sort order: {method['sort_order']}"
    )
    await call.message.edit_text(text, reply_markup=adm_pay_actions_kb(method_id, method["is_active"]))


@router.callback_query(F.data.startswith("adm_pay_edit:"))
async def cb_adm_pay_edit(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return await call.answer("❌")
    method_id = int(call.data.split(":")[1])
    method = await get_payment_method(method_id)
    if not method:
        await call.answer("Not found.", show_alert=True)
        return
    await state.update_data(editing_pay_id=method_id)
    await call.message.edit_text(
        f"✏️ <b>Editing: {method['name']}</b>\n\nChoose a field to change:",
        reply_markup=adm_pay_edit_kb(method_id)
    )
    await call.answer()


@router.callback_query(F.data.startswith("adm_pay_edit_field:"))
async def cb_adm_pay_edit_field(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return await call.answer("❌")
    parts = call.data.split(":")
    method_id, field = int(parts[1]), parts[2]
    field_names = {
        "name": "Name",
        "description": "Description",
        "details": "Payment details",
        "sort_order": "Sort order",
    }
    await state.update_data(editing_pay_id=method_id, editing_pay_field=field)
    await state.set_state(AdminPaymentMethodState.editing_value)
    await call.message.edit_text(f"✏️ Enter the new value for <b>{field_names.get(field, field)}</b>:")
    await call.answer()


@router.message(AdminPaymentMethodState.editing_value)
async def adm_pay_save_edit(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    data = await state.get_data()
    method_id = data.get("editing_pay_id")
    field = data.get("editing_pay_field")
    value = message.text.strip()
    if field == "sort_order":
        try:
            value = int(value)
        except ValueError:
            await message.answer("❌ Enter a whole number.")
            return
    await update_payment_method(method_id, **{field: value})
    await state.clear()
    method = await get_payment_method(method_id)
    await message.answer(
        f"✅ Field updated!\n\n💳 <b>{method['name']}</b>",
        reply_markup=adm_pay_actions_kb(method_id, method["is_active"])
    )


@router.callback_query(F.data.startswith("adm_pay_delete:"))
async def cb_adm_pay_delete(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return await call.answer("❌")
    method_id = int(call.data.split(":")[1])
    method = await get_payment_method(method_id)
    name = method["name"] if method else f"#{method_id}"
    await delete_payment_method(method_id)
    await call.answer(f"🗑 Payment method «{name}» deleted.")
    methods = await get_all_payment_methods()
    await call.message.edit_text(
        f"💳 <b>Payment methods</b> (total: {len(methods)})",
        reply_markup=adm_pay_methods_kb(methods)
    )
