"""
Конвертер Excel-файла с данными организаций ОПК в фикстуры Django.
Поддерживает 6 связанных листов: industry, activity_type, ceo_position, person, organizations.

Использование:
    python excel_to_org_fixtures.py organizations.xlsx --output fixtures/
    python excel_to_org_fixtures.py data.xlsx --pretty --encoding cp1251
"""

import argparse
import json
import os
import sys
import re
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


class ExcelToOrgFixtures:
    """Конвертер Excel в Django фикстуры для организаций"""
    
    # Маппинг колонок из Excel в поля модели
    COLUMN_MAPPING = {
        'organization_id': 'organization_id',
        'okpo': 'okpo',
        'ogrn': 'ogrn',
        'inn': 'inn',
        'kpp': 'kpp',
        'okato': 'okato',
        'name': 'name',
        'full_name': 'full_name',
        'short_name': 'short_name',
        'city': 'city',
        'address': 'address',
        'url': 'url',
        'holding_1': 'holding_1',
        'holding_2': 'holding_2',
        'holding_3': 'holding_3',
        'industry': 'industry',
        'activity_type': 'activity_type',
        'activity_description': 'activity_description',
        'register_opk': 'register_opk',
        'e_mail': 'email',
        'ceo_position': 'ceo_position',
        'ceo': 'ceo',
        'phone': 'phone',
        'strategic': 'strategic',
        'gisp_catalogue_id': 'gisp_catalogue_id'
    }
    
    def __init__(self, excel_path, output_dir='fixtures', pretty=False, encoding='utf-8'):
        self.excel_path = Path(excel_path)
        self.output_dir = Path(output_dir)
        self.pretty = pretty
        self.encoding = encoding
        
        # Хранилища для данных
        self.data = {
            'industry': [],
            'activity_type': [],
            'ceo_position': [],
            'person': [],
            'organization': []
        }
        
        # Множества для проверки связей
        self.industry_ids = set()
        self.activity_type_ids = set()
        self.ceo_position_ids = set()
        self.person_ids = set()
        self.city_ids = set()  # Будут загружены отдельно из russia.xlsx
        
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
            required_sheets = ['industry', 'activity_type', 'ceo_position', 'person', 'organizations']
            for sheet in required_sheets:
                if sheet not in excel_file.sheet_names:
                    print(f"❌ Лист '{sheet}' не найден в файле")
                    return False
            
            # Парсим в правильном порядке (сначала справочники)
            print("\n🔍 Парсинг справочников...")
            self.parse_industry(excel_file)
            self.parse_activity_type(excel_file)
            self.parse_ceo_position(excel_file)
            self.parse_person(excel_file)
            
            print("\n🔍 Парсинг организаций...")
            self.parse_organizations(excel_file)
            
            # Сохраняем фикстуры
            self.save_fixtures()
            
            # Показываем статистику
            self.print_statistics()
            
            return True
            
        except Exception as e:
            print(f"❌ Ошибка при обработке: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def parse_industry(self, excel_file):
        """Парсинг отраслей"""
        print("  📋 Отрасли промышленности...")
        
        df = pd.read_excel(excel_file, 'industry')
        
        # Проверяем структуру
        if 'industry_id' not in df.columns or 'industry' not in df.columns:
            print("  ❌ В листе 'industry' нет нужных колонок")
            return
        
        # Обрабатываем строки
        for _, row in df.iterrows():
            if pd.isna(row['industry_id']) or pd.isna(row['industry']):
                continue
            
            industry_id = int(row['industry_id'])
            industry_name = str(row['industry']).strip()
            
            industry = {
                "model": "core.industry",
                "pk": industry_id,
                "fields": {
                    "industry": industry_name,
                    "slug": self.slugify(industry_name),
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat()
                }
            }
            
            self.data['industry'].append(industry)
            self.industry_ids.add(industry_id)
            self.stats['industry'] += 1
        
        print(f"    ✅ Найдено: {len(self.data['industry'])} отраслей")
    
    def parse_activity_type(self, excel_file):
        """Парсинг типов деятельности"""
        print("  📋 Типы деятельности...")
        
        df = pd.read_excel(excel_file, 'activity_type')
        
        # Проверяем структуру
        if 'activity_type_id' not in df.columns or 'activity_type' not in df.columns:
            print("  ❌ В листе 'activity_type' нет нужных колонок")
            return
        
        # Обрабатываем строки
        for _, row in df.iterrows():
            if pd.isna(row['activity_type_id']) or pd.isna(row['activity_type']):
                continue
            
            activity_type_id = int(row['activity_type_id'])
            activity_type_name = str(row['activity_type']).strip()
            
            activity_type = {
                "model": "core.activitytype",
                "pk": activity_type_id,
                "fields": {
                    "activity_type": activity_type_name,
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat()
                }
            }
            
            self.data['activity_type'].append(activity_type)
            self.activity_type_ids.add(activity_type_id)
            self.stats['activity_type'] += 1
        
        print(f"    ✅ Найдено: {len(self.data['activity_type'])} типов деятельности")
    
    def parse_ceo_position(self, excel_file):
        """Парсинг должностей руководителей"""
        print("  📋 Должности руководителей...")
        
        df = pd.read_excel(excel_file, 'ceo_position')
        
        # Проверяем структуру
        if 'ceo_position_id' not in df.columns or 'ceo_position' not in df.columns:
            print("  ❌ В листе 'ceo_position' нет нужных колонок")
            return
        
        # Обрабатываем строки
        for _, row in df.iterrows():
            if pd.isna(row['ceo_position_id']) or pd.isna(row['ceo_position']):
                continue
            
            ceo_position_id = int(row['ceo_position_id'])
            ceo_position_name = str(row['ceo_position']).strip()
            
            ceo_position = {
                "model": "core.ceoposition",
                "pk": ceo_position_id,
                "fields": {
                    "ceo_position": ceo_position_name,
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat()
                }
            }
            
            self.data['ceo_position'].append(ceo_position)
            self.ceo_position_ids.add(ceo_position_id)
            self.stats['ceo_position'] += 1
        
        print(f"    ✅ Найдено: {len(self.data['ceo_position'])} должностей")
    
    def parse_person(self, excel_file):
        """Парсинг руководителей (физических лиц)"""
        print("  📋 Руководители...")
        
        df = pd.read_excel(excel_file, 'person')
        
        # Проверяем структуру
        required_cols = ['ceo_id', 'ceo', 'last_name', 'first_name', 'middle_name']
        for col in required_cols:
            if col not in df.columns:
                print(f"  ❌ В листе 'person' нет колонки '{col}'")
                return
        
        # Обрабатываем строки
        skipped = 0
        for _, row in df.iterrows():
            if pd.isna(row['ceo_id']) or pd.isna(row['ceo']):
                skipped += 1
                continue
            
            ceo_id = int(row['ceo_id'])
            ceo_full = str(row['ceo']).strip()
            
            # Обрабатываем составные части
            last_name = str(row['last_name']).strip() if pd.notna(row['last_name']) else ''
            first_name = str(row['first_name']).strip() if pd.notna(row['first_name']) else ''
            middle_name = str(row['middle_name']).strip() if pd.notna(row['middle_name']) else ''
            
            # Если составные части пустые, но есть полное ФИО - разбираем
            if not last_name and not first_name and ceo_full:
                name_parts = ceo_full.split()
                if len(name_parts) >= 1:
                    last_name = name_parts[0]
                if len(name_parts) >= 2:
                    first_name = name_parts[1]
                if len(name_parts) >= 3:
                    middle_name = ' '.join(name_parts[2:])
            
            person = {
                "model": "core.person",
                "pk": ceo_id,
                "fields": {
                    "ceo": ceo_full,
                    "last_name": last_name or None,
                    "first_name": first_name or None,
                    "middle_name": middle_name or None,
                    "slug": self.slugify(f"{last_name}-{first_name}-{middle_name}"[:200]),
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat()
                }
            }
            
            self.data['person'].append(person)
            self.person_ids.add(ceo_id)
            self.stats['person'] += 1
        
        print(f"    ✅ Найдено: {len(self.data['person'])} руководителей")
        if skipped:
            print(f"    ⚠️ Пропущено: {skipped} (нет ID или ФИО)")
    
    def parse_organizations(self, excel_file):
        """Парсинг организаций (основной лист)"""
        print("  📋 Организации...")
        
        df = pd.read_excel(excel_file, 'organizations')
        
        # Проверяем наличие обязательных колонок
        if 'organization_id' not in df.columns:
            print("  ❌ В листе 'organizations' нет колонки 'organization_id'")
            return
        
        # Обрабатываем строки
        skipped_no_id = 0
        skipped_no_name = 0
        skipped_city = 0
        skipped_industry = 0
        skipped_activity = 0
        skipped_ceo = 0
        skipped_ceo_pos = 0
        
        for idx, row in df.iterrows():
            if pd.isna(row['organization_id']):
                skipped_no_id += 1
                continue
            
            org_id = int(row['organization_id'])
            
            # Пропускаем если нет названия
            if pd.isna(row.get('name')):
                skipped_no_name += 1
                continue
            
            # Формируем поля организации
            fields = {
                "organization_id": org_id,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            
            # Заполняем поля из маппинга
            for excel_col, model_field in self.COLUMN_MAPPING.items():
                if excel_col in row and pd.notna(row.get(excel_col)):
                    value = row[excel_col]
                    
                    # Обработка специальных типов
                    if model_field in ['register_opk', 'strategic']:
                        # Булевы поля (1/0, True/False, "1", "да")
                        if isinstance(value, (int, float)):
                            fields[model_field] = bool(value)
                        elif isinstance(value, str):
                            fields[model_field] = value.lower() in ['1', 'true', 'да', 'yes', 'y']
                        else:
                            fields[model_field] = False
                    
                    elif model_field in ['city', 'industry', 'activity_type', 'ceo_position', 'ceo']:
                        # Внешние ключи
                        try:
                            fields[model_field] = int(float(value))
                        except (ValueError, TypeError):
                            # Если не число, пропускаем
                            pass
                    
                    elif model_field == 'email':
                        # Email поле
                        fields[model_field] = str(value).strip()
                    
                    else:
                        # Обычные текстовые поля
                        if isinstance(value, (int, float)):
                            fields[model_field] = str(int(value)) if value == int(value) else str(value)
                        else:
                            fields[model_field] = str(value).strip()
            
            # Проверяем обязательные связи
            valid = True
            
            # Проверка города
            if 'city' in fields:
                city_id = fields['city']
                # Города будут загружены отдельно, поэтому только предупреждаем
                self.city_ids.add(city_id)
            else:
                fields['city'] = None
            
            # Проверка отрасли
            if 'industry' in fields:
                ind_id = fields['industry']
                if ind_id not in self.industry_ids:
                    print(f"    ⚠️ Организация {org_id}: нет отрасли с ID {ind_id}")
                    skipped_industry += 1
                    valid = False
            else:
                fields['industry'] = None
            
            # Проверка типа деятельности
            if 'activity_type' in fields:
                act_id = fields['activity_type']
                if act_id not in self.activity_type_ids:
                    print(f"    ⚠️ Организация {org_id}: нет типа деятельности с ID {act_id}")
                    skipped_activity += 1
                    valid = False
            else:
                fields['activity_type'] = None
            
            # Проверка должности руководителя
            if 'ceo_position' in fields:
                pos_id = fields['ceo_position']
                if pos_id not in self.ceo_position_ids:
                    print(f"    ⚠️ Организация {org_id}: нет должности с ID {pos_id}")
                    skipped_ceo_pos += 1
                    valid = False
            else:
                fields['ceo_position'] = None
            
            # Проверка руководителя
            if 'ceo' in fields:
                person_id = fields['ceo']
                if person_id not in self.person_ids:
                    print(f"    ⚠️ Организация {org_id}: нет руководителя с ID {person_id}")
                    skipped_ceo += 1
                    valid = False
            else:
                fields['ceo'] = None
            
            if not valid:
                self.stats['organizations_skipped'] += 1
                continue
            
            # Генерируем slug из названия
            name = fields.get('name', '')
            if name:
                fields['slug'] = self.slugify(str(name)[:500])
            
            # Создаем запись
            organization = {
                "model": "core.organization",
                "pk": org_id,
                "fields": fields
            }
            
            self.data['organization'].append(organization)
            self.stats['organizations'] += 1
        
        # Выводим статистику обработки
        print(f"    ✅ Найдено: {len(self.data['organization'])} организаций")
        
        issues = []
        if skipped_no_id:
            issues.append(f"нет ID: {skipped_no_id}")
        if skipped_no_name:
            issues.append(f"нет названия: {skipped_no_name}")
        if skipped_industry:
            issues.append(f"нет отрасли: {skipped_industry}")
        if skipped_activity:
            issues.append(f"нет типа деят.: {skipped_activity}")
        if skipped_ceo:
            issues.append(f"нет руководителя: {skipped_ceo}")
        if skipped_ceo_pos:
            issues.append(f"нет должности: {skipped_ceo_pos}")
        
        if issues:
            print(f"    ⚠️ Пропущено всего: {self.stats['organizations_skipped']} ({', '.join(issues)})")
    
    def save_fixtures(self):
        """Сохранение всех фикстур в файлы"""
        print("\n💾 Сохранение фикстур...")
        
        # Порядок важен для загрузки!
        fixtures_order = [
            ('industry.json', self.data['industry']),
            ('activity_type.json', self.data['activity_type']),
            ('ceo_position.json', self.data['ceo_position']),
            ('person.json', self.data['person']),
            ('organization.json', self.data['organization'])
        ]
        
        for filename, data in fixtures_order:
            if data:
                self.save_fixture(filename, data)
            else:
                print(f"  ⚠️ {filename} - нет данных")
    
    def save_fixture(self, filename, data):
        """Сохранение одной фикстуры в файл"""
        filepath = self.output_dir / filename
        
        indent = 2 if self.pretty else None
        separators = (',', ': ') if self.pretty else (',', ':')
        
        with open(filepath, 'w', encoding=self.encoding) as f:
            json.dump(data, f, ensure_ascii=False, indent=indent, separators=separators)
        
        print(f"  💾 Сохранено: {filename} ({len(data)} записей)")
    
    def slugify(self, text):
        """Простой slugify для русского текста"""
        if not text:
            return f"item-{datetime.now().timestamp()}"
        
        # Транслитерация
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
        
        # Заменяем символы
        result = []
        for char in text.lower():
            if char.isalnum():
                result.append(translit.get(char, char))
            elif char in (' ', '-', '_', '.', ',', '"', "'", '(', ')'):
                result.append('-')
        
        # Убираем повторяющиеся дефисы
        slug = ''.join(result)
        while '--' in slug:
            slug = slug.replace('--', '-')
        
        # Убираем дефисы в начале и конце
        return slug.strip('-') or f"item-{datetime.now().timestamp()}"
    
    def print_statistics(self):
        """Вывод статистики"""
        print("\n" + "="*60)
        print("📊 СТАТИСТИКА КОНВЕРТАЦИИ")
        print("="*60)
        print(f"Отрасли:                 {self.stats['industry']}")
        print(f"Типы деятельности:       {self.stats['activity_type']}")
        print(f"Должности руководителей: {self.stats['ceo_position']}")
        print(f"Руководители:            {self.stats['person']}")
        print(f"Организации:             {self.stats['organizations']}")
        if self.stats['organizations_skipped']:
            print(f"  ⚠️ Пропущено организаций: {self.stats['organizations_skipped']}")
        
        if self.city_ids:
            print(f"\n🏙️  Города (ID для проверки): {len(self.city_ids)}")
            print(f"   (Убедитесь, что city.json загружен перед organization.json)")
        
        print("="*60)
        print(f"✅ Фикстуры сохранены в: {self.output_dir}/")
        print("="*60)
        
        print("\n📌 Порядок загрузки фикстур:")
        print("   1. python manage.py loaddata industry.json")
        print("   2. python manage.py loaddata activity_type.json")
        print("   3. python manage.py loaddata ceo_position.json")
        print("   4. python manage.py loaddata person.json")
        print("   5. python manage.py loaddata city.json (из географических данных)")
        print("   6. python manage.py loaddata organization.json")


def main():
    """Точка входа"""
    parser = argparse.ArgumentParser(
        description='Конвертер Excel в Django фикстуры для организаций ОПК',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  %(prog)s organizations.xlsx
  %(prog)s data.xlsx --output fixtures --pretty
  %(prog)s organizations.xlsx --encoding cp1251 --pretty
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
    converter = ExcelToOrgFixtures(
        excel_path=args.excel_file,
        output_dir=args.output,
        pretty=args.pretty,
        encoding=args.encoding
    )
    
    success = converter.run()
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()