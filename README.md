# 🎯 Tennants Auction Parser

Простой и эффективный парсер аукционного дома Tennants с полным набором функций.

## 📁 Структура проекта

```
auctions/
├── perfect_lot_parser.py       # 🚀 Основной класс парсера
├── parse_full_auction.py       # 📦 Скрипт для парсинга всего аукциона
├── test_current_lot.py         # 🧪 Тестирование на одном лоте
├── find_upcoming_auctions.py   # 🔍 Поиск предстоящих аукционов
├── requirements.txt            # 📋 Зависимости Python
├── tennants_perfect_data/      # 💾 Данные парсинга (CSV + изображения)
├── venv/                       # 🐍 Виртуальная среда Python
└── MISSING_FIELDS_ANALYSIS.md  # 📊 Анализ полей данных
```

## 🚀 Быстрый старт

### 1. Тестирование одного лота
```bash
python3 test_current_lot.py
```

### 2. Парсинг всего аукциона
```bash
python3 parse_full_auction.py
```

### 3. Поиск новых аукционов
```bash
python3 find_upcoming_auctions.py
```

## 📊 Извлекаемые данные

✅ **Заполняемые поля:**
- `auction_id` - ID аукциона
- `lot_number` - Номер лота  
- `lot_title` - Название лота
- `lot_description` - Описание лота
- `lot_estimate` - Оценочная стоимость
- `buyer_premium` - Комиссия покупателя
- `condition_report` - Отчет о состоянии
- `image_url` - URL изображения
- `image_high_res_url` - URL HD изображения

⏳ **Доступны после аукциона:**
- `lot_sold_price` - Цена продажи
- `lot_status` - Статус лота (Sold/Unsold/Withdrawn)

## 🎯 Особенности

- 🔄 **Надежность**: Обработка ошибок и повторные попытки
- 📸 **Изображения**: Автоматическое скачивание изображений лотов
- 💾 **CSV экспорт**: Все данные сохраняются в удобном формате
- 🧪 **Тестирование**: Легкое тестирование на отдельных лотах
- 📊 **Статистика**: Подробные отчеты о процессе парсинга

## 📋 Требования

```
pip install -r requirements.txt
```

- Python 3.7+
- requests
- beautifulsoup4

## 🎯 Проверенные аукционы

- ✅ **Antiques & Interiors** (96 лотов, 100% успех)
- ✅ **Все поля корректно заполняются**
- ✅ **HD изображения скачиваются автоматически** 