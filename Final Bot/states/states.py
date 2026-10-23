"""
states/states.py — all FSM states.
"""
from aiogram.fsm.state import State, StatesGroup


class CatalogState(StatesGroup):
    choosing_city = State()


class CartState(StatesGroup):
    entering_promo = State()


class AdminCityState(StatesGroup):
    waiting_name = State()
    waiting_description = State()
    waiting_photo = State()
    waiting_sort_order = State()
    editing_field = State()
    editing_value = State()


class AdminCategoryState(StatesGroup):
    waiting_name = State()
    waiting_emoji = State()
    waiting_sort_order = State()
    editing_field = State()
    editing_value = State()


class AdminProductState(StatesGroup):
    waiting_name = State()
    waiting_description = State()
    waiting_price = State()
    waiting_old_price = State()
    waiting_stock = State()
    waiting_photo = State()
    editing_field = State()
    editing_value = State()
    # context used while adding a new product
    choosing_city = State()
    choosing_category = State()


class AdminPromoState(StatesGroup):
    waiting_code = State()
    waiting_type = State()
    waiting_value = State()
    waiting_uses = State()


class AdminBroadcastState(StatesGroup):
    waiting_text = State()


class AdminUserState(StatesGroup):
    waiting_id = State()


class AdminPaymentMethodState(StatesGroup):
    waiting_name = State()
    waiting_description = State()
    waiting_details = State()
    waiting_sort_order = State()
    editing_field = State()
    editing_value = State()


class AdminOrderFulfillState(StatesGroup):
    """Admin fills in order fulfillment details (on payment confirmation or when editing)."""
    waiting_address = State()
    waiting_location = State()
    waiting_comment = State()
