#!/bin/bash
# deploy.sh — скрипт развёртывания бота на VPS
# Использование: bash deploy.sh

set -e

INSTALL_DIR="/opt/shopbot"
SERVICE_NAME="shopbot"

echo "=== Развёртывание Telegram Shop Bot ==="

# 1. Создаём директорию
sudo mkdir -p "$INSTALL_DIR"
sudo cp -r . "$INSTALL_DIR/"
cd "$INSTALL_DIR"

# 2. Устанавливаем Python-зависимости
python3 -m venv venv
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt

# 3. Создаём .env если не существует
if [ ! -f .env ]; then
    cp .env.example .env
    echo ""
    echo "⚠️  Файл .env создан из шаблона. Заполните его перед запуском:"
    echo "    nano $INSTALL_DIR/.env"
    echo ""
fi

# 4. Создаём директорию для данных
mkdir -p data

# 5. Устанавливаем systemd-сервис
sudo cp bot.service /etc/systemd/system/${SERVICE_NAME}.service
# Заменяем путь в сервисе на актуальный
sudo sed -i "s|/opt/shopbot|$INSTALL_DIR|g" /etc/systemd/system/${SERVICE_NAME}.service

sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE_NAME"

echo ""
echo "=== Готово! ==="
echo ""
echo "Команды управления:"
echo "  Запуск:    sudo systemctl start $SERVICE_NAME"
echo "  Статус:    sudo systemctl status $SERVICE_NAME"
echo "  Логи:      sudo journalctl -u $SERVICE_NAME -f"
echo "  Остановка: sudo systemctl stop $SERVICE_NAME"
echo ""
echo "Не забудьте заполнить: nano $INSTALL_DIR/.env"
