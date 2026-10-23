# Telegram Shop Bot

Полноценный Telegram-магазин с поддержкой нескольких способов оплаты, управляемых через админ-панель.

---

## Возможности

- 🏙 Города, категории, товары с фото
- 🛒 Корзина, промокоды, скидки
- 💳 Динамические способы оплаты (управляются через админ-панель)
- 🔄 Автоматическая проверка USDT TRC20 платежей
- 👤 Профиль, история заказов, избранное
- 📣 Рассылка всем пользователям
- ⭐ Акции (товары со скидкой)
- 🔗 Реферальная программа

---

## Быстрый старт

### 1. Клонирование и настройка

```bash
git clone <repo_url> shopbot
cd shopbot
cp .env.example .env
nano .env   # заполните все поля
```

### 2. Установка зависимостей

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Запуск (разработка)

```bash
python main.py
```

---

## Развёртывание на VPS (Production)

### Автоматическое развёртывание

```bash
bash deploy.sh
```

### Ручное развёртывание

```bash
# Установка зависимостей
python3 -m venv /opt/shopbot/venv
/opt/shopbot/venv/bin/pip install -r requirements.txt

# Настройка systemd
sudo cp bot.service /etc/systemd/system/shopbot.service
# Отредактируйте пути в bot.service под ваш сервер
sudo systemctl daemon-reload
sudo systemctl enable shopbot
sudo systemctl start shopbot
```

### Управление сервисом

```bash
sudo systemctl start shopbot      # запуск
sudo systemctl stop shopbot       # остановка
sudo systemctl restart shopbot    # перезапуск
sudo systemctl status shopbot     # статус
sudo journalctl -u shopbot -f     # логи в реальном времени
```

---

## Переменные окружения (.env)

| Переменная | Описание |
|---|---|
| `BOT_TOKEN` | Токен бота от @BotFather |
| `ADMIN_IDS` | ID администраторов через запятую |
| `SHOP_NAME` | Название магазина |
| `SHOP_USERNAME` | Username бота (для поддержки) |
| `USDT_WALLET` | Кошелёк USDT TRC20 (резерв) |
| `PAYMENT_TIMEOUT_MINUTES` | Время ожидания оплаты (мин) |
| `PAYMENT_CONFIRMATIONS` | Мин. подтверждений в сети |
| `DATABASE_PATH` | Путь к SQLite файлу |
| `TRONGRID_API_KEY` | Ключ TronGrid API |

---

## Способы оплаты

Способы оплаты управляются через **Админ-панель → 💳 Способы оплаты**.

Для каждого способа можно задать:
- **Название** (например: USDT TRC20, Карта Tinkoff, Наличные)
- **Описание** — инструкция для пользователя
- **Реквизиты** — адрес кошелька, номер карты и т.д.
- **Статус** — включить/отключить

Пользователи видят только активные способы при оформлении заказа.

---

## Структура проекта

```
shopbot/
├── main.py                 # Точка входа
├── requirements.txt
├── .env                    # Настройки (не коммитить!)
├── .env.example            # Шаблон настроек
├── bot.service             # systemd unit
├── deploy.sh               # Скрипт развёртывания
│
├── config/
│   └── settings.py         # Загрузка .env
│
├── database/
│   └── db.py               # Все операции с SQLite
│
├── handlers/
│   ├── start.py            # /start, FAQ, поддержка
│   ├── catalog.py          # Каталог
│   ├── cart.py             # Корзина, оплата
│   ├── profile.py          # Профиль, заказы
│   └── admin.py            # Админ-панель
│
├── keyboards/
│   └── kb.py               # Все клавиатуры
│
├── middlewares/
│   └── throttle.py         # Антифлуд
│
├── services/
│   └── tron_checker.py     # Автопроверка USDT TRC20
│
├── states/
│   └── states.py           # FSM-состояния
│
└── data/
    └── shop.db             # SQLite база данных
```
