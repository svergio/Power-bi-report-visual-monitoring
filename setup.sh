#!/bin/bash

# Скрипт быстрой установки Power BI Scraper

echo "=================================="
echo "Power BI Scraper - Установка"
echo "=================================="
echo ""

# Проверка Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 не найден. Пожалуйста, установите Python 3."
    exit 1
fi

echo "✓ Python 3 найден: $(python3 --version)"

# Создание виртуального окружения
echo ""
echo "📦 Создание виртуального окружения..."
if [ -d "venv" ]; then
    echo "⚠️  Виртуальное окружение уже существует"
    read -p "Пересоздать? (y/n): " recreate
    if [ "$recreate" = "y" ]; then
        rm -rf venv
        python3 -m venv venv
    fi
else
    python3 -m venv venv
fi

# Активация виртуального окружения
echo "🔄 Активация виртуального окружения..."
source venv/bin/activate

# Обновление pip
echo "⬆️  Обновление pip..."
pip install --upgrade pip

# Установка зависимостей
echo ""
echo "📥 Установка зависимостей..."
pip install -r requirements.txt

# Опциональная установка Selenium
echo ""
read -p "Установить Selenium для работы с динамическими страницами? (y/n): " install_selenium
if [ "$install_selenium" = "y" ]; then
    pip install selenium webdriver-manager
    echo "✓ Selenium установлен"
fi

# Создание конфигурационного файла
echo ""
if [ ! -f "config.env" ]; then
    echo "📝 Создание конфигурационного файла..."
    cp config_example.env config.env
    echo "✓ Файл config.env создан"
    echo "⚠️  Пожалуйста, отредактируйте config.env и укажите свои данные"
else
    echo "ℹ️  Файл config.env уже существует"
fi

# Создание output директории
mkdir -p output
echo "✓ Директория output создана"

# Вывод финальной информации
echo ""
echo "=================================="
echo "✅ Установка завершена!"
echo "=================================="
echo ""
echo "Следующие шаги:"
echo "1. Отредактируйте config.env и укажите свои данные"
echo "2. Активируйте виртуальное окружение: source venv/bin/activate"
echo "3. Запустите тест: python test_scraper.py --interactive"
echo "4. Или запустите скрапер: python scraper_with_config.py"
echo ""
echo "Документация: README.md"
echo ""



