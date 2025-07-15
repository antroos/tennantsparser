#!/usr/bin/env python3
"""
Скрипт для поиска ближайших аукционов на Tennants
"""

import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
import re

class TennantsAuctionFinder:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        })
        
    def find_upcoming_auctions(self):
        """Поиск предстоящих аукционов"""
        print("🔍 Ищем ближайшие аукционы на Tennants...")
        
        # Пробуем разные URL
        possible_urls = [
            "https://auctions.tennants.co.uk/",
            "https://auctions.tennants.co.uk/forthcoming-auctions/",
            "https://auctions.tennants.co.uk/live-auctions/",
            "https://auctions.tennants.co.uk/current-auctions/",
            "https://www.tennants.co.uk/auctions/",
            "https://www.tennants.co.uk/"
        ]
        
        for url in possible_urls:
            try:
                print(f"🔍 Пробуем URL: {url}")
                response = self.session.get(url, timeout=30)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.content, 'html.parser')
                
                auctions = []
                
                # Ищем различные типы ссылок на аукционы
                auction_links = []
                
                # Вариант 1: Прямые ссылки на аукционы
                auction_links.extend(soup.find_all('a', href=re.compile(r'/auction/')))
                
                # Вариант 2: Ссылки содержащие "auction"
                auction_links.extend(soup.find_all('a', href=re.compile(r'auction', re.IGNORECASE)))
                
                print(f"🔗 Найдено ссылок на аукционы: {len(auction_links)}")
                
                seen_urls = set()
                
                for link in auction_links:
                    try:
                        auction_url = link.get('href')
                        if not auction_url:
                            continue
                            
                        # Делаем абсолютный URL
                        if auction_url.startswith('/'):
                            base_url = url.rstrip('/')
                            auction_url = base_url + auction_url
                        elif not auction_url.startswith('http'):
                            continue
                        
                        # Пропускаем дубликаты
                        if auction_url in seen_urls:
                            continue
                        seen_urls.add(auction_url)
                        
                        # Проверяем что это действительно ссылка на аукцион
                        if '/auction/' not in auction_url.lower():
                            continue
                        
                        # Получаем название
                        title = link.get_text(strip=True)
                        if not title or len(title) < 3:
                            continue
                        
                        # Ищем дату в тексте рядом с ссылкой
                        parent = link.parent
                        date_text = ""
                        if parent:
                            parent_text = parent.get_text()
                            date_match = re.search(r'\d{1,2}[^\w]+\w+[^\w]+20\d{2}', parent_text)
                            if date_match:
                                date_text = date_match.group()
                        
                        # Извлекаем ID аукциона
                        auction_id = ""
                        id_match = re.search(r'/auction/(\d+)', auction_url)
                        if id_match:
                            auction_id = id_match.group(1)
                        
                        auction_info = {
                            'id': auction_id,
                            'title': title,
                            'date': date_text,
                            'url': auction_url
                        }
                        
                        auctions.append(auction_info)
                        
                    except Exception as e:
                        continue
                
                if auctions:
                    print(f"✅ Найдено аукционов на {url}: {len(auctions)}")
                    return auctions
                else:
                    print(f"❌ Аукционы не найдены на {url}")
                    
            except Exception as e:
                print(f"❌ Ошибка для {url}: {e}")
                continue
        
        print("❌ Не удалось найти аукционы ни на одном из URLs")
        return []
    
    def get_auction_lots(self, auction_url, limit=5):
        """Получение лотов из аукциона"""
        print(f"\n📦 Получаем лоты из аукциона: {auction_url}")
        
        try:
            response = self.session.get(auction_url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            lots = []
            
            # Ищем ссылки на лоты
            lot_links = soup.find_all('a', href=re.compile(r'/auction/lot/'))
            
            print(f"🔗 Найдено ссылок на лоты: {len(lot_links)}")
            
            for link in lot_links[:limit]:
                lot_url = link.get('href')
                if not lot_url.startswith('http'):
                    lot_url = 'https://auctions.tennants.co.uk' + lot_url
                
                # Извлекаем номер лота
                lot_match = re.search(r'lot=(\d+)', lot_url)
                lot_id = lot_match.group(1) if lot_match else ""
                
                # Получаем текст лота
                lot_text = link.get_text(strip=True)
                
                lot_info = {
                    'id': lot_id,
                    'text': lot_text,
                    'url': lot_url
                }
                
                lots.append(lot_info)
            
            return lots
            
        except Exception as e:
            print(f"❌ Ошибка при получении лотов: {e}")
            return []

def main():
    finder = TennantsAuctionFinder()
    
    # Находим аукционы
    auctions = finder.find_upcoming_auctions()
    
    if not auctions:
        print("❌ Не удалось найти аукционы")
        return
    
    print("\n🎯 НАЙДЕННЫЕ АУКЦИОНЫ:")
    print("="*60)
    
    for i, auction in enumerate(auctions[:10], 1):
        print(f"{i}. {auction['title']}")
        print(f"   ID: {auction['id']}")
        print(f"   Дата: {auction['date']}")
        print(f"   URL: {auction['url']}")
        print()
    
    # Берем первый аукцион для тестирования
    if auctions:
        test_auction = auctions[0]
        print(f"🎯 ТЕСТИРУЕМ НА АУКЦИОНЕ: {test_auction['title']}")
        print("="*60)
        
        # Получаем лоты
        lots = finder.get_auction_lots(test_auction['url'])
        
        if lots:
            print(f"\n📦 НАЙДЕННЫЕ ЛОТЫ (первые 5):")
            print("="*40)
            
            for i, lot in enumerate(lots, 1):
                print(f"{i}. Лот ID: {lot['id']}")
                print(f"   Текст: {lot['text'][:100]}...")
                print(f"   URL: {lot['url']}")
                print()
            
            # Возвращаем первый лот для тестирования
            if lots:
                print(f"✅ РЕКОМЕНДУЕМЫЙ ЛОТ ДЛЯ ТЕСТИРОВАНИЯ:")
                print(f"URL: {lots[0]['url']}")
                return lots[0]['url']
        else:
            print("❌ Не удалось найти лоты в аукционе")
    
    return None

if __name__ == "__main__":
    main() 