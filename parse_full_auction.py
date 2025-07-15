#!/usr/bin/env python3
"""
Парсер для полного аукциона Tennants
"""

import time
import requests
from bs4 import BeautifulSoup
import re
from pathlib import Path
import csv
from datetime import datetime
from urllib.parse import urljoin, urlparse
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

class FullAuctionParser:
    def __init__(self, auction_title="", auction_date=""):
        # 🚀 ОПТИМИЗИРОВАННАЯ СЕССИЯ С ПУЛОМ СОЕДИНЕНИЙ
        self.session = requests.Session()
        
        # Настройка повторных попыток и пула соединений
        retry_strategy = Retry(
            total=3,
            backoff_factor=0.3,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=20,  # пул из 20 соединений
            pool_maxsize=20,
            pool_block=False
        )
        
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        
        # 🔥 СОЗДАЕМ УНИКАЛЬНУЮ ПАПКУ ДЛЯ ПАРСИНГА
        now = datetime.now()
        parsing_time = now.strftime("%Y-%m-%d_%H-%M")
        
        # Очищаем название аукциона для файловой системы
        clean_auction_name = self.clean_filename(auction_title) if auction_title else "Unknown_Auction"
        clean_auction_date = auction_date if auction_date else "Unknown_Date"
        
        # Создаем уникальное имя папки
        folder_name = f"{clean_auction_name}_{clean_auction_date}_parsed_{parsing_time}"
        
        self.working_dir = Path(folder_name)
        self.working_dir.mkdir(exist_ok=True)
        
        self.images_dir = self.working_dir / "images"
        self.images_dir.mkdir(exist_ok=True)
        
        # 🔥 СОЗДАЕМ ИНФОРМАТИВНОЕ ИМЯ ФАЙЛА БАЗЫ ДАННЫХ
        db_filename = f"{clean_auction_name}_{clean_auction_date}_{parsing_time}.csv"
        self.db_file = self.working_dir / db_filename
        self.init_database()
        
        # Статистика заполненности полей
        self.field_stats = {}
        
        print(f"📁 Создана папка парсинга: {self.working_dir}")
    
    def clean_filename(self, text):
        """Очистка текста для использования в имени файла/папки"""
        # Убираем специальные символы и заменяем пробелы на подчеркивания
        clean = re.sub(r'[^\w\s-]', '', text)
        clean = re.sub(r'[-\s]+', '_', clean)
        return clean[:50]  # Ограничиваем длину
    
    def init_database(self):
        """Инициализация CSV базы с правильными полями"""
        headers = [
            'timestamp',
            'auction_id', 
            'auction_title',
            'auction_date',
            'lot_system_id',
            'lot_number',
            'lot_title',
            'lot_description', 
            'lot_url',
            'image_url',
            'image_high_res_url',
            'additional_images_count',
            'additional_images_urls',
            'lot_estimate',
            'lot_sold_price',
            'lot_status',
            'buyer_premium',
            'condition_report',
            'dimensions',
            'materials',
            'period_dating',
            'artist_maker',
            'origin_country',
            'lot_category',
            'full_lot_info'
        ]
        
        if not self.db_file.exists():
            with open(self.db_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(headers)
    
    def parse_lot_page(self, lot_url):
        """Парсинг страницы лота"""
        try:
            print(f"🎯 ПАРСИНГ ЛОТА: {lot_url}")
            
            response = self.session.get(lot_url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Извлекаем все данные
            lot_data = {}
            lot_data['url'] = lot_url
            lot_data['timestamp'] = datetime.now().isoformat()
            
            # Auction ID из URL
            auction_id_match = re.search(r'au=(\d+)', lot_url)
            lot_data['auction_id'] = auction_id_match.group(1) if auction_id_match else ""
            
            # System ID лота из URL
            lot_id_match = re.search(r'lot=(\d+)', lot_url)
            lot_data['lot_system_id'] = lot_id_match.group(1) if lot_id_match else ""
            
            # Название аукциона из breadcrumb
            auction_title = ""
            
            # 🔥 УЛУЧШЕННОЕ ИЗВЛЕЧЕНИЕ НАЗВАНИЯ АУКЦИОНА
            # Способ 1: Ищем в H4 с классом auction-title  
            auction_h4 = soup.find('h4', {'class': 'auction-title'}) or soup.find('H4', {'class': 'auction-title'})
            if auction_h4:
                auction_link = auction_h4.find('a')
                if auction_link:
                    auction_title = auction_link.get_text(strip=True)
                    # Убираем HTML entities
                    auction_title = auction_title.replace('&amp;', '&')
            
            # Способ 2: Альтернативный поиск в auctiondetails tab
            if not auction_title:
                auction_tab = soup.find('div', {'id': 'auctiondetails'})
                if auction_tab:
                    auction_link = auction_tab.find('a', href=re.compile(r'auction/search\?au='))
                    if auction_link:
                        auction_title = auction_link.get_text(strip=True).replace('&amp;', '&')
            
            # Способ 3: Поиск в breadcrumb (оригинальный метод как резерв)
            if not auction_title:
                breadcrumb = soup.find('ol', {'class': 'breadcrumb'}) 
                if breadcrumb:
                    auction_link = breadcrumb.find('a', href=re.compile(r'auction/details'))
                    if auction_link:
                        auction_title = auction_link.get_text(strip=True)
            
            # Способ 4: Поиск в скрытых полях формы
            if not auction_title:
                append_text_input = soup.find('input', {'id': 'AppendText'})
                if append_text_input:
                    append_value = append_text_input.get('value', '')
                    # Извлекаем название аукциона из строки типа "Lot 1 (Antiques & Interiors, to include...)"
                    match = re.search(r'\(([^,]+,[^)]+)\)', append_value)
                    if match:
                        auction_title = match.group(1).replace('&amp;', '&')
            
            lot_data['auction_title'] = auction_title
            
            # Дата аукциона - ищем в тексте страницы
            page_text = soup.get_text()
            year_match = re.search(r'20\d{2}', page_text)
            lot_data['auction_date'] = year_match.group(0) if year_match else "2025"
            
            # 🔥 УЛУЧШЕННОЕ ИЗВЛЕЧЕНИЕ НОМЕРА ЛОТА
            lot_number = ""
            # Ищем в span с классом lot-number
            lot_number_span = soup.find('span', {'class': 'lot-number'})
            if lot_number_span:
                lot_text = lot_number_span.get_text(strip=True)
                lot_match = re.search(r'Lot\s+(\d+)', lot_text)
                if lot_match:
                    lot_number = lot_match.group(1)
            
            # Альтернативный поиск в H3 с классом lot-a-t
            if not lot_number:
                h3_lot = soup.find('h3', {'class': 'lot-a-t'}) or soup.find('H3', {'class': 'lot-a-t'})
                if h3_lot:
                    lot_number = h3_lot.get_text(strip=True)
            
            # Поиск в title страницы
            if not lot_number:
                title_tag = soup.find('title')
                if title_tag:
                    title_text = title_tag.get_text(strip=True)
                    lot_match = re.search(r'Lot\s+(\d+)', title_text)
                    if lot_match:
                        lot_number = lot_match.group(1)
            
            lot_data['lot_number'] = lot_number
            lot_data['lot_title'] = lot_number  # Используем номер как заголовок
            
            # 🔥 УЛУЧШЕННОЕ ИЗВЛЕЧЕНИЕ ОПИСАНИЯ ЛОТА  
            lot_description = ""
            # Ищем в div с классом lot-desc
            lot_desc_div = soup.find('div', {'class': 'lot-desc'})
            if lot_desc_div:
                # Извлекаем текст из всех параграфов
                paragraphs = lot_desc_div.find_all('p')
                if paragraphs:
                    desc_parts = []
                    for p in paragraphs:
                        text = p.get_text(strip=True)
                        if text:
                            desc_parts.append(text)
                    lot_description = ' '.join(desc_parts)
                else:
                    # Если нет параграфов, берем весь текст
                    lot_description = lot_desc_div.get_text(strip=True)
            
            # Альтернативный поиск в title/meta description
            if not lot_description:
                meta_desc = soup.find('meta', {'name': 'description'})
                if meta_desc:
                    content = meta_desc.get('content', '')
                    # Убираем "Lot X - " из начала
                    desc_clean = re.sub(r'^Lot\s+\d+\s*[-:]?\s*', '', content)
                    lot_description = desc_clean
            
            lot_data['lot_description'] = lot_description
            
            # Изображения - ищем main image
            main_img = soup.find('img', {'id': 'lot-image'}) or soup.find('img', {'class': 'main-image'}) or soup.find('img', src=re.compile(r'stock.*medium'))
            if main_img:
                img_src = main_img.get('src', '')
                if img_src:
                    # Полный URL
                    if img_src.startswith('//'):
                        img_src = 'https:' + img_src
                    elif img_src.startswith('/'):
                        img_src = 'https://tennants.blob.core.windows.net' + img_src
                    
                    lot_data['image_url'] = img_src
                    # HD версия (убираем -medium)
                    lot_data['image_high_res_url'] = img_src.replace('-medium', '')
                else:
                    lot_data['image_url'] = ""
                    lot_data['image_high_res_url'] = ""
            else:
                lot_data['image_url'] = ""
                lot_data['image_high_res_url'] = ""
            
            # 🔥 УЛУЧШЕННОЕ ИЗВЛЕЧЕНИЕ ОЦЕНОЧНОЙ СТОИМОСТИ
            estimate_text = ""
            # Ищем в div с классом estimate
            estimate_div = soup.find('div', {'class': 'estimate'})
            if estimate_div:
                estimate_text = estimate_div.get_text(strip=True)
                # Очищаем от "Estimate" и лишних символов
                estimate_text = re.sub(r'^Estimate\s*', '', estimate_text, flags=re.IGNORECASE)
                # Заменяем HTML entities
                estimate_text = estimate_text.replace('&#163;', '£')
            
            # Альтернативный поиск в тексте страницы
            if not estimate_text:
                estimate_match = re.search(r'Estimate[:\s]*£[\d,\s-]+', page_text, re.IGNORECASE)
                if estimate_match:
                    estimate_text = estimate_match.group(0).replace('Estimate', '').strip(' :')
            
            lot_data['lot_estimate'] = estimate_text
            
            # Цена продажи и статус (обычно пустые для будущих аукционов)
            lot_data['lot_sold_price'] = ""
            lot_data['lot_status'] = ""
            
            # 🔥 УЛУЧШЕННОЕ ИЗВЛЕЧЕНИЕ КОМИССИИ ПОКУПАТЕЛЯ
            premium_text = ""
            # Ищем в div с классом buyers-premium
            premium_div = soup.find('div', {'class': 'buyers-premium'})
            if premium_div:
                premium_full_text = premium_div.get_text(strip=True)
                # Извлекаем только процент
                premium_match = re.search(r'(\d+(?:\.\d+)?)%', premium_full_text)
                if premium_match:
                    premium_text = f"{premium_match.group(1)}%"
                
            # Альтернативный поиск в тексте страницы
            if not premium_text:
                premium_match = re.search(r'(\d+(?:\.\d+)?)%', page_text)
                premium_text = f"{premium_match.group(1)}%" if premium_match else "22.00%"
            
            lot_data['buyer_premium'] = premium_text
            
            # 🔥 УЛУЧШЕННОЕ ИЗВЛЕЧЕНИЕ ОТЧЕТА О СОСТОЯНИИ
            condition_report = ""
            
            # Ищем в табе condition
            condition_tab = soup.find('div', {'id': 'condition'})
            if condition_tab:
                # Извлекаем первый параграф с текстом
                condition_paragraphs = condition_tab.find_all('p')
                for p in condition_paragraphs:
                    text = p.get_text(strip=True)
                    # Пропускаем пустые и стандартные disclaimer тексты
                    if text and not text.startswith('We are happy to provide') and not text.startswith('We cannot guarantee'):
                        condition_report = text
                        break
            
            # Альтернативные фразы
            if not condition_report:
                if "no condition report" in page_text.lower():
                    condition_report = "There is no condition report for this lot. Click the 'Ask a question' button below to request further information."
                elif "condition report" in page_text.lower():
                    condition_match = re.search(r'[^.]*condition report[^.]*\.', page_text, re.IGNORECASE)
                    condition_report = condition_match.group(0) if condition_match else "We are happy to provide Condition Reports to Prospective Buyers, but would welcome your request as soon as possible, preferably at least 48 hours before the Day of Sale."
                else:
                    condition_report = "We are happy to provide Condition Reports to Prospective Buyers, but would welcome your request as soon as possible, preferably at least 48 hours before the Day of Sale."
            
            lot_data['condition_report'] = condition_report
            
            # 🔥 ИЗВЛЕЧЕНИЕ ДОПОЛНИТЕЛЬНЫХ ПОЛЕЙ
            description_full = lot_data.get('lot_description', '')
            
            # Размеры
            lot_data['dimensions'] = self.extract_dimensions(description_full)
            
            # Материалы
            lot_data['materials'] = self.extract_materials(description_full)
            
            # Период и датировка
            lot_data['period_dating'] = self.extract_period_dating(description_full)
            
            # Художник/производитель
            lot_data['artist_maker'] = self.extract_artist_maker(description_full)
            
            # Страна происхождения
            lot_data['origin_country'] = self.extract_origin_country(description_full)
            
            # Категория лота
            lot_data['lot_category'] = self.extract_lot_category(soup)
            
            # Дополнительные изображения
            additional_images = self.extract_additional_images(soup)
            lot_data['additional_images_count'] = len(additional_images)
            lot_data['additional_images_urls'] = ' | '.join(additional_images) if additional_images else ""
            
            # Полная информация о лоте
            full_info = f"Lot {lot_data.get('lot_number', 'N/A')} ({lot_data.get('auction_title', 'Unknown Auction')}, {lot_data.get('auction_date', 'Unknown Date')})\n"
            full_info += lot_data.get('lot_description', '')
            if lot_data.get('lot_estimate'):
                full_info += f"\nEstimate: {lot_data['lot_estimate']}"
            if lot_data.get('dimensions'):
                full_info += f"\nDimensions: {lot_data['dimensions']}"
            if lot_data.get('materials'):
                full_info += f"\nMaterials: {lot_data['materials']}"
            if lot_data.get('period_dating'):
                full_info += f"\nPeriod: {lot_data['period_dating']}"
            lot_data['full_lot_info'] = full_info
            
            # 🔍 ДИАГНОСТИКА ИЗВЛЕЧЕННЫХ ДАННЫХ
            print(f"✅ ИЗВЛЕЧЕННЫЕ ДАННЫЕ:")
            important_fields = ['lot_number', 'lot_description', 'lot_estimate', 'buyer_premium']
            for field in important_fields:
                value = lot_data.get(field, '')
                if value:
                    display_value = str(value)[:100] + "..." if len(str(value)) > 100 else str(value)
                    print(f"   ✅ {field}: {display_value}")
                else:
                    print(f"   ❌ {field}: ПУСТО!")
            
            # 🔥 ПОКАЗЫВАЕМ НОВЫЕ ИЗВЛЕЧЕННЫЕ ПОЛЯ
            new_fields = ['dimensions', 'materials', 'period_dating', 'artist_maker', 'origin_country', 'lot_category', 'additional_images_count']
            print(f"🔥 ДОПОЛНИТЕЛЬНЫЕ ПОЛЯ:")
            for field in new_fields:
                value = lot_data.get(field, '')
                if value:
                    display_value = str(value)[:80] + "..." if len(str(value)) > 80 else str(value)
                    print(f"   🎯 {field}: {display_value}")
                else:
                    print(f"   ⚪ {field}: -")
            
            # Показываем дополнительные поля
            other_fields = ['auction_id', 'lot_system_id', 'auction_title', 'image_url', 'condition_report']
            for field in other_fields:
                value = lot_data.get(field, '')
                if value and len(str(value)) > 100:
                    print(f"   📋 {field}: {str(value)[:50]}...")
                elif value:
                    print(f"   📋 {field}: {value}")
            
            return lot_data
            
        except Exception as e:
            print(f"❌ Ошибка парсинга лота: {e}")
            return None
    
    def save_lot_data(self, lot_data):
        """Сохранение данных лота в CSV"""
        with open(self.db_file, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            row = [
                lot_data.get('timestamp', ''),
                lot_data.get('auction_id', ''),
                lot_data.get('auction_title', ''),
                lot_data.get('auction_date', ''),
                lot_data.get('lot_system_id', ''),
                lot_data.get('lot_number', ''),
                lot_data.get('lot_title', ''),
                lot_data.get('lot_description', ''),
                lot_data.get('url', ''),
                lot_data.get('image_url', ''),
                lot_data.get('image_high_res_url', ''),
                lot_data.get('additional_images_count', ''),
                lot_data.get('additional_images_urls', ''),
                lot_data.get('lot_estimate', ''),
                lot_data.get('lot_sold_price', ''),
                lot_data.get('lot_status', ''),
                lot_data.get('buyer_premium', ''),
                lot_data.get('condition_report', ''),
                lot_data.get('dimensions', ''),
                lot_data.get('materials', ''),
                lot_data.get('period_dating', ''),
                lot_data.get('artist_maker', ''),
                lot_data.get('origin_country', ''),
                lot_data.get('lot_category', ''),
                lot_data.get('full_lot_info', '')
            ]
            writer.writerow(row)
        
        print(f"💾 Данные сохранены в {self.db_file}")
    
    def download_image(self, image_url, lot_id, lot_number="", lot_description="", is_main=True, image_index=0):
        """Скачивание изображения лота в отдельную папку лота"""
        if not image_url:
            return None
        
        try:
            # 🔥 СОЗДАЕМ ОТДЕЛЬНУЮ ПАПКУ ДЛЯ ЛОТА
            clean_lot_desc = self.clean_filename(lot_description)
            lot_folder_name = f"Lot_{lot_number}_{clean_lot_desc}" if lot_number else f"Lot_ID_{lot_id}"
            lot_images_dir = self.images_dir / lot_folder_name
            lot_images_dir.mkdir(exist_ok=True)
            
            # 🔥 ОПТИМИЗИРОВАННАЯ ЗАГРУЗКА: короткий timeout + stream
            response = self.session.get(image_url, timeout=10, stream=True)
            response.raise_for_status()
            
            # Определяем расширение файла
            ext = '.jpg'
            if '.png' in image_url:
                ext = '.png'
            
            # Создаем имя файла
            if is_main:
                filename = f"lot_{lot_id}_main{ext}"
            else:
                filename = f"lot_{lot_id}_additional_{image_index}{ext}"
            
            filepath = lot_images_dir / filename
            
            # Загружаем по частям для лучшей производительности
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            print(f"🖼️ Изображение сохранено: {filepath}")
            return str(filepath)
            
        except Exception as e:
            print(f"❌ Ошибка скачивания изображения: {e}")
            return None
    
    def download_all_lot_images(self, lot_data):
        """🚀 ПАРАЛЛЕЛЬНАЯ загрузка всех изображений лота"""
        lot_id = lot_data.get('lot_system_id', '')
        lot_number = lot_data.get('lot_number', '')
        lot_description = lot_data.get('lot_description', '')
        
        # Собираем все URL для загрузки
        images_to_download = []
        
        # Основное изображение
        main_image_url = lot_data.get('image_url', '')
        if main_image_url:
            images_to_download.append({
                'url': main_image_url,
                'lot_id': lot_id,
                'lot_number': lot_number,
                'lot_description': lot_description,
                'is_main': True,
                'image_index': 0
            })
        
        # Дополнительные изображения
        additional_urls = lot_data.get('additional_images_urls', '')
        if additional_urls:
            urls_list = additional_urls.split(' | ')
            for i, url in enumerate(urls_list, 1):
                if url.strip():
                    images_to_download.append({
                        'url': url.strip(),
                        'lot_id': lot_id,
                        'lot_number': lot_number,
                        'lot_description': lot_description,
                        'is_main': False,
                        'image_index': i
                    })
        
        if not images_to_download:
            print(f"📷 Нет изображений для лота #{lot_number}")
            return []
        
        # 🚀 ПАРАЛЛЕЛЬНАЯ ЗАГРУЗКА
        print(f"📥 Загружаем {len(images_to_download)} изображений для лота #{lot_number}...")
        start_time = time.time()
        downloaded_images = []
        
        with ThreadPoolExecutor(max_workers=6) as executor:
            # Запускаем все загрузки параллельно
            future_to_image = {
                executor.submit(
                    self.download_image,
                    img_data['url'],
                    img_data['lot_id'],
                    img_data['lot_number'],
                    img_data['lot_description'],
                    img_data['is_main'],
                    img_data['image_index']
                ): img_data for img_data in images_to_download
            }
            
            # Собираем результаты по мере завершения
            for future in as_completed(future_to_image):
                try:
                    result = future.result()
                    if result:
                        downloaded_images.append(result)
                except Exception as e:
                    print(f"❌ Ошибка загрузки изображения: {e}")
        
        download_time = time.time() - start_time
        print(f"📷 Скачано {len(downloaded_images)}/{len(images_to_download)} изображений для лота #{lot_number} за {download_time:.1f}с")
        return downloaded_images
    
    def validate_lot_data(self, lot_data, lot_number):
        """Проверка заполненности полей лота"""
        # Определяем обязательные поля
        required_fields = {
            'auction_id': 'ID аукциона',
            'lot_number': 'Номер лота',
            'lot_title': 'Название лота',
            'lot_description': 'Описание лота',
            'lot_estimate': 'Оценочная стоимость',
            'buyer_premium': 'Комиссия покупателя',
            'image_url': 'URL изображения',
            'image_high_res_url': 'URL HD изображения',
            'condition_report': 'Отчет о состоянии'
        }
        
        # Дополнительные поля (извлекаются по возможности)
        additional_fields = {
            'dimensions': 'Размеры',
            'materials': 'Материалы',
            'period_dating': 'Период/датировка',
            'artist_maker': 'Художник/производитель',
            'origin_country': 'Страна происхождения',
            'lot_category': 'Категория лота',
            'additional_images_count': 'Количество доп. изображений'
        }
        
        # Поля которые могут быть пустыми (аукцион не состоялся)
        optional_fields = {
            'lot_sold_price': 'Цена продажи',
            'lot_status': 'Статус лота'
        }
        
        all_fields = {**required_fields, **additional_fields, **optional_fields}
        
        # Проверяем каждое поле
        missing_fields = []
        filled_fields = []
        additional_filled = []
        
        for field, description in all_fields.items():
            value = lot_data.get(field, '')
            
            # Инициализируем статистику поля если нужно
            if field not in self.field_stats:
                self.field_stats[field] = {'filled': 0, 'empty': 0}
            
            if value and str(value).strip():
                if field in required_fields:
                    filled_fields.append(f"✅ {description}")
                elif field in additional_fields:
                    additional_filled.append(f"🎯 {description}")
                else:
                    filled_fields.append(f"✅ {description}")
                self.field_stats[field]['filled'] += 1
            else:
                if field in required_fields:
                    missing_fields.append(f"❌ {description}")
                    self.field_stats[field]['empty'] += 1
                elif field in additional_fields:
                    self.field_stats[field]['empty'] += 1
                else:
                    missing_fields.append(f"⏳ {description} (ожидается после аукциона)")
                    self.field_stats[field]['empty'] += 1
        
        # Выводим результат проверки
        total_required = len(required_fields)
        total_filled = len([f for f in filled_fields if "✅" in f])
        
        print(f"   📋 Проверка полей лота #{lot_number}:")
        print(f"      ✅ Основные поля: {total_filled}/{total_required}")
        
        if additional_filled:
            print(f"      🎯 Дополнительные поля: {len(additional_filled)}/{len(additional_fields)}")
            for field in additional_filled[:3]:  # Показываем первые 3
                print(f"         {field}")
        
        if any("❌" in field for field in missing_fields):
            print(f"      ⚠️ Пустые обязательные поля:")
            for field in missing_fields:
                if "❌" in field:
                    print(f"         {field}")
        
        return len([f for f in missing_fields if "❌" in f]) == 0  # True если нет критических ошибок
    
    def print_field_statistics(self, total_lots):
        """Печать итоговой статистики по полям"""
        print(f"\n📊 СТАТИСТИКА ЗАПОЛНЕННОСТИ ПОЛЕЙ:")
        print("="*60)
        
        for field, stats in self.field_stats.items():
            filled = stats['filled']
            empty = stats['empty']
            percentage = (filled / total_lots * 100) if total_lots > 0 else 0
            
            status = "✅" if percentage >= 95 else "⚠️" if percentage >= 80 else "❌"
            
            print(f"{status} {field:<20} | {filled:>3}/{total_lots:<3} | {percentage:>5.1f}%")
        
        # Находим проблемные поля
        problem_fields = [field for field, stats in self.field_stats.items() 
                         if stats['filled'] / total_lots < 0.95 and field not in ['lot_sold_price', 'lot_status']]
        
        if problem_fields:
            print(f"\n⚠️ ПОЛЯ С НИЗКОЙ ЗАПОЛНЕННОСТЬЮ:")
            for field in problem_fields:
                stats = self.field_stats[field]
                percentage = stats['filled'] / total_lots * 100
                print(f"   - {field}: {percentage:.1f}% (проблема в {stats['empty']} лотах)")
        else:
            print(f"\n🎉 ВСЕ ОБЯЗАТЕЛЬНЫЕ ПОЛЯ ЗАПОЛНЯЮТСЯ КОРРЕКТНО!")
        
    def get_all_auction_lots(self, auction_url):
        """Получение всех лотов из аукциона"""
        print(f"🔍 СКАНИРОВАНИЕ АУКЦИОНА: {auction_url}")
        print("="*60)
        
        try:
            response = self.session.get(auction_url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            lots = []
            seen_lots = set()
            
            # Ищем все ссылки на лотов
            lot_links = soup.find_all('a', href=re.compile(r'/auction/lot/'))
            
            print(f"🔗 Найдено потенциальных ссылок на лотов: {len(lot_links)}")
            
            for link in lot_links:
                try:
                    lot_url = link.get('href')
                    if not lot_url.startswith('http'):
                        lot_url = 'https://auctions.tennants.co.uk' + lot_url
                    
                    # Извлекаем ID лота
                    lot_match = re.search(r'lot=(\d+)', lot_url)
                    if not lot_match:
                        continue
                    
                    lot_id = lot_match.group(1)
                    
                    # Пропускаем дубликаты
                    if lot_id in seen_lots:
                        continue
                    seen_lots.add(lot_id)
                    
                    # Получаем текст лота для предварительной информации
                    lot_text = link.get_text(strip=True)
                    
                    lot_info = {
                        'id': lot_id,
                        'url': lot_url,
                        'preview_text': lot_text
                    }
                    
                    lots.append(lot_info)
                    
                except Exception as e:
                    continue
            
            print(f"✅ Найдено уникальных лотов: {len(lots)}")
            return lots
            
        except Exception as e:
            print(f"❌ Ошибка при сканировании аукциона: {e}")
            return []
    
    def parse_auction(self, auction_url, max_lots=None, delay=2):
        """Парсинг полного аукциона"""
        print(f"🚀 НАЧИНАЕМ ПАРСИНГ ПОЛНОГО АУКЦИОНА")
        print("="*60)
        
        # Получаем все лоты
        lots = self.get_all_auction_lots(auction_url)
        
        if not lots:
            print("❌ Не удалось найти лоты в аукционе")
            return False
        
        total_lots = len(lots)
        if max_lots:
            lots = lots[:max_lots]
            print(f"🎯 Ограничиваем парсинг до {max_lots} лотов из {total_lots}")
        
        print(f"\n📦 НАЧИНАЕМ ПАРСИНГ {len(lots)} ЛОТОВ")
        print("="*50)
        
        success_count = 0
        error_count = 0
        
        for i, lot in enumerate(lots, 1):
            try:
                print(f"\n[{i}/{len(lots)}] Парсим лот ID: {lot['id']}")
                print(f"URL: {lot['url']}")
                
                # Парсим лот
                lot_data = self.parse_lot_page(lot['url'])
                
                if lot_data:
                    # Сохраняем данные
                    self.save_lot_data(lot_data)
                    
                    # Скачиваем изображение
                    self.download_all_lot_images(lot_data)
                    
                    success_count += 1
                    lot_number = lot_data.get('lot_number', lot['id'])
                    print(f"✅ Лот #{lot_number} успешно обработан")
                    
                    # Показываем краткую информацию
                    desc = lot_data.get('lot_description', '')
                    if len(desc) > 100:
                        desc = desc[:100] + "..."
                    print(f"   Описание: {desc}")
                    print(f"   Оценка: {lot_data.get('lot_estimate', 'N/A')}")
                    
                    # 🔍 ПРОВЕРЯЕМ ЗАПОЛНЕННОСТЬ ПОЛЕЙ
                    is_valid = self.validate_lot_data(lot_data, lot_number)
                    if not is_valid:
                        print(f"   ⚠️ Лот #{lot_number} имеет незаполненные обязательные поля!")
                    
                else:
                    error_count += 1
                    print(f"❌ Ошибка парсинга лота {lot['id']}")
                
                # Прогресс
                if i % 10 == 0:
                    print(f"\n📊 ПРОГРЕСС: {i}/{len(lots)} ({i/len(lots)*100:.1f}%)")
                    print(f"   Успешно: {success_count}")
                    print(f"   Ошибок: {error_count}")
                
                # Задержка между запросами
                if i < len(lots):
                    time.sleep(delay)
                    
            except KeyboardInterrupt:
                print(f"\n⚠️ ПРЕРЫВАНИЕ ПОЛЬЗОВАТЕЛЕМ")
                print(f"Обработано: {success_count}/{len(lots)} лотов")
                break
                
            except Exception as e:
                error_count += 1
                print(f"❌ Критическая ошибка для лота {lot['id']}: {e}")
                continue
        
        # Финальная статистика
        print(f"\n🎉 ПАРСИНГ ЗАВЕРШЕН!")
        print("="*40)
        print(f"Всего лотов в аукционе: {total_lots}")
        print(f"Обработано: {success_count + error_count}/{len(lots)}")
        print(f"Успешно: {success_count}")
        print(f"Ошибок: {error_count}")
        print(f"Успешность: {success_count/len(lots)*100:.1f}%")
        print(f"📁 Данные сохранены в: {self.working_dir}")
        
        # 📊 Показываем статистику заполненности полей
        if success_count > 0:
            self.print_field_statistics(success_count)
        
        return success_count > 0

    def extract_dimensions(self, description_text):
        """Извлечение размеров из текста описания"""
        dimensions = []
        
        # Различные паттерны для размеров
        patterns = [
            r'(\d+(?:\.\d+)?)\s*cm\s+(?:high|height|h)\b',
            r'(\d+(?:\.\d+)?)\s*cm\s+(?:wide|width|w)\b', 
            r'(\d+(?:\.\d+)?)\s*cm\s+(?:deep|depth|d)\b',
            r'(\d+(?:\.\d+)?)\s*cm\s+(?:long|length|l)\b',
            r'(\d+(?:\.\d+)?)\s*cm\s+(?:diameter|diam)\b',
            r'(\d+(?:\.\d+)?)\s*x\s*(\d+(?:\.\d+)?)\s*(?:x\s*(\d+(?:\.\d+)?))?\s*cm',
            r'(\d+(?:\.\d+)?)\s*inches?\s+(?:high|wide|deep|long)',
            r'(\d+(?:\.\d+)?)\s*"\s+(?:high|wide|deep|long)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, description_text, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    # Для сложных размеров (например, 10x20x30 cm)
                    dim_str = ' x '.join([d for d in match if d])
                    dimensions.append(dim_str + ' cm')
                else:
                    dimensions.append(f"{match} cm")
        
        return '; '.join(dimensions) if dimensions else ""
    
    def extract_materials(self, description_text):
        """Извлечение материалов из текста описания"""
        # Распространенные материалы в аукционах
        materials = [
            'brass', 'bronze', 'copper', 'silver', 'gold', 'platinum',
            'wood', 'oak', 'mahogany', 'walnut', 'pine', 'teak', 'ebony',
            'glass', 'crystal', 'ceramic', 'porcelain', 'earthenware', 'stoneware', 'jasper',
            'marble', 'stone', 'granite', 'slate',
            'fabric', 'silk', 'cotton', 'wool', 'linen', 'velvet', 'leather',
            'plastic', 'resin', 'bakelite',
            'ivory', 'bone', 'mother of pearl',
            'enamel', 'lacquer', 'gilt', 'gilded'
        ]
        
        found_materials = []
        text_lower = description_text.lower()
        
        for material in materials:
            if material in text_lower:
                found_materials.append(material.title())
        
        return ', '.join(found_materials) if found_materials else ""
    
    def extract_period_dating(self, description_text):
        """Извлечение периода и датировки"""
        periods = []
        
        # Паттерны для веков
        century_patterns = [
            r'(\d+)(?:st|nd|rd|th)\s+century',
            r'(\d+)(?:st|nd|rd|th)\s+c\.',
        ]
        
        # Паттерны для конкретных дат
        date_patterns = [
            r'circa\s+(\d{4})',
            r'c\.\s*(\d{4})',
            r'\b(\d{4})\b',
            r'(\d{4})\s*-\s*(\d{4})',
        ]
        
        for pattern in century_patterns:
            matches = re.findall(pattern, description_text, re.IGNORECASE)
            for match in matches:
                periods.append(f"{match} century")
        
        for pattern in date_patterns:
            matches = re.findall(pattern, description_text, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    periods.append(f"{match[0]}-{match[1]}")
                else:
                    periods.append(match)
        
        return ', '.join(periods) if periods else ""
    
    def extract_artist_maker(self, description_text):
        """Извлечение имен художников и производителей"""
        makers = []
        
        # Паттерны для производителей/художников
        patterns = [
            r'by\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*),\s+(?:Paris|London|Berlin|Vienna)',
            r'(?:signed|attributed to|after)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, description_text)
            makers.extend(matches)
        
        # Удаляем дубликаты
        unique_makers = list(dict.fromkeys(makers))
        return ', '.join(unique_makers) if unique_makers else ""
    
    def extract_origin_country(self, description_text):
        """Извлечение страны происхождения"""
        countries = [
            'French', 'English', 'British', 'German', 'Italian', 'Spanish', 
            'Chinese', 'Japanese', 'American', 'Austrian', 'Dutch', 'Belgian',
            'Russian', 'Scandinavian', 'European'
        ]
        
        text_words = description_text.split()
        found_countries = []
        
        for country in countries:
            if country in text_words:
                found_countries.append(country)
        
        return ', '.join(found_countries) if found_countries else ""
    
    def extract_additional_images(self, soup):
        """Извлечение всех дополнительных изображений лота"""
        additional_images = []
        
        # Ищем в condition report
        condition_tab = soup.find('div', {'id': 'condition'})
        if condition_tab:
            condition_images = condition_tab.find_all('img')
            for img in condition_images:
                src = img.get('src', '')
                if src and 'stock' in src:
                    # Получаем высокое разрешение
                    high_res_url = src.replace('-small', '').replace('-medium', '')
                    if high_res_url.startswith('//'):
                        high_res_url = 'https:' + high_res_url
                    elif high_res_url.startswith('/'):
                        high_res_url = 'https://tennants.blob.core.windows.net' + high_res_url
                    additional_images.append(high_res_url)
        
        return additional_images
    
    def extract_lot_category(self, soup):
        """Определение категории лота"""
        # Ищем в h1 с классом lot-title
        h1_tag = soup.find('h1', {'class': re.compile(r'lot-title.*cat-\d+')})
        if h1_tag:
            class_attr = h1_tag.get('class', [])
            for cls in class_attr:
                if cls.startswith('cat-'):
                    # Можно создать словарь категорий если нужно
                    return cls
        
        # Альтернативно ищем в option elements
        options = soup.find_all('option')
        for option in options:
            text = option.get_text(strip=True)
            if any(keyword in text.lower() for keyword in ['ceramics', 'glass', 'furniture', 'art', 'jewelry']):
                return text
        
        return ""

def main():
    # URL аукциона, найденного ранее
    auction_url = "https://auctions.tennants.co.uk/auction/details/180725-antiques--interiors-to-include-designer-fashion-and-affordable-modern--contemporary-art/?au=14251"
    
    print("🎯 ПАРСИНГ АУКЦИОНА: Antiques & Interiors (18 июля 2025)")
    print("="*70)
    
    # 🔥 ПОЛУЧАЕМ ИНФОРМАЦИЮ ОБ АУКЦИОНЕ ДЛЯ НАЗВАНИЯ ПАПКИ
    print("📋 Получение информации об аукционе...")
    
    # Быстрый запрос для получения названия аукциона
    try:
        import requests
        from bs4 import BeautifulSoup
        
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        
        response = session.get(auction_url, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Извлекаем название аукциона
        auction_title = ""
        title_tag = soup.find('title')
        if title_tag:
            full_title = title_tag.get_text(strip=True)
            # Извлекаем название до " - "
            auction_title = full_title.split(' - ')[0] if ' - ' in full_title else full_title
        
        if not auction_title:
            auction_title = "Antiques & Interiors"
        
        # Извлекаем дату аукциона
        auction_date = "2025-07-18"  # По умолчанию
        date_element = soup.find('p', {'class': 'date-title'})
        if date_element:
            date_text = date_element.get_text(strip=True)
            # Ищем дату в формате "18th Jul, 2025"
            date_match = re.search(r'(\d+)\w+\s+(\w+),?\s+(\d{4})', date_text)
            if date_match:
                day, month, year = date_match.groups()
                # Преобразуем месяц
                month_map = {
                    'Jan': '01', 'Feb': '02', 'Mar': '03', 'Apr': '04',
                    'May': '05', 'Jun': '06', 'Jul': '07', 'Aug': '08', 
                    'Sep': '09', 'Oct': '10', 'Nov': '11', 'Dec': '12'
                }
                month_num = month_map.get(month, '07')
                auction_date = f"{year}-{month_num}-{day.zfill(2)}"
        
        print(f"✅ Название аукциона: {auction_title}")
        print(f"✅ Дата аукциона: {auction_date}")
        
    except Exception as e:
        print(f"⚠️ Ошибка получения информации об аукционе: {e}")
        auction_title = "Antiques_Interiors"
        auction_date = "2025-07-18"
    
    # 🔥 СОЗДАЕМ ПАРСЕР С ИНФОРМАЦИЕЙ ОБ АУКЦИОНЕ
    parser = FullAuctionParser(auction_title=auction_title, auction_date=auction_date)
    
    # 🔍 ПОДСЧИТЫВАЕМ КОЛИЧЕСТВО ЛОТОВ В АУКЦИОНЕ
    print("\n📊 Подсчет лотов в аукционе...")
    try:
        lots = parser.get_all_auction_lots(auction_url)
        total_lots_count = len(lots) if lots else 0
        
        if total_lots_count > 0:
            print(f"✅ Всего лотов в аукционе: {total_lots_count}")
        else:
            print("❌ Не удалось подсчитать лоты в аукционе")
            return
    except Exception as e:
        print(f"⚠️ Ошибка подсчета лотов: {e}")
        total_lots_count = "неизвестно"

    # Спрашиваем пользователя о количестве лотов
    try:
        user_input = input(f"\n🤔 Сколько лотов парсить из {total_lots_count}? (Enter = все лоты, число = ограничить): ").strip()
        max_lots = None
        if user_input and user_input.isdigit():
            max_lots = int(user_input)
            print(f"✅ Будем парсить максимум {max_lots} лотов из {total_lots_count}")
        else:
            print(f"✅ Будем парсить ВСЕ {total_lots_count} лотов аукциона")
    except KeyboardInterrupt:
        print("\n❌ Отменено пользователем")
        return
    
    # Запускаем парсинг
    success = parser.parse_auction(auction_url, max_lots=max_lots)
    
    if success:
        print(f"\n🎉 ПАРСИНГ УСПЕШНО ЗАВЕРШЕН!")
        print(f"📊 Результаты сохранены в папке: {parser.working_dir}")
        print(f"💾 База данных: {parser.db_file}")
        print(f"🖼️ Изображения организованы по папкам лотов в: {parser.images_dir}")
    else:
        print(f"\n❌ ПАРСИНГ НЕ УДАЛСЯ")

if __name__ == "__main__":
    main() 