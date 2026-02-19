"""
Конвертер Excel-файла с географическими данными в фикстуры Django.
Поддерживает три связанных листа: district, region, city.

Использование:
    python excel_to_fixtures.py russia.xlsx --output fixtures/
    python excel_to_fixtures.py data.xlsx --pretty --encoding cp1251
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from collections import defaultdict

# Проверка наличия зависимостей
try:
    import pandas as pd
    from pandas import ExcelFile
except ImportError:
    print("❌ Ошибка: не установлен pandas. Установите: pip install pandas openpyxl")
    sys.exit(1)


class ExcelToFixtures:
    """Конвертер Excel в Django фикстуры"""
    
    def __init__(self, excel_path, output_dir='fixtures', pretty=False, encoding='utf-8'):
        self.excel_path = Path(excel_path)
        self.output_dir = Path(output_dir)
        self.pretty = pretty
        self.encoding = encoding
        
        # Статистика
        self.stats = defaultdict(int)
        
    def run(self):
        """Запуск конвертации"""
        print(f"📂 Чтение файла: {self.excel_path}")
        
        if not self.excel_path.exists():
            print(f"❌ Файл не найден: {self.excel_path}")
            return False
        
        # Создаем выходную директорию
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            # Читаем Excel-файл
            excel_file = pd.ExcelFile(self.excel_path)
            
            # Проверяем наличие всех листов
            required_sheets = ['district', 'region', 'city']
            for sheet in required_sheets:
                if sheet not in excel_file.sheet_names:
                    print(f"❌ Лист '{sheet}' не найден в файле")
                    return False
            
            # Парсим в правильном порядке
            districts = self.parse_district(excel_file)
            if not districts:
                return False
                
            regions = self.parse_region(excel_file, districts)
            if not regions:
                return False
                
            cities = self.parse_city(excel_file, regions)
            
            # Сохраняем фикстуры
            self.save_fixture('district.json', districts)
            self.save_fixture('region.json', regions)
            self.save_fixture('city.json', cities)
            
            # Показываем статистику
            self.print_statistics()
            
            return True
            
        except Exception as e:
            print(f"❌ Ошибка при обработке: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def parse_district(self, excel_file):
        """Парсинг федеральных округов"""
        print("\n🔍 Парсинг федеральных округов...")
        
        df = pd.read_excel(excel_file, 'district')
        districts = []
        
        # Проверяем структуру
        required_cols = ['district_id', 'district', 'district_short']
        for col in required_cols:
            if col not in df.columns:
                print(f"❌ В листе 'district' нет колонки '{col}'")
                return None
        
        # Обрабатываем строки
        for _, row in df.iterrows():
            if pd.isna(row['district_id']) or pd.isna(row['district']):
                continue
                
            district_id = int(row['district_id'])
            district_name = str(row['district']).strip()
            district_short = str(row['district_short']).strip() if pd.notna(row['district_short']) else ''
            
            district = {
                "model": "core.district",
                "pk": district_id,
                "fields": {
                    "district": district_name,
                    "district_short": district_short,
                    "slug": self.slugify(district_name),
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat()
                }
            }
            districts.append(district)
            self.stats['districts'] += 1
        
        print(f"  ✅ Найдено: {len(districts)} округов")
        return districts
    
    def parse_region(self, excel_file, districts):
        """Парсинг регионов"""
        print("🔍 Парсинг регионов...")
        
        df = pd.read_excel(excel_file, 'region')
        regions = []
        
        # Создаем множество существующих district_id
        existing_districts = {d['pk'] for d in districts}
        
        # Проверяем структуру
        required_cols = ['region_id', 'title', 'district_id']
        for col in required_cols:
            if col not in df.columns:
                print(f"❌ В листе 'region' нет колонки '{col}'")
                return None
        
        # Обрабатываем строки
        skipped = 0
        for _, row in df.iterrows():
            if pd.isna(row['region_id']) or pd.isna(row['title']):
                continue
                
            region_id = int(row['region_id'])
            region_title = str(row['title']).strip()
            district_id = int(row['district_id']) if pd.notna(row['district_id']) else None
            
            # Проверяем связь с округом
            if district_id not in existing_districts:
                print(f"  ⚠️ Пропущен регион '{region_title}': нет округа с ID {district_id}")
                skipped += 1
                self.stats['regions_skipped'] += 1
                continue
            
            region = {
                "model": "core.region",
                "pk": region_id,
                "fields": {
                    "title": region_title,
                    "district": district_id,
                    "slug": self.slugify(region_title),
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat()
                }
            }
            regions.append(region)
            self.stats['regions'] += 1
        
        print(f"  ✅ Найдено: {len(regions)} регионов")
        if skipped:
            print(f"  ⚠️ Пропущено: {skipped} (нет связи с округом)")
        return regions
    
    def parse_city(self, excel_file, regions):
        """Парсинг городов"""
        print("🔍 Парсинг городов...")
        
        df = pd.read_excel(excel_file, 'city')
        cities = []
        
        # Создаем множество существующих region_id
        existing_regions = {r['pk'] for r in regions}
        
        # Проверяем структуру
        required_cols = ['city_id', 'city', 'region']
        for col in required_cols:
            if col not in df.columns:
                print(f"❌ В листе 'city' нет колонки '{col}'")
                return None
        
        # Обрабатываем строки
        skipped_no_region = 0
        skipped_no_coords = 0
        
        for _, row in df.iterrows():
            if pd.isna(row['city_id']) or pd.isna(row['city']):
                continue
                
            city_id = int(row['city_id'])
            city_name = str(row['city']).strip()
            region_id = int(row['region']) if pd.notna(row['region']) else None
            
            # Проверяем связь с регионом
            if region_id not in existing_regions:
                print(f"  ⚠️ Пропущен город '{city_name}': нет региона с ID {region_id}")
                skipped_no_region += 1
                self.stats['cities_skipped_region'] += 1
                continue
            
            # Обрабатываем координаты
            latitude = None
            longitude = None
            
            if 'latitude' in df.columns and pd.notna(row.get('latitude')):
                try:
                    latitude = float(row['latitude'])
                except (ValueError, TypeError):
                    pass
                    
            if 'longitude' in df.columns and pd.notna(row.get('longitude')):
                try:
                    longitude = float(row['longitude'])
                except (ValueError, TypeError):
                    pass
            
            if latitude is None or longitude is None:
                skipped_no_coords += 1
                self.stats['cities_no_coords'] += 1
            
            # Генерируем slug
            slug = self.slugify(f"{city_name}-{region_id}")
            
            city = {
                "model": "core.city",
                "pk": city_id,
                "fields": {
                    "city": city_name,
                    "region": region_id,
                    "latitude": latitude,
                    "longitude": longitude,
                    "slug": slug,
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat()
                }
            }
            cities.append(city)
            self.stats['cities'] += 1
        
        print(f"  ✅ Найдено: {len(cities)} городов")
        if skipped_no_region:
            print(f"  ⚠️ Пропущено (нет региона): {skipped_no_region}")
        if skipped_no_coords:
            print(f"  ℹ️ Без координат: {skipped_no_coords}")
        return cities
    
    def save_fixture(self, filename, data):
        """Сохранение фикстуры в файл"""
        filepath = self.output_dir / filename
        
        indent = 2 if self.pretty else None
        separators = (',', ': ') if self.pretty else (',', ':')
        
        with open(filepath, 'w', encoding=self.encoding) as f:
            json.dump(data, f, ensure_ascii=False, indent=indent, separators=separators)
        
        print(f"  💾 Сохранено: {filename} ({len(data)} записей)")
    
    def slugify(self, text):
        """Простой slugify для русского текста"""
        # Транслитерация (базовая)
        translit = {
            'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'e',
            'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
            'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
            'ф': 'f', 'х': 'kh', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'sch',
            'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya',
            
            'А': 'A', 'Б': 'B', 'В': 'V', 'Г': 'G', 'Д': 'D', 'Е': 'E', 'Ё': 'E',
            'Ж': 'Zh', 'З': 'Z', 'И': 'I', 'Й': 'Y', 'К': 'K', 'Л': 'L', 'М': 'M',
            'Н': 'N', 'О': 'O', 'П': 'P', 'Р': 'R', 'С': 'S', 'Т': 'T', 'У': 'U',
            'Ф': 'F', 'Х': 'Kh', 'Ц': 'Ts', 'Ч': 'Ch', 'Ш': 'Sh', 'Щ': 'Sch',
            'Ъ': '', 'Ы': 'Y', 'Ь': '', 'Э': 'E', 'Ю': 'Yu', 'Я': 'Ya'
        }
        
        result = []
        for char in text.lower():
            if char.isalnum():
                result.append(translit.get(char, char))
            elif char in (' ', '-', '_'):
                result.append('-')
        
        # Убираем повторяющиеся дефисы
        slug = ''.join(result)
        while '--' in slug:
            slug = slug.replace('--', '-')
        
        return slug.strip('-')
    
    def print_statistics(self):
        """Вывод статистики"""
        print("\n" + "="*50)
        print("📊 СТАТИСТИКА КОНВЕРТАЦИИ")
        print("="*50)
        print(f"Федеральные округа: {self.stats['districts']}")
        print(f"Регионы:           {self.stats['regions']}")
        if self.stats['regions_skipped']:
            print(f"  ⚠️ Пропущено регионов: {self.stats['regions_skipped']}")
        print(f"Города:            {self.stats['cities']}")
        if self.stats['cities_skipped_region']:
            print(f"  ⚠️ Пропущено городов: {self.stats['cities_skipped_region']}")
        if self.stats['cities_no_coords']:
            print(f"  ℹ️ Городов без координат: {self.stats['cities_no_coords']}")
        print("="*50)
        print(f"✅ Фикстуры сохранены в: {self.output_dir}/")
        print("="*50)


def main():
    """Точка входа"""
    parser = argparse.ArgumentParser(
        description='Конвертер Excel в Django фикстуры для географических данных',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  %(prog)s russia.xlsx
  %(prog)s data.xlsx --output fixtures --pretty
  %(prog)s russia.xlsx --encoding cp1251 --pretty
        """
    )
    
    parser.add_argument(
        'excel_file',
        help='Путь к Excel-файлу'
    )
    
    parser.add_argument(
        '-o', '--output',
        default='fixtures',
        help='Директория для сохранения фикстур (по умолчанию: fixtures)'
    )
    
    parser.add_argument(
        '-p', '--pretty',
        action='store_true',
        help='Форматировать JSON с отступами для читаемости'
    )
    
    parser.add_argument(
        '-e', '--encoding',
        default='utf-8',
        help='Кодировка для выходных файлов (по умолчанию: utf-8)'
    )
    
    args = parser.parse_args()
    
    # Создаем конвертер и запускаем
    converter = ExcelToFixtures(
        excel_path=args.excel_file,
        output_dir=args.output,
        pretty=args.pretty,
        encoding=args.encoding
    )
    
    success = converter.run()
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()