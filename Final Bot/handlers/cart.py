"""
handlers/cart.py — cart, promo codes, payment.
"""
import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from config.settings import settings
from utils.helpers import safe_edit_text
from database.db import (
    add_order_items,
    add_to_cart,
    clear_cart,
    create_order,
    create_payment,
    get_cart,
    get_cart_total,
    get_payment_by_order,
    get_pending_payments,
    get_product,
    get_promo,
    get_user,
    update_cart_quantity,
    use_promo,
    get_all_payment_methods,
    get_payment_method,
)
from keyboards.kb import cart_kb, payment_kb, promo_kb, payment_methods_kb
from states.states import CartState

logger = logging.getLogger(__name__)
router = Router()


# ── Add to cart ───────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("add_cart:"))
async def cb_add_to_cart(call: CallbackQuery):
    product_id = int(call.data.split(":")[1])
    product = await get_product(product_id)
    if not product:
        await call.answer("Product not found.", show_alert=True)
        return
    if not product["is_active"] or product["stock"] <= 0:
        await call.answer("❌ Product unavailable or out of stock.", show_alert=True)
        return

    await add_to_cart(call.from_user.id, product_id)
    await call.answer(f"✅ \u00ab{product['name']}\u00bb added to cart!")


# ── View cart ─────────────────────────────────────────────────────────

@router.message(F.text == "🛒 Cart")
async def btn_cart(message: Message):
    await _show_cart(message.from_user.id, message)


async def _show_cart(user_id: int, target: Message | CallbackQuery):
    items = await get_cart(user_id)
    is_call = isinstance(target, CallbackQuery)

    if not items:
        text = "🛒 Your cart is empty.\n\nAdd products from the catalog!"
        if is_call:
            await safe_edit_text(target.message, text)
            await target.answer()
        else:
            await target.answer(text)
        return

    total = sum(i["price"] * i["quantity"] for i in items)
    text = "🛒 <b>Your cart:</b>\n\n"
    for item in items:
        text += f"• {item['name']} × {item['quantity']} = {item['price'] * item['quantity']:.2f}$\n"
    text += f"\n💰 <b>Total: {total:.2f}$</b>"

    kb = cart_kb(items, total)
    if is_call:
        await safe_edit_text(target.message, text, reply_markup=kb)
        await target.answer()
    else:
        await target.answer(text, reply_markup=kb)


# ── Remove an item from the cart ──────────────────────────────────────

@router.callback_query(F.data.startswith("cart_del:"))
async def cb_cart_delete(call: CallbackQuery):
    product_id = int(call.data.split(":")[1])
    await update_cart_quantity(call.from_user.id, product_id, 0)
    await call.answer("Removed from cart.")
    await _show_cart(call.from_user.id, call)


# ── Clear cart ────────────────────────────────────────────────────────

@router.callback_query(F.data == "cart_clear")
async def cb_cart_clear(call: CallbackQuery):
    await clear_cart(call.from_user.id)
    await call.answer("🗑 Cart cleared.")
    await safe_edit_text(call.message, "🛒 Cart is empty.")


# ── Promo code ────────────────────────────────────────────────────────

@router.callback_query(F.data == "checkout")
async def cb_checkout(call: CallbackQuery):
    items = await get_cart(call.from_user.id)
    if not items:
        await call.answer("Cart is empty.", show_alert=True)
        return
    await safe_edit_text(call.message, 
        "🏷 Have a promo code?\n\nChoose an action:",
        reply_markup=promo_kb(),
    )
    await call.answer()


@router.callback_query(F.data == "enter_promo")
async def cb_enter_promo(call: CallbackQuery, state: FSMContext):
    await state.set_state(CartState.entering_promo)
    await safe_edit_text(call.message, "✏️ Enter your promo code:")
    await call.answer()


@router.message(CartState.entering_promo)
async def process_promo(message: Message, state: FSMContext):
    code = message.text.strip().upper()
    promo = await get_promo(code)

    if not promo:
        await message.answer("❌ This promo code is invalid or has been used up. Try another one or continue without a discount.", reply_markup=promo_kb())
        await state.clear()
        return

    await state.update_data(promo_code=code, promo_type=promo["discount_type"], promo_value=promo["discount_value"])
    await message.answer(
        f"✅ Promo code <b>{code}</b> applied!\n"
        f"Discount: {promo['discount_value']}{'%' if promo['discount_type'] == 'percent' else ' $'}"
    )
    await state.clear()
    await _process_payment(message, user_id=message.from_user.id, promo_code=code, promo_type=promo["discount_type"], promo_value=promo["discount_value"])


@router.callback_query(F.data == "checkout_no_promo")
async def cb_checkout_no_promo(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.answer()
    await _process_payment(call.message, user_id=call.from_user.id)


async def _process_payment(target: Message, user_id: int = None, promo_code: str = "", promo_type: str = "", promo_value: float = 0):
    # user_id is passed explicitly because call.message.from_user = None (the message is from the bot)
    if user_id is None:
        user_id = target.from_user.id if target.from_user else None
    if user_id is None:
        await target.answer("Error: could not determine the user.")
        return

    user = await get_user(user_id)
    if not user or not user["city_id"]:
        await target.answer("Error: no city selected. Use /start")
        return

    items = await get_cart(user_id)
    if not items:
        await target.answer("Cart is empty.")
        return

    total = sum(i["price"] * i["quantity"] for i in items)
    discount = 0.0

    if promo_code and promo_value:
        if promo_type == "percent":
            discount = round(total * promo_value / 100, 2)
        else:
            discount = min(promo_value, total)
        await use_promo(promo_code)

    final_total = max(total - discount, 0.01)

    # Create the order
    order_id = await create_order(
        user_id=user_id,
        city_id=user["city_id"],
        total=final_total,
        discount=discount,
        promo_code=promo_code,
    )

    order_items = [
        {"product_id": i["product_id"], "name": i["name"], "price": i["price"], "quantity": i["quantity"]}
        for i in items
    ]
    await add_order_items(order_id, order_items)
    await clear_cart(user_id)

    # Load active payment methods from the DB
    pay_methods = await get_all_payment_methods(active_only=True)

    if not pay_methods:
        # Fallback: if no payment methods are configured — default to USDT
        await create_payment(
            order_id=order_id,
            user_id=user_id,
            amount=final_total,
            wallet=settings.usdt_wallet,
            timeout_minutes=settings.payment_timeout_minutes,
        )
        text = (
            f"💳 <b>Payment for order #{order_id}</b>\n\n"
            f"Amount: <b>{final_total:.2f} USDT</b>\n"
            + (f"Discount: {discount:.2f} USDT\n" if discount else "")
            + f"\n📤 Send exactly <b>{final_total:.2f} USDT (TRC20)</b> to:\n\n"
            f"<code>{settings.usdt_wallet}</code>\n\n"
            f"⏱ This payment is valid for {settings.payment_timeout_minutes} minutes.\n"
            f"The bot will confirm your payment automatically.\n\n"
            f"📦 Once payment is confirmed, we will send you the address, pickup "
            f"location, and all the details for receiving your order."
        )
        await target.answer(text, reply_markup=payment_kb(order_id))
    else:
        # Show the list of available payment methods
        text = (
            f"💳 <b>Payment for order #{order_id}</b>\n\n"
            f"Amount: <b>{final_total:.2f} $</b>\n"
            + (f"Discount: {discount:.2f} $\n" if discount else "")
            + "\n💳 Choose a payment method:"
        )
        await target.answer(text, reply_markup=payment_methods_kb(pay_methods, order_id))



# ── Manual payment check ──────────────────────────────────────────────

@router.callback_query(F.data.startswith("paid_check:"))
async def cb_paid_check(call: CallbackQuery):
    order_id = int(call.data.split(":")[1])
    payment = await get_payment_by_order(order_id)
    if not payment:
        await call.answer("Payment not found.", show_alert=True)
        return

    if payment["status"] == "confirmed":
        await call.answer("✅ Payment is already confirmed!", show_alert=True)
        return
    if payment["status"] == "expired":
        await call.answer("❌ The payment window has expired. Please create a new order.", show_alert=True)
        return

    await call.answer("⏳ Waiting for the transaction to confirm. This takes 1-2 minutes.", show_alert=True)


# ── Cancel order ──────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("cancel_order:"))
async def cb_cancel_order(call: CallbackQuery):
    order_id = int(call.data.split(":")[1])
    from database.db import get_order, update_order_status
    order = await get_order(order_id)
    if not order or order["user_id"] != call.from_user.id:
        await call.answer("Order not found.", show_alert=True)
        return
    if order["status"] not in ("pending",):
        await call.answer("This order has already been processed.", show_alert=True)
        return

    await update_order_status(order_id, "cancelled")
    await safe_edit_text(call.message, f"❌ Order #{order_id} cancelled.")
    await call.answer("Order cancelled.")


# ── Choose payment method ─────────────────────────────────────────────

@router.callback_query(F.data.startswith("select_pay_method:"))
async def cb_select_pay_method(call: CallbackQuery):
    parts = call.data.split(":")
    order_id, method_id = int(parts[1]), int(parts[2])

    from database.db import get_order
    order = await get_order(order_id)
    if not order:
        await call.answer("Order not found.", show_alert=True)
        return

    method = await get_payment_method(method_id)
    if not method or not method["is_active"]:
        await call.answer("This payment method is unavailable.", show_alert=True)
        return

    # Create the payment record (wallet = method name for non-crypto methods)
    wallet_ref = method["details"] if method["details"] else method["name"]
    await create_payment(
        order_id=order_id,
        user_id=call.from_user.id,
        amount=order["total_price"],
        wallet=wallet_ref,
        timeout_minutes=settings.payment_timeout_minutes,
    )

    text = (
        f"💳 <b>Payment for order #{order_id}</b>\n\n"
        f"Payment method: <b>{method['name']}</b>\n"
        f"Amount: <b>{order['total_price']:.2f} $</b>\n"
    )
    if method["description"]:
        text += f"\n📋 {method['description']}\n"
    if method["details"]:
        text += f"\n📤 Payment details:\n<code>{method['details']}</code>\n"
    text += f"\n⏱ This payment is valid for {settings.payment_timeout_minutes} minutes."
    text += (
        f"\n\n📦 Once payment is confirmed, we will send you the address, pickup "
        f"location, and all the details for receiving your order."
    )

    await safe_edit_text(call.message, text, reply_markup=payment_kb(order_id))
    await call.answer()
