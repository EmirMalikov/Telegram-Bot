"""
database/db.py — all SQLite operations via aiosqlite.
Principle: every function opens its own connection — no global objects.
"""

import asyncio
import logging
import os
import sqlite3
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import aiosqlite

from config.settings import settings

logger = logging.getLogger(__name__)

DB_PATH = settings.database_path


# ─────────────────────────── helpers ──────────────────────────────────────────

@asynccontextmanager
async def get_db():
    """Async context manager — always a fresh connection, automatic commit/rollback."""
    os.makedirs(os.path.dirname(DB_PATH) if os.path.dirname(DB_PATH) else ".", exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        await db.execute("PRAGMA foreign_keys = ON")
        await db.execute("PRAGMA journal_mode = WAL")
        try:
            yield db
            await db.commit()
        except Exception:
            await db.rollback()
            raise


async def fetchone(sql: str, params: tuple = ()) -> Optional[aiosqlite.Row]:
    async with get_db() as db:
        async with db.execute(sql, params) as cur:
            return await cur.fetchone()


async def fetchall(sql: str, params: tuple = ()) -> List[aiosqlite.Row]:
    async with get_db() as db:
        async with db.execute(sql, params) as cur:
            return await cur.fetchall()


async def execute(sql: str, params: tuple = ()) -> int:
    """Returns lastrowid."""
    async with get_db() as db:
        cur = await db.execute(sql, params)
        return cur.lastrowid


# ─────────────────────────── init ─────────────────────────────────────────────

async def init_db():
    """Creates all tables on first run."""
    async with get_db() as db:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id          INTEGER PRIMARY KEY,
                tg_id       INTEGER UNIQUE NOT NULL,
                username    TEXT,
                first_name  TEXT,
                last_name   TEXT,
                is_banned   INTEGER DEFAULT 0,
                is_admin    INTEGER DEFAULT 0,
                referrer_id INTEGER,
                city_id     INTEGER,
                created_at  TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (city_id) REFERENCES cities(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS cities (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT NOT NULL,
                description TEXT DEFAULT '',
                photo_id    TEXT DEFAULT '',
                is_active   INTEGER DEFAULT 1,
                sort_order  INTEGER DEFAULT 0,
                created_at  TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS categories (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                city_id     INTEGER NOT NULL,
                name        TEXT NOT NULL,
                emoji       TEXT DEFAULT '🏷',
                is_active   INTEGER DEFAULT 1,
                sort_order  INTEGER DEFAULT 0,
                FOREIGN KEY (city_id) REFERENCES cities(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS products (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                city_id      INTEGER NOT NULL,
                category_id  INTEGER NOT NULL,
                name         TEXT NOT NULL,
                description  TEXT DEFAULT '',
                price        REAL NOT NULL,
                old_price    REAL DEFAULT 0,
                stock        INTEGER DEFAULT 0,
                photo_id     TEXT DEFAULT '',
                is_active    INTEGER DEFAULT 1,
                sort_order   INTEGER DEFAULT 0,
                created_at   TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (city_id)     REFERENCES cities(id)     ON DELETE CASCADE,
                FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS cart (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL,
                product_id  INTEGER NOT NULL,
                quantity    INTEGER DEFAULT 1,
                UNIQUE(user_id, product_id),
                FOREIGN KEY (user_id)    REFERENCES users(tg_id)    ON DELETE CASCADE,
                FOREIGN KEY (product_id) REFERENCES products(id)    ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS orders (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL,
                city_id     INTEGER,
                total_price REAL NOT NULL,
                discount    REAL DEFAULT 0,
                status      TEXT DEFAULT 'pending',
                promo_code  TEXT DEFAULT '',
                pickup_address  TEXT DEFAULT '',
                pickup_lat      REAL,
                pickup_lon      REAL,
                pickup_comment  TEXT DEFAULT '',
                created_at  TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (user_id)  REFERENCES users(tg_id)  ON DELETE CASCADE,
                FOREIGN KEY (city_id)  REFERENCES cities(id)    ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS order_items (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id    INTEGER NOT NULL,
                product_id  INTEGER,
                name        TEXT NOT NULL,
                price       REAL NOT NULL,
                quantity    INTEGER NOT NULL,
                FOREIGN KEY (order_id)   REFERENCES orders(id)   ON DELETE CASCADE,
                FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS payments (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id        INTEGER NOT NULL UNIQUE,
                user_id         INTEGER NOT NULL,
                amount          REAL NOT NULL,
                wallet          TEXT NOT NULL,
                status          TEXT DEFAULT 'waiting',
                tx_hash         TEXT DEFAULT '',
                expires_at      TEXT NOT NULL,
                confirmed_at    TEXT DEFAULT '',
                FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS promo_codes (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                code            TEXT UNIQUE NOT NULL,
                discount_type   TEXT NOT NULL,
                discount_value  REAL NOT NULL,
                uses_left       INTEGER DEFAULT -1,
                is_active       INTEGER DEFAULT 1,
                created_at      TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS favorites (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL,
                product_id  INTEGER NOT NULL,
                UNIQUE(user_id, product_id),
                FOREIGN KEY (user_id)    REFERENCES users(tg_id)    ON DELETE CASCADE,
                FOREIGN KEY (product_id) REFERENCES products(id)    ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS reviews (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL,
                product_id  INTEGER NOT NULL,
                rating      INTEGER NOT NULL,
                text        TEXT DEFAULT '',
                created_at  TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (user_id)    REFERENCES users(tg_id)    ON DELETE CASCADE,
                FOREIGN KEY (product_id) REFERENCES products(id)    ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS broadcasts (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                text        TEXT NOT NULL,
                sent_count  INTEGER DEFAULT 0,
                created_at  TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS payment_methods (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT NOT NULL,
                description TEXT DEFAULT '',
                details     TEXT DEFAULT '',
                is_active   INTEGER DEFAULT 1,
                sort_order  INTEGER DEFAULT 0,
                created_at  TEXT DEFAULT (datetime('now'))
            );

            CREATE INDEX IF NOT EXISTS idx_products_city     ON products(city_id);
            CREATE INDEX IF NOT EXISTS idx_products_category ON products(category_id);
            CREATE INDEX IF NOT EXISTS idx_cart_user         ON cart(user_id);
            CREATE INDEX IF NOT EXISTS idx_orders_user       ON orders(user_id);
            CREATE INDEX IF NOT EXISTS idx_payments_order    ON payments(order_id);
            CREATE INDEX IF NOT EXISTS idx_categories_city   ON categories(city_id);
        """)

        # Migration: add order-fulfillment columns to orders if the DB already
        # existed without them (created before this feature was added).
        cur = await db.execute("PRAGMA table_info(orders)")
        existing_cols = {row[1] for row in await cur.fetchall()}
        pickup_migrations = {
            "pickup_address": "ALTER TABLE orders ADD COLUMN pickup_address TEXT DEFAULT ''",
            "pickup_lat": "ALTER TABLE orders ADD COLUMN pickup_lat REAL",
            "pickup_lon": "ALTER TABLE orders ADD COLUMN pickup_lon REAL",
            "pickup_comment": "ALTER TABLE orders ADD COLUMN pickup_comment TEXT DEFAULT ''",
        }
        for col, ddl in pickup_migrations.items():
            if col not in existing_cols:
                await db.execute(ddl)
                logger.info("🔧 DB migration: added column orders.%s", col)
    logger.info("✅ Database initialized: %s", DB_PATH)


# ─────────────────────── USERS ────────────────────────────────────────────────

async def get_or_create_user(tg_id: int, username: str = "", first_name: str = "", last_name: str = "", referrer_id: Optional[int] = None) -> aiosqlite.Row:
    row = await fetchone("SELECT * FROM users WHERE tg_id = ?", (tg_id,))
    if row:
        await execute(
            "UPDATE users SET username=?, first_name=?, last_name=? WHERE tg_id=?",
            (username, first_name, last_name, tg_id),
        )
        return await fetchone("SELECT * FROM users WHERE tg_id = ?", (tg_id,))
    await execute(
        "INSERT OR IGNORE INTO users (tg_id, username, first_name, last_name, referrer_id) VALUES (?,?,?,?,?)",
        (tg_id, username, first_name, last_name, referrer_id),
    )
    return await fetchone("SELECT * FROM users WHERE tg_id = ?", (tg_id,))


async def get_user(tg_id: int) -> Optional[aiosqlite.Row]:
    return await fetchone("SELECT * FROM users WHERE tg_id = ?", (tg_id,))


async def set_user_city(tg_id: int, city_id: int):
    await execute("UPDATE users SET city_id = ? WHERE tg_id = ?", (city_id, tg_id))


async def ban_user(tg_id: int):
    await execute("UPDATE users SET is_banned = 1 WHERE tg_id = ?", (tg_id,))


async def unban_user(tg_id: int):
    await execute("UPDATE users SET is_banned = 0 WHERE tg_id = ?", (tg_id,))


async def get_all_users() -> List[aiosqlite.Row]:
    return await fetchall("SELECT * FROM users ORDER BY created_at DESC")


async def get_users_count() -> int:
    row = await fetchone("SELECT COUNT(*) as cnt FROM users")
    return row["cnt"] if row else 0


async def get_referrals_count(tg_id: int) -> int:
    row = await fetchone("SELECT COUNT(*) as cnt FROM users WHERE referrer_id = ?", (tg_id,))
    return row["cnt"] if row else 0


# ─────────────────────── CITIES ───────────────────────────────────────────────

async def get_all_cities(active_only: bool = False) -> List[aiosqlite.Row]:
    if active_only:
        return await fetchall("SELECT * FROM cities WHERE is_active=1 ORDER BY sort_order, name")
    return await fetchall("SELECT * FROM cities ORDER BY sort_order, name")


async def get_city(city_id: int) -> Optional[aiosqlite.Row]:
    return await fetchone("SELECT * FROM cities WHERE id = ?", (city_id,))


async def create_city(name: str, description: str = "", photo_id: str = "", sort_order: int = 0) -> int:
    return await execute(
        "INSERT INTO cities (name, description, photo_id, sort_order) VALUES (?,?,?,?)",
        (name, description, photo_id, sort_order),
    )


async def update_city(city_id: int, **kwargs):
    allowed = {"name", "description", "photo_id", "is_active", "sort_order"}
    fields = {k: v for k, v in kwargs.items() if k in allowed}
    if not fields:
        return
    set_clause = ", ".join(f"{k}=?" for k in fields)
    await execute(
        f"UPDATE cities SET {set_clause} WHERE id=?",
        (*fields.values(), city_id),
    )


async def delete_city(city_id: int):
    """Deletes a city. Cascades to delete its categories and products (FK ON DELETE CASCADE)."""
    await execute("DELETE FROM cities WHERE id = ?", (city_id,))


async def toggle_city(city_id: int):
    await execute(
        "UPDATE cities SET is_active = CASE WHEN is_active=1 THEN 0 ELSE 1 END WHERE id=?",
        (city_id,),
    )


# ─────────────────────── CATEGORIES ───────────────────────────────────────────

async def get_categories(city_id: int, active_only: bool = True) -> List[aiosqlite.Row]:
    if active_only:
        return await fetchall(
            "SELECT * FROM categories WHERE city_id=? AND is_active=1 ORDER BY sort_order, name",
            (city_id,),
        )
    return await fetchall(
        "SELECT * FROM categories WHERE city_id=? ORDER BY sort_order, name",
        (city_id,),
    )


async def get_category(cat_id: int) -> Optional[aiosqlite.Row]:
    return await fetchone("SELECT * FROM categories WHERE id = ?", (cat_id,))


async def create_category(city_id: int, name: str, emoji: str = "🏷", sort_order: int = 0) -> int:
    return await execute(
        "INSERT INTO categories (city_id, name, emoji, sort_order) VALUES (?,?,?,?)",
        (city_id, name, emoji, sort_order),
    )


async def update_category(cat_id: int, **kwargs):
    allowed = {"name", "emoji", "is_active", "sort_order", "city_id"}
    fields = {k: v for k, v in kwargs.items() if k in allowed}
    if not fields:
        return
    set_clause = ", ".join(f"{k}=?" for k in fields)
    await execute(
        f"UPDATE categories SET {set_clause} WHERE id=?",
        (*fields.values(), cat_id),
    )


async def delete_category(cat_id: int):
    await execute("DELETE FROM categories WHERE id = ?", (cat_id,))


# ─────────────────────── PRODUCTS ─────────────────────────────────────────────

async def get_products(category_id: int, active_only: bool = True) -> List[aiosqlite.Row]:
    if active_only:
        return await fetchall(
            "SELECT * FROM products WHERE category_id=? AND is_active=1 ORDER BY sort_order, name",
            (category_id,),
        )
    return await fetchall(
        "SELECT * FROM products WHERE category_id=? ORDER BY sort_order, name",
        (category_id,),
    )


async def get_products_by_city(city_id: int, active_only: bool = True) -> List[aiosqlite.Row]:
    q = "SELECT * FROM products WHERE city_id=?"
    params: tuple = (city_id,)
    if active_only:
        q += " AND is_active=1"
    q += " ORDER BY sort_order, name"
    return await fetchall(q, params)


async def get_product(product_id: int) -> Optional[aiosqlite.Row]:
    return await fetchone("SELECT * FROM products WHERE id = ?", (product_id,))


async def create_product(city_id: int, category_id: int, name: str, description: str,
                          price: float, stock: int, photo_id: str = "",
                          old_price: float = 0, sort_order: int = 0) -> int:
    return await execute(
        """INSERT INTO products
           (city_id, category_id, name, description, price, old_price, stock, photo_id, sort_order)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (city_id, category_id, name, description, price, old_price, stock, photo_id, sort_order),
    )


async def update_product(product_id: int, **kwargs):
    allowed = {"name", "description", "price", "old_price", "stock",
               "photo_id", "is_active", "sort_order", "category_id", "city_id"}
    fields = {k: v for k, v in kwargs.items() if k in allowed}
    if not fields:
        return
    set_clause = ", ".join(f"{k}=?" for k in fields)
    await execute(
        f"UPDATE products SET {set_clause} WHERE id=?",
        (*fields.values(), product_id),
    )


async def delete_product(product_id: int):
    """Fully deletes a product from the DB, including cart entries and favorites (CASCADE)."""
    await execute("DELETE FROM products WHERE id = ?", (product_id,))


async def toggle_product(product_id: int):
    await execute(
        "UPDATE products SET is_active = CASE WHEN is_active=1 THEN 0 ELSE 1 END WHERE id=?",
        (product_id,),
    )


async def get_sale_products(city_id: int) -> List[aiosqlite.Row]:
    return await fetchall(
        "SELECT * FROM products WHERE city_id=? AND is_active=1 AND old_price>0 AND old_price>price ORDER BY sort_order",
        (city_id,),
    )


# ─────────────────────── CART ─────────────────────────────────────────────────

async def get_cart(user_id: int) -> List[aiosqlite.Row]:
    return await fetchall(
        """SELECT c.id, c.quantity, p.id as product_id, p.name, p.price, p.stock, p.photo_id
           FROM cart c
           JOIN products p ON p.id = c.product_id
           WHERE c.user_id = ? AND p.is_active = 1
           ORDER BY c.id""",
        (user_id,),
    )


async def add_to_cart(user_id: int, product_id: int, quantity: int = 1):
    await execute(
        """INSERT INTO cart (user_id, product_id, quantity) VALUES (?,?,?)
           ON CONFLICT(user_id, product_id) DO UPDATE SET quantity = quantity + ?""",
        (user_id, product_id, quantity, quantity),
    )


async def update_cart_quantity(user_id: int, product_id: int, quantity: int):
    if quantity <= 0:
        await execute("DELETE FROM cart WHERE user_id=? AND product_id=?", (user_id, product_id))
    else:
        await execute(
            "UPDATE cart SET quantity=? WHERE user_id=? AND product_id=?",
            (quantity, user_id, product_id),
        )


async def clear_cart(user_id: int):
    await execute("DELETE FROM cart WHERE user_id = ?", (user_id,))


async def get_cart_total(user_id: int) -> float:
    row = await fetchone(
        """SELECT SUM(c.quantity * p.price) as total
           FROM cart c JOIN products p ON p.id=c.product_id
           WHERE c.user_id=? AND p.is_active=1""",
        (user_id,),
    )
    return row["total"] or 0.0 if row else 0.0


# ─────────────────────── PROMO CODES ──────────────────────────────────────────

async def get_promo(code: str) -> Optional[aiosqlite.Row]:
    return await fetchone(
        "SELECT * FROM promo_codes WHERE code=? AND is_active=1 AND (uses_left=-1 OR uses_left>0)",
        (code.upper(),),
    )


async def use_promo(code: str):
    await execute(
        "UPDATE promo_codes SET uses_left = CASE WHEN uses_left>0 THEN uses_left-1 ELSE uses_left END WHERE code=?",
        (code.upper(),),
    )


async def create_promo(code: str, discount_type: str, discount_value: float, uses_left: int = -1) -> int:
    return await execute(
        "INSERT INTO promo_codes (code, discount_type, discount_value, uses_left) VALUES (?,?,?,?)",
        (code.upper(), discount_type, discount_value, uses_left),
    )


async def get_all_promos() -> List[aiosqlite.Row]:
    return await fetchall("SELECT * FROM promo_codes ORDER BY created_at DESC")


async def delete_promo(promo_id: int):
    await execute("DELETE FROM promo_codes WHERE id=?", (promo_id,))


async def toggle_promo(promo_id: int):
    await execute(
        "UPDATE promo_codes SET is_active = CASE WHEN is_active=1 THEN 0 ELSE 1 END WHERE id=?",
        (promo_id,),
    )


# ─────────────────────── ORDERS ───────────────────────────────────────────────

async def create_order(user_id: int, city_id: int, total: float, discount: float = 0, promo_code: str = "") -> int:
    return await execute(
        "INSERT INTO orders (user_id, city_id, total_price, discount, promo_code) VALUES (?,?,?,?,?)",
        (user_id, city_id, total, discount, promo_code),
    )


async def add_order_items(order_id: int, items: List[Dict]):
    async with get_db() as db:
        for item in items:
            await db.execute(
                "INSERT INTO order_items (order_id, product_id, name, price, quantity) VALUES (?,?,?,?,?)",
                (order_id, item["product_id"], item["name"], item["price"], item["quantity"]),
            )


async def update_order_status(order_id: int, status: str):
    await execute("UPDATE orders SET status=? WHERE id=?", (status, order_id))


async def update_order_pickup_info(order_id: int, address: str, lat: float, lon: float, comment: str = ""):
    """Saves/updates order fulfillment data (address, geolocation, comment)."""
    await execute(
        "UPDATE orders SET pickup_address=?, pickup_lat=?, pickup_lon=?, pickup_comment=? WHERE id=?",
        (address, lat, lon, comment, order_id),
    )


async def get_user_orders(user_id: int, limit: int = 10) -> List[aiosqlite.Row]:
    return await fetchall(
        "SELECT * FROM orders WHERE user_id=? ORDER BY created_at DESC LIMIT ?",
        (user_id, limit),
    )


async def get_order(order_id: int) -> Optional[aiosqlite.Row]:
    return await fetchone("SELECT * FROM orders WHERE id=?", (order_id,))


async def get_order_items(order_id: int) -> List[aiosqlite.Row]:
    return await fetchall("SELECT * FROM order_items WHERE order_id=?", (order_id,))


async def get_all_orders(limit: int = 15) -> List[aiosqlite.Row]:
    return await fetchall(
        """SELECT o.*, u.username, u.first_name FROM orders o
           LEFT JOIN users u ON u.tg_id = o.user_id
           ORDER BY o.created_at DESC LIMIT ?""",
        (limit,),
    )


# ─────────────────────── PAYMENTS ─────────────────────────────────────────────

async def create_payment(order_id: int, user_id: int, amount: float, wallet: str, timeout_minutes: int) -> int:
    expires = (datetime.utcnow() + timedelta(minutes=timeout_minutes)).strftime("%Y-%m-%d %H:%M:%S")
    return await execute(
        "INSERT INTO payments (order_id, user_id, amount, wallet, expires_at) VALUES (?,?,?,?,?)",
        (order_id, user_id, amount, wallet, expires),
    )


async def get_pending_payments() -> List[aiosqlite.Row]:
    return await fetchall(
        "SELECT * FROM payments WHERE status='waiting' AND expires_at > datetime('now')"
    )


async def get_payment_by_order(order_id: int) -> Optional[aiosqlite.Row]:
    return await fetchone("SELECT * FROM payments WHERE order_id=?", (order_id,))


async def confirm_payment(order_id: int, tx_hash: str):
    async with get_db() as db:
        await db.execute(
            "UPDATE payments SET status='confirmed', tx_hash=?, confirmed_at=datetime('now') WHERE order_id=?",
            (tx_hash, order_id),
        )
        await db.execute("UPDATE orders SET status='paid' WHERE id=?", (order_id,))


async def expire_old_payments():
    async with get_db() as db:
        await db.execute(
            "UPDATE payments SET status='expired' WHERE status='waiting' AND expires_at <= datetime('now')"
        )
        await db.execute(
            """UPDATE orders SET status='cancelled'
               WHERE status='pending' AND id IN (
                   SELECT order_id FROM payments WHERE status='expired'
               )"""
        )


# ─────────────────────── FAVORITES ────────────────────────────────────────────

async def toggle_favorite(user_id: int, product_id: int) -> bool:
    """Returns True if added, False if removed."""
    row = await fetchone("SELECT id FROM favorites WHERE user_id=? AND product_id=?", (user_id, product_id))
    if row:
        await execute("DELETE FROM favorites WHERE user_id=? AND product_id=?", (user_id, product_id))
        return False
    await execute("INSERT INTO favorites (user_id, product_id) VALUES (?,?)", (user_id, product_id))
    return True


async def get_favorites(user_id: int) -> List[aiosqlite.Row]:
    return await fetchall(
        """SELECT p.* FROM favorites f
           JOIN products p ON p.id=f.product_id
           WHERE f.user_id=? AND p.is_active=1""",
        (user_id,),
    )


# ─────────────────────── STATS ────────────────────────────────────────────────

async def get_admin_stats() -> Dict:
    users = await fetchone("SELECT COUNT(*) as cnt FROM users")
    orders_total = await fetchone("SELECT COUNT(*) as cnt FROM orders")
    orders_paid = await fetchone("SELECT COUNT(*) as cnt FROM orders WHERE status='paid'")
    revenue = await fetchone("SELECT COALESCE(SUM(total_price),0) as total FROM orders WHERE status='paid'")
    products = await fetchone("SELECT COUNT(*) as cnt FROM products WHERE is_active=1")
    cities = await fetchone("SELECT COUNT(*) as cnt FROM cities WHERE is_active=1")
    today_orders = await fetchone(
        "SELECT COUNT(*) as cnt FROM orders WHERE date(created_at)=date('now')"
    )
    return {
        "users": users["cnt"] if users else 0,
        "orders_total": orders_total["cnt"] if orders_total else 0,
        "orders_paid": orders_paid["cnt"] if orders_paid else 0,
        "revenue": revenue["total"] if revenue else 0,
        "products": products["cnt"] if products else 0,
        "cities": cities["cnt"] if cities else 0,
        "today_orders": today_orders["cnt"] if today_orders else 0,
    }


# ─────────────────────── BROADCASTS ───────────────────────────────────────────

async def save_broadcast(text: str, sent_count: int):
    await execute("INSERT INTO broadcasts (text, sent_count) VALUES (?,?)", (text, sent_count))


# ─────────────────────── PAYMENT METHODS ──────────────────────────────────────

async def get_all_payment_methods(active_only: bool = False) -> List[aiosqlite.Row]:
    if active_only:
        return await fetchall(
            "SELECT * FROM payment_methods WHERE is_active=1 ORDER BY sort_order, name"
        )
    return await fetchall("SELECT * FROM payment_methods ORDER BY sort_order, name")


async def get_payment_method(method_id: int) -> Optional[aiosqlite.Row]:
    return await fetchone("SELECT * FROM payment_methods WHERE id=?", (method_id,))


async def create_payment_method(name: str, description: str = "", details: str = "", sort_order: int = 0) -> int:
    return await execute(
        "INSERT INTO payment_methods (name, description, details, sort_order) VALUES (?,?,?,?)",
        (name, description, details, sort_order),
    )


async def update_payment_method(method_id: int, **kwargs):
    allowed = {"name", "description", "details", "is_active", "sort_order"}
    fields = {k: v for k, v in kwargs.items() if k in allowed}
    if not fields:
        return
    set_clause = ", ".join(f"{k}=?" for k in fields)
    await execute(
        f"UPDATE payment_methods SET {set_clause} WHERE id=?",
        (*fields.values(), method_id),
    )


async def delete_payment_method(method_id: int):
    await execute("DELETE FROM payment_methods WHERE id=?", (method_id,))


async def toggle_payment_method(method_id: int):
    await execute(
        "UPDATE payment_methods SET is_active = CASE WHEN is_active=1 THEN 0 ELSE 1 END WHERE id=?",
        (method_id,),
    )

