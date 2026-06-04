#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Генератор XML Sitemap для kristallik.com.ua
Створює sitemap з CSV/XML фіду
"""

import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime
import re

FEED_FILE = Path(__file__).parent / "Analylics" / "feed_fixed.xml"
SITEMAP_OUTPUT = Path(__file__).parent / "Analylics" / "sitemap-products.xml"
DOMAIN = "https://kristallik.com.ua"

def clean_html(text):
    """Видаляє HTML теги"""
    if not text:
        return ""
    text = re.sub(r'<[^>]+>', '', text)
    return text.strip()

def generate_sitemap():
    """Генерує sitemap з фіду"""

    print("📖 Читаю фід...")
    try:
        tree = ET.parse(FEED_FILE)
        root = tree.getroot()
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return

    # Namespace
    ns = {'g': 'http://base.google.com/ns/1.0'}

    # Створюємо sitemap
    urlset = ET.Element('urlset')
    urlset.set('xmlns', 'http://www.sitemaps.org/schemas/sitemap/0.9')
    urlset.set('xmlns:image', 'http://www.google.com/schemas/sitemap-image/1.1')

    # Обробляємо кожен товар
    items = root.findall('.//item')
    print(f"📦 Обробляю {len(items)} товарів...")

    count = 0
    for item in items:
        # URL товара
        link_elem = item.find('g:link', ns)
        if link_elem is None or not link_elem.text:
            continue

        link = link_elem.text

        # Додаємо URL в sitemap
        url = ET.SubElement(urlset, 'url')
        loc = ET.SubElement(url, 'loc')
        loc.text = link

        # LastMod (поточна дата)
        lastmod = ET.SubElement(url, 'lastmod')
        lastmod.text = datetime.now().strftime('%Y-%m-%d')

        # Change frequency
        changefreq = ET.SubElement(url, 'changefreq')
        changefreq.text = 'weekly'

        # Priority (0.8 для товарів)
        priority = ET.SubElement(url, 'priority')
        priority.text = '0.8'

        # Image (якщо є)
        image_elem = item.find('g:image_link', ns)
        if image_elem is not None and image_elem.text:
            image = ET.SubElement(url, 'image:image')
            image_loc = ET.SubElement(image, 'image:loc')
            image_loc.text = image_elem.text

            # Image title
            title_elem = item.find('g:title', ns)
            if title_elem is not None:
                image_title = ET.SubElement(image, 'image:title')
                image_title.text = clean_html(title_elem.text)

        count += 1

    # Сортуємо по URL
    urls = list(urlset)
    urls.sort(key=lambda x: x.find('loc').text)
    for url in urls:
        urlset.remove(url)
    for url in urls:
        urlset.append(url)

    # Зберігаємо
    print(f"\n💾 Зберігаю sitemap ({count} URLs)...")
    tree = ET.ElementTree(urlset)
    tree.write(SITEMAP_OUTPUT, encoding='utf-8', xml_declaration=True)

    print(f"✅ Sitemap готов: {SITEMAP_OUTPUT}")
    print(f"\n📄 Додай це в robots.txt:")
    print(f"Sitemap: {DOMAIN}/sitemap-products.xml")

if __name__ == "__main__":
    generate_sitemap()
