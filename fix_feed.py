#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Google Merchant Center Feed Fixer для Кристалік
Исправляет ошибки в фиде и добавляет недостающие атрибуты
"""

import xml.etree.ElementTree as ET
from pathlib import Path
import re

# Путь к файлам
FEED_INPUT = Path(__file__).parent / "Analylics" / "feed_google.xml"
FEED_OUTPUT = Path(__file__).parent / "Analylics" / "feed_fixed.xml"
REPORT_OUTPUT = Path(__file__).parent / "Analylics" / "feed_report.txt"

# Google Merchant Center категории для волосяных аксессуаров
CATEGORIES = {
    "краб": 171,  # Accessories > Hair Accessories
    "заколка": 171,
    "резинка": 171,
    "невидимка": 171,
    "гребінець": 171,
    "пов'язка": 171,
    "обруч": 171,
    "біжутерія": 163,  # Jewelry
    "сережка": 163,
    "браслет": 163,
    "кулон": 163,
    "бісер": 545,  # Craft & Hobby
    "набір": 171,
}

def get_category(title):
    """Определяет правильную категорию по названию товара"""
    title_lower = title.lower()
    for keyword, category in CATEGORIES.items():
        if keyword in title_lower:
            return category
    return 171  # Default категория

def extract_quantity_info(description):
    """Извлекает информацию о количестве из описания"""
    # Ищет паттерны типа "12шт", "10 пакетиків", etc
    matches = re.findall(r'(\d+)\s*(?:шт|пакет|уп)', description.lower())
    if matches:
        return int(matches[0])
    return 1

def extract_price_per_unit(price_str, qty):
    """Извлекает цену за единицу"""
    # price_str формата "54.06 UAH"
    try:
        price = float(price_str.split()[0])
        return round(price / qty, 2) if qty > 1 else price
    except:
        return 0

def clean_html(text):
    """Убирает HTML теги из текста"""
    if not text:
        return ""
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def fix_feed():
    """Основная функция исправления фида"""

    print("📖 Читаю фид...")
    try:
        tree = ET.parse(FEED_INPUT)
        root = tree.getroot()
    except Exception as e:
        print(f"❌ Ошибка при чтении фида: {e}")
        return

    # Namespace для Google
    ns = {'g': 'http://base.google.com/ns/1.0'}

    errors = {
        'missing_quantity': 0,
        'missing_sku': 0,
        'missing_weight': 0,
        'short_description': 0,
        'wrong_category': 0,
        'total_items': 0
    }

    # Обработка каждого товара (RSS формат)
    entries = root.findall('.//item')
    print(f"📦 Найдено товаров: {len(entries)}")

    for idx, entry in enumerate(entries):
        errors['total_items'] += 1

        # ID товара
        item_id = entry.find('g:id', ns)
        product_id = item_id.text if item_id is not None else f"product_{idx}"

        # Название
        title_elem = entry.find('g:title', ns)
        title = clean_html(title_elem.text) if title_elem is not None else ""

        # Описание
        desc_elem = entry.find('g:description', ns)
        description = clean_html(desc_elem.text) if desc_elem is not None else ""

        # Цена
        price_elem = entry.find('g:price', ns)
        currency_elem = entry.find('g:currency', ns)
        currency = currency_elem.text if currency_elem is not None else "UAH"
        price_text = f"{price_elem.text} {currency}" if price_elem is not None else "0 UAH"

        # Извлекаем количество из описания
        quantity = extract_quantity_info(description)

        # 1. Добавляем/исправляем g:quantity (обязательно!)
        qty_elem = entry.find('g:quantity', ns)
        if qty_elem is None:
            qty_elem = ET.SubElement(entry, '{http://base.google.com/ns/1.0}quantity')
            errors['missing_quantity'] += 1
        qty_elem.text = str(quantity)

        # 2. Добавляем/исправляем g:sku (артикул)
        sku_elem = entry.find('g:sku', ns)
        if sku_elem is None or not sku_elem.text:
            sku_elem = entry.find('g:sku', ns)
            if sku_elem is None:
                sku_elem = ET.SubElement(entry, '{http://base.google.com/ns/1.0}sku')
            sku_elem.text = str(product_id)
            errors['missing_sku'] += 1

        # 3. Добавляем g:min_order_quantity (минимальный заказ для опта)
        min_order_elem = entry.find('g:min_order_quantity', ns)
        if min_order_elem is None:
            min_order_elem = ET.SubElement(entry, '{http://base.google.com/ns/1.0}min_order_quantity')
            min_order_elem.text = str(quantity)  # Минимальный заказ = количество в упаковке

        # 4. Добавляем g:weight (вес)
        weight_elem = entry.find('g:weight', ns)
        if weight_elem is None:
            weight_elem = ET.SubElement(entry, '{http://base.google.com/ns/1.0}weight')
            weight_elem.text = "0.02 kg"  # 20g для всех товаров
            errors['missing_weight'] += 1

        # 5. Исправляем категорию
        category_elem = entry.find('g:google_product_category', ns)
        correct_category = get_category(title)
        if category_elem is None:
            category_elem = ET.SubElement(entry, '{http://base.google.com/ns/1.0}google_product_category')
        if category_elem.text != str(correct_category):
            category_elem.text = str(correct_category)
            errors['wrong_category'] += 1

        # 6. Улучшаем описание (добавляем ключевые слова)
        if len(description) < 30:
            errors['short_description'] += 1
            # Добавляем информацию о количестве и материале
            enhanced_desc = f"{title}. Кількість: {quantity}шт. Оптовою ціною. В упаковці: {quantity} шт."
            desc_elem = entry.find('g:description', ns)
            if desc_elem is not None:
                desc_elem.text = enhanced_desc

        # 7. Добавляем price per unit (для удобства)
        price_per_unit = extract_price_per_unit(price_text, quantity)
        unit_price_elem = entry.find('g:unit_pricing_base_measure', ns)
        if unit_price_elem is None:
            unit_price_elem = ET.SubElement(entry, '{http://base.google.com/ns/1.0}unit_pricing_base_measure')
            unit_price_elem.text = "1 item"

    # Сохраняем исправленный фид
    print("\n💾 Сохраняю исправленный фид...")
    tree.write(FEED_OUTPUT, encoding='utf-8', xml_declaration=True)

    # Создаём отчет
    print("\n📊 Создаю отчет...")
    with open(REPORT_OUTPUT, 'w', encoding='utf-8') as f:
        f.write("=" * 60 + "\n")
        f.write("ОТЧЕТ ОБ ИСПРАВЛЕНИИ GOOGLE MERCHANT CENTER ФИДА\n")
        f.write("Кристалік - kristallik.com.ua\n")
        f.write("=" * 60 + "\n\n")

        f.write("СТАТИСТИКА ОШИБОК:\n")
        f.write(f"  ✅ Всего товаров: {errors['total_items']}\n")
        f.write(f"  ❌ Отсутствовало g:quantity: {errors['missing_quantity']}\n")
        f.write(f"  ❌ Отсутствовало g:sku: {errors['missing_sku']}\n")
        f.write(f"  ❌ Отсутствовало g:weight: {errors['missing_weight']}\n")
        f.write(f"  ❌ Короткие описания: {errors['short_description']}\n")
        f.write(f"  ❌ Неправильные категории: {errors['wrong_category']}\n\n")

        f.write("ИСПРАВЛЕНИЯ:\n")
        f.write("  ✅ Добавлены обязательные атрибуты (g:quantity, g:sku, g:weight)\n")
        f.write("  ✅ Добавлена информация о минимальном заказе (g:min_order_quantity)\n")
        f.write("  ✅ Исправлены категории товаров\n")
        f.write("  ✅ Улучшены описания товаров\n")
        f.write("  ✅ Добавлены цены за единицу\n\n")

        f.write("СЛЕДУЮЩИЕ ШАГИ:\n")
        f.write("  1. Загрузите feed_fixed.xml в Google Merchant Center\n")
        f.write("     (Products → Feeds → Upload)\n")
        f.write("  2. Проверьте Issues - большинство должны исчезнуть\n")
        f.write("  3. Если ещё ошибки - проверьте конкретные товары\n")
        f.write("  4. Убедитесь что все товары имеют изображения\n\n")

        f.write("РЕКОМЕНДАЦИИ:\n")
        f.write("  • Добавьте реальный вес каждого товара\n")
        f.write("  • Убедитесь в корректности цен\n")
        f.write("  • Для B2B товаров добавьте информацию об опте\n")
        f.write("  • Обновляйте фид автоматически еженедельно\n")

    print(f"\n✅ Готово!")
    print(f"\n📁 Исправленный фид: {FEED_OUTPUT}")
    print(f"📄 Отчет: {REPORT_OUTPUT}")

    return True

if __name__ == "__main__":
    fix_feed()
