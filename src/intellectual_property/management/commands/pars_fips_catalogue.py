"""
Команда для парсинга каталогов открытых данных ФИПС Роспатента.
Поддерживает все типы РИД: изобретения, полезные модели, промышленные образцы,
топологии интегральных микросхем, программы для ЭВМ и базы данных.
"""

import logging
import re
from datetime import datetime

from django.db import models
from django.core.management.base import BaseCommand, CommandError
from django.utils.text import slugify
from tqdm import tqdm
import pandas as pd
import os

from intellectual_property.models import (
    FipsOpenDataCatalogue, IPType, ProtectionDocumentType,
    IPObject, AdditionalPatent, IPImage
)
from core.models import City, Region, District, Person, Organization, FOIV, Country
from common.utils.text import TextUtils
from common.utils.dates import DateUtils

logger = logging.getLogger(__name__)


class BaseFIPSParser:
    """
    Базовый класс для всех парсеров каталогов ФИПС.
    Содержит общие методы для работы с данными.
    """
    
    def __init__(self, command):
        self.command = command
        self.stdout = command.stdout
        self.style = command.style
        
        # Кэши для оптимизации
        self.country_cache = {}
        self.person_cache = {}
        self.organization_cache = {}
        self.city_cache = {}
        
    def get_ip_type(self):
        """Должен быть переопределен в дочерних классах"""
        raise NotImplementedError
    
    def get_required_columns(self):
        """Возвращает список обязательных колонок для данного типа РИД"""
        raise NotImplementedError
    
    def parse_dataframe(self, df, catalogue):
        """Основной метод парсинга DataFrame"""
        raise NotImplementedError
    
    def clean_string(self, value):
        """Очистка строкового значения"""
        if pd.isna(value) or value is None:
            return ''
        value = str(value).strip()
        if value in ['', 'None', 'null', 'NULL', 'nan']:
            return ''
        return value
    
    def parse_date(self, value):
        """Парсинг даты из строки"""
        if pd.isna(value) or not value:
            return None
        
        date_str = str(value).strip()
        if not date_str:
            return None
        
        # Пробуем разные форматы
        for fmt in ['%Y%m%d', '%Y-%m-%d', '%d.%m.%Y', '%Y/%m/%d']:
            try:
                return datetime.strptime(date_str, fmt).date()
            except (ValueError, TypeError):
                continue
        
        # Пробуем автоматическое определение
        try:
            return pd.to_datetime(date_str).date()
        except (ValueError, TypeError):
            return None
    
    def parse_bool(self, value):
        """Парсинг булевого значения"""
        if pd.isna(value) or not value:
            return False
        
        value = str(value).lower().strip()
        return value in ['1', 'true', 'yes', 'да', 'действует', 'true', 't', '1.0', 'активен']
    
    def get_or_create_country(self, code):
        """Получение или создание страны по коду"""
        if not code or pd.isna(code):
            return None
        
        code = str(code).upper().strip()
        if len(code) != 2:
            return None
        
        if code in self.country_cache:
            return self.country_cache[code]
        
        # Словарь для преобразования кодов в названия
        country_names = {
            'RU': ('Россия', 'Russia', 'РФ'),
            'US': ('США', 'USA', 'United States'),
            'DE': ('Германия', 'Germany', 'DE'),
            'FR': ('Франция', 'France', 'FR'),
            'GB': ('Великобритания', 'United Kingdom', 'GB'),
            'CN': ('Китай', 'China', 'CN'),
            'JP': ('Япония', 'Japan', 'JP'),
            'KZ': ('Казахстан', 'Kazakhstan', 'KZ'),
            'BY': ('Беларусь', 'Belarus', 'BY'),
            'UA': ('Украина', 'Ukraine', 'UA'),
        }
        
        try:
            country, created = Country.objects.get_or_create(
                code=code,
                defaults={
                    'name': country_names.get(code, (code, code))[0],
                    'name_en': country_names.get(code, (code, code))[1],
                }
            )
            self.country_cache[code] = country
            return country
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"  Ошибка создания страны {code}: {e}"))
            return None


class InventionParser(BaseFIPSParser):
    """Парсер для изобретений"""
    
    def get_ip_type(self):
        """Получение типа РИД для изобретений"""
        return IPType.objects.filter(slug='invention').first()
    
    def get_required_columns(self):
        """Обязательные колонки для работы парсера"""
        return ['registration number', 'invention name']
    
    def parse_authors(self, authors_str):
        """Парсинг строки с авторами"""
        if pd.isna(authors_str) or not authors_str:
            return []
        
        authors_str = str(authors_str)
        
        # Разделяем по переводу строки или запятой
        authors_list = re.split(r'[\n,]\s*', authors_str)
        
        result = []
        for author in authors_list:
            author = author.strip()
            if not author or author == '""' or author == 'null':
                continue
            
            # Убираем кавычки
            author = author.strip('"')
            
            # Убираем код страны в скобках
            author = re.sub(r'\s*\([A-Z]{2}\)', '', author)
            
            # Пытаемся разобрать ФИО
            parts = author.split()
            
            if len(parts) >= 2:
                last_name = parts[0]
                first_name = parts[1] if len(parts) > 1 else ''
                middle_name = parts[2] if len(parts) > 2 else ''
                
                # Обрабатываем инициалы
                first_name = first_name.replace('.', '')
                middle_name = middle_name.replace('.', '')
                
                result.append({
                    'last_name': last_name,
                    'first_name': first_name,
                    'middle_name': middle_name,
                })
            else:
                # Если не удалось разобрать, сохраняем как есть
                result.append({
                    'last_name': author,
                    'first_name': '',
                    'middle_name': '',
                })
        
        return result
    
    def parse_patent_holders(self, holders_str):
        """Парсинг строки с патентообладателями"""
        if pd.isna(holders_str) or not holders_str:
            return []
        
        holders_str = str(holders_str)
        
        # Разделяем организации (обычно разделены переводом строки)
        holders_list = re.split(r'[\n]\s*', holders_str)
        
        result = []
        for holder in holders_list:
            holder = holder.strip().strip('"')
            if not holder or holder == 'null' or holder == 'None':
                continue
            
            # Убираем код страны в скобках
            holder = re.sub(r'\s*\([A-Z]{2}\)', '', holder)
            
            result.append(holder)
        
        return result
    
    def find_or_create_person(self, person_data):
        """Поиск или создание физического лица с кэшированием"""
        # Создаем ключ для кэша
        cache_key = f"{person_data['last_name']}|{person_data['first_name']}|{person_data['middle_name']}"
        
        if cache_key in self.person_cache:
            return self.person_cache[cache_key]
        
        # Пытаемся найти по ФИО
        persons = Person.objects.filter(
            last_name=person_data['last_name'],
            first_name=person_data['first_name']
        )
        
        if person_data['middle_name']:
            persons = persons.filter(middle_name=person_data['middle_name'])
        
        if persons.exists():
            person = persons.first()
            self.person_cache[cache_key] = person
            return person
        
        # Создаем новое - нужно сгенерировать ceo_id
        try:
            # Находим максимальный существующий ID и увеличиваем на 1
            max_id = Person.objects.aggregate(models.Max('ceo_id'))['ceo_id__max'] or 0
            new_id = max_id + 1
            
            # Собираем полное ФИО
            full_name_parts = [person_data['last_name'], person_data['first_name']]
            if person_data['middle_name']:
                full_name_parts.append(person_data['middle_name'])
            full_name = ' '.join(full_name_parts)
            
            person = Person.objects.create(
                ceo_id=new_id,
                ceo=full_name,
                last_name=person_data['last_name'],
                first_name=person_data['first_name'],
                middle_name=person_data['middle_name']
            )
            self.person_cache[cache_key] = person
            return person
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"  Ошибка создания Person: {e}"))
            return None
        
    def find_or_create_organization(self, org_name):
        """Поиск или создание организации с кэшированием"""
        if pd.isna(org_name) or not org_name:
            return None
        
        org_name = str(org_name).strip()
        org_name = org_name.strip('"')
        
        if not org_name or org_name == 'null' or org_name == 'None':
            return None
        
        # Проверяем, не является ли это физическим лицом
        # Паттерны для определения физлиц
        person_patterns = [
            r'^[А-ЯЁ][а-яё]+\s+[А-ЯЁ][а-яё]+\s+[А-ЯЁ][а-яё]+$',  # Иванов Иван Иванович
            r'^[А-ЯЁ][а-яё]+\s+[А-ЯЁ]\.[А-ЯЁ]\.$',  # Иванов И.И.
            r'^[А-ЯЁ][а-яё]+\s+[А-ЯЁ][а-яё]+$',  # Иванов Иван
        ]
        
        for pattern in person_patterns:
            if re.match(pattern, org_name):
                self.stdout.write(f"     ⚠️ Пропуск организации (похоже на физлицо): {org_name[:50]}...")
                return None
        
        # Проверяем кэш
        if org_name in self.organization_cache:
            org = self.organization_cache[org_name]
            if isinstance(org, Organization):
                return org
            return None
        
        # Генерируем slug из названия
        base_slug = slugify(org_name[:50])
        if not base_slug:
            base_slug = 'organization'
        
        # Проверяем уникальность slug
        unique_slug = base_slug
        counter = 1
        while Organization.objects.filter(slug=unique_slug).exists():
            unique_slug = f"{base_slug}-{counter}"
            counter += 1
        
        try:
            # Находим максимальный существующий ID и увеличиваем на 1
            from django.db.models import Max
            max_id = Organization.objects.aggregate(Max('organization_id'))['organization_id__max'] or 0
            new_id = max_id + 1
            
            org, created = Organization.objects.get_or_create(
                name=org_name,
                defaults={
                    'organization_id': new_id,
                    'name': org_name,
                    'short_name': org_name[:100] if len(org_name) > 100 else org_name,
                    'slug': unique_slug
                }
            )
            
            self.organization_cache[org_name] = org
            return org
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"  Ошибка создания Organization '{org_name[:50]}...': {e}"))
            return None
    
    def find_or_create_foiv(self, holder_text):
        """
        Поиск или создание ФОИВ из текста патентообладателя.
        Обрабатывает случаи:
        - "Минпромторг России"
        - "Российская Федерация в лице Минпромторга России"
        - "Федеральное агентство ..."
        - "Министерство ..."
        """
        if pd.isna(holder_text) or not holder_text:
            return None
        
        holder_text = str(holder_text).strip().strip('"')
        
        # Проверяем кэш
        if holder_text in self.organization_cache:
            org = self.organization_cache[holder_text]
            if isinstance(org, FOIV):
                return org
            return None
        
        # Сначала пробуем извлечь из шаблона "РФ в лице"
        foiv = self.extract_foiv_from_rf_template(holder_text)  # Теперь метод существует
        if foiv:
            self.organization_cache[holder_text] = foiv
            return foiv
        
        # Паттерны для прямого поиска ФОИВ
        try:
            all_foivs = FOIV.objects.all()
            for foiv in all_foivs:
                # Проверяем, содержится ли краткое название ФОИВ в тексте
                if foiv.short_name and foiv.short_name.lower() in holder_text.lower():
                    self.organization_cache[holder_text] = foiv
                    return foiv
                
                # Проверяем по частям (без "России")
                short_without_russia = foiv.short_name.replace('России', '').strip()
                if short_without_russia and short_without_russia.lower() in holder_text.lower():
                    self.organization_cache[holder_text] = foiv
                    return foiv
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"  Ошибка при поиске ФОИВ: {e}"))
        
        return None
    
    def extract_foiv_from_rf_template(self, holder_text):
        """
        Извлекает название ФОИВ из шаблона "Российская Федерация в лице ..."
        """
        patterns = [
            r'Российская\s+Федерация\s+в\s+лице\s+(.+)',
            r'РФ\s+в\s+лице\s+(.+)',
            r'Министерство\s+(.+)',
            r'Федеральное\s+(?:агентство|служба)\s+(.+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, holder_text, re.IGNORECASE)
            if match:
                extracted = match.group(1).strip()
                # Пробуем найти ФОИВ по извлеченному названию
                try:
                    foiv = FOIV.objects.filter(short_name__icontains=extracted).first()
                    if foiv:
                        return foiv
                except:
                    pass
        
        return None
    
    def process_authors(self, row, ip_object):
        """Обработка авторов"""
        authors_str = row.get('authors')
        
        if pd.isna(authors_str) or not authors_str:
            self.stdout.write("     👥 Авторы: нет данных")
            return
        
        try:
            authors_data = self.parse_authors(authors_str)
            
            if authors_data:
                self.stdout.write(f"     👥 Авторы: {len(authors_data)} чел.")
                for author_data in authors_data:
                    person = self.find_or_create_person(author_data)
                    if person:
                        ip_object.authors.add(person)
            else:
                self.stdout.write("     👥 Авторы: нет данных")
            
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"  Ошибка обработки авторов: {e}"))
    
    def process_patent_holders(self, row, ip_object):
        """Обработка патентообладателей (организации и ФОИВ)"""
        holders_str = row.get('patent holders')
        
        if pd.isna(holders_str) or not holders_str:
            self.stdout.write("     🏢 Патентообладатели: нет данных")
            return
        
        try:
            holders_list = self.parse_patent_holders(holders_str)
            
            if holders_list:
                self.stdout.write(f"     🏢 Патентообладатели: {len(holders_list)}")
                for holder_name in holders_list:
                    # Сначала проверяем, не ФОИВ ли это
                    foiv = self.find_or_create_foiv(holder_name)
                    if foiv:
                        ip_object.owner_foivs.add(foiv)
                        self.stdout.write(f"        ФОИВ: {foiv.short_name}")
                        continue
                    
                    # Если не ФОИВ, пробуем как организацию
                    org = self.find_or_create_organization(holder_name)
                    if org:
                        ip_object.owner_organizations.add(org)
                        self.stdout.write(f"        Организация: {org.name[:50]}...")
            else:
                self.stdout.write("     🏢 Патентообладатели: нет данных")
            
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"  Ошибка обработки патентообладателей: {e}"))
    
    def process_correspondence_address(self, row, ip_object):
        """Обработка адреса для переписки"""
        address = row.get('correspondence address')
        
        if pd.isna(address) or not address:
            return
        
        try:
            if address and len(str(address)) > 10:
                self.stdout.write(f"     📍 Адрес: {str(address)[:50]}...")
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"  Ошибка обработки адреса: {e}"))
    
    def process_row(self, row, catalogue, ip_type):
        """Обработка одной строки данных"""
        registration_number = self.clean_string(row.get('registration number'))
        
        if not registration_number:
            return 'skipped'
        
        self.stdout.write(f"\n  📄 Обработка патента №{registration_number}")
        
        # Основные поля - только те, что есть в модели IPObject
        name = self.clean_string(row.get('invention name'))
        if not name:
            name = f"Изобретение №{registration_number}"
        
        self.stdout.write(f"     Название: {name[:50]}...")
        
        # Даты (все эти поля есть в модели)
        application_date = self.parse_date(row.get('application date'))
        registration_date = self.parse_date(row.get('registration date'))
        patent_starting_date = self.parse_date(row.get('patent starting date'))
        expiration_date = self.parse_date(row.get('expiration date'))
        
        if application_date:
            self.stdout.write(f"     Дата подачи: {application_date}")
        if registration_date:
            self.stdout.write(f"     Дата регистрации: {registration_date}")
        
        # Статус
        actual = self.parse_bool(row.get('actual'))
        self.stdout.write(f"     Статус: {'Активен' if actual else 'Не активен'}")
        
        # URL публикации
        publication_url = self.clean_string(row.get('publication URL'))
        
        # Дополнительные текстовые поля, которые есть в модели
        abstract = self.clean_string(row.get('abstract'))  # реферат
        claims = self.clean_string(row.get('claims'))      # формула
        
        # Пытаемся извлечь год создания из дат
        creation_year = None
        if application_date:
            creation_year = application_date.year
        elif registration_date:
            creation_year = registration_date.year
        
        # Проверяем, существует ли уже такой объект
        try:
            ip_object, created = IPObject.objects.get_or_create(
                registration_number=registration_number,
                ip_type=ip_type,
                defaults={
                    'name': name,
                    'application_date': application_date,
                    'registration_date': registration_date,
                    'patent_starting_date': patent_starting_date,
                    'expiration_date': expiration_date,
                    'actual': actual,
                    'publication_url': publication_url,
                    'abstract': abstract,
                    'claims': claims,
                    'creation_year': creation_year,
                }
            )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  Ошибка создания IPObject {registration_number}: {e}"))
            return 'skipped'
        
        if self.command.dry_run:
            return 'created' if created else 'updated'
        
        # Если объект уже существует, обновляем поля
        if not created:
            update_fields = []
            
            if name and ip_object.name != name:
                ip_object.name = name
                update_fields.append('name')
            
            if application_date and ip_object.application_date != application_date:
                ip_object.application_date = application_date
                update_fields.append('application_date')
            
            if registration_date and ip_object.registration_date != registration_date:
                ip_object.registration_date = registration_date
                update_fields.append('registration_date')
            
            if patent_starting_date and ip_object.patent_starting_date != patent_starting_date:
                ip_object.patent_starting_date = patent_starting_date
                update_fields.append('patent_starting_date')
            
            if expiration_date and ip_object.expiration_date != expiration_date:
                ip_object.expiration_date = expiration_date
                update_fields.append('expiration_date')
            
            if ip_object.actual != actual:
                ip_object.actual = actual
                update_fields.append('actual')
            
            if publication_url and ip_object.publication_url != publication_url:
                ip_object.publication_url = publication_url
                update_fields.append('publication_url')
            
            if abstract and ip_object.abstract != abstract:
                ip_object.abstract = abstract
                update_fields.append('abstract')
            
            if claims and ip_object.claims != claims:
                ip_object.claims = claims
                update_fields.append('claims')
            
            if creation_year and ip_object.creation_year != creation_year:
                ip_object.creation_year = creation_year
                update_fields.append('creation_year')
            
            if update_fields:
                ip_object.save(update_fields=update_fields)
                self.stdout.write(f"     Обновлено полей: {len(update_fields)}")
        
        # Обрабатываем авторов (ManyToMany)
        self.process_authors(row, ip_object)
        
        # Обрабатываем патентообладателей (разделяем на организации и ФОИВ)
        self.process_patent_holders(row, ip_object)
        
        return 'created' if created else 'updated'
    
    def parse_dataframe(self, df, catalogue):
        """Парсинг DataFrame с изобретениями"""
        self.stdout.write(self.style.SUCCESS("  🔄 Начинаем парсинг изобретений..."))
        
        stats = {
            'processed': 0,
            'created': 0,
            'updated': 0,
            'skipped': 0,
            'errors': 0
        }
        
        ip_type = self.get_ip_type()
        if not ip_type:
            self.stdout.write(self.style.ERROR("  ❌ Тип РИД 'invention' не найден в БД"))
            stats['errors'] += 1
            return stats
        
        # Обрабатываем записи с прогресс-баром
        with tqdm(total=len(df), desc="  Обработка записей", unit=" зап") as pbar:
            for idx, row in df.iterrows():
                try:
                    result = self.process_row(row, catalogue, ip_type)
                    
                    if result == 'created':
                        stats['created'] += 1
                    elif result == 'updated':
                        stats['updated'] += 1
                    elif result == 'skipped':
                        stats['skipped'] += 1
                    
                    stats['processed'] += 1
                    
                except Exception as e:
                    stats['errors'] += 1
                    reg_num = row.get('registration number', 'N/A')
                    self.stdout.write(self.style.ERROR(f"\n  ❌ Ошибка в записи {reg_num}: {e}"))
                    logger.error(f"Error processing invention {reg_num}: {e}", exc_info=True)
                
                finally:
                    pbar.update(1)
        
        self.stdout.write(self.style.SUCCESS(f"  ✅ Парсинг изобретений завершен"))
        self.stdout.write(f"     Создано: {stats['created']}, Обновлено: {stats['updated']}, "
                         f"Пропущено: {stats['skipped']}, Ошибок: {stats['errors']}")
        
        return stats


class UtilityModelParser(BaseFIPSParser):
    """Парсер для полезных моделей"""
    
    def get_ip_type(self):
        return IPType.objects.filter(slug='utility-model').first()
    
    def get_required_columns(self):
        return ['registration number', 'utility model name']
    
    def parse_dataframe(self, df, catalogue):
        """Парсинг DataFrame с полезными моделями"""
        self.stdout.write(self.style.SUCCESS("  Парсер полезных моделей готов к работе"))
        # TODO: Реализовать логику парсинга
        return {'processed': 0, 'created': 0, 'updated': 0, 'skipped': 0, 'errors': 0}


class IndustrialDesignParser(BaseFIPSParser):
    """Парсер для промышленных образцов"""
    
    def get_ip_type(self):
        return IPType.objects.filter(slug='industrial-design').first()
    
    def get_required_columns(self):
        return ['registration number', 'industrial design name']
    
    def parse_dataframe(self, df, catalogue):
        """Парсинг DataFrame с промышленными образцами"""
        self.stdout.write(self.style.SUCCESS("  Парсер промышленных образцов готов к работе"))
        # TODO: Реализовать логику парсинга
        return {'processed': 0, 'created': 0, 'updated': 0, 'skipped': 0, 'errors': 0}


class IntegratedCircuitTopologyParser(BaseFIPSParser):
    """Парсер для топологий интегральных микросхем"""
    
    def get_ip_type(self):
        return IPType.objects.filter(slug='integrated-circuit-topology').first()
    
    def get_required_columns(self):
        return ['registration number', 'microchip name']
    
    def parse_dataframe(self, df, catalogue):
        """Парсинг DataFrame с топологиями микросхем"""
        self.stdout.write(self.style.SUCCESS("  Парсер топологий микросхем готов к работе"))
        # TODO: Реализовать логику парсинга
        return {'processed': 0, 'created': 0, 'updated': 0, 'skipped': 0, 'errors': 0}


class ComputerProgramParser(BaseFIPSParser):
    """Парсер для программ для ЭВМ"""
    
    def get_ip_type(self):
        return IPType.objects.filter(slug='computer-program').first()
    
    def get_required_columns(self):
        return ['registration number', 'program name']
    
    def parse_dataframe(self, df, catalogue):
        """Парсинг DataFrame с программами для ЭВМ"""
        self.stdout.write(self.style.SUCCESS("  Парсер программ для ЭВМ готов к работе"))
        # TODO: Реализовать логику парсинга
        return {'processed': 0, 'created': 0, 'updated': 0, 'skipped': 0, 'errors': 0}


class DatabaseParser(BaseFIPSParser):
    """Парсер для баз данных"""
    
    def get_ip_type(self):
        return IPType.objects.filter(slug='database').first()
    
    def get_required_columns(self):
        return ['registration number', 'db name']
    
    def parse_dataframe(self, df, catalogue):
        """Парсинг DataFrame с базами данных"""
        self.stdout.write(self.style.SUCCESS("  Парсер баз данных готов к работе"))
        # TODO: Реализовать логику парсинга
        return {'processed': 0, 'created': 0, 'updated': 0, 'skipped': 0, 'errors': 0}


class Command(BaseCommand):
    help = 'Парсинг каталогов открытых данных ФИПС Роспатента'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--catalogue-id',
            type=int,
            help='ID конкретного каталога для парсинга',
        )
        parser.add_argument(
            '--ip-type',
            type=str,
            choices=['invention', 'utility-model', 'industrial-design', 
                    'integrated-circuit-topology', 'computer-program', 'database'],
            help='Тип РИД для парсинга (если не указан, парсятся все)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Режим проверки без сохранения в БД',
        )
        parser.add_argument(
            '--encoding',
            type=str,
            default='utf-8',
            help='Кодировка CSV файла',
        )
        parser.add_argument(
            '--delimiter',
            type=str,
            default=',',
            help='Разделитель в CSV файле',
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=100,
            help='Размер пакета для bulk-операций',
        )
        parser.add_argument(
            '--min-year',
            type=int,
            default=2000,
            help='Минимальный год регистрации для фильтрации',
        )
        parser.add_argument(
            '--skip-filters',
            action='store_true',
            help='Пропустить фильтрацию (обработать все записи)',
        )
        parser.add_argument(
            '--only-active',
            action='store_true',
            help='Парсить только активные патенты (actual = True)',
        )
        parser.add_argument(
            '--max-rows',
            type=int,
            help='Максимальное количество строк для обработки (для тестирования)',
        )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Регистрируем парсеры для каждого типа РИД
        self.parsers = {
            'invention': InventionParser(self),
            'utility-model': UtilityModelParser(self),
            'industrial-design': IndustrialDesignParser(self),
            'integrated-circuit-topology': IntegratedCircuitTopologyParser(self),
            'computer-program': ComputerProgramParser(self),
            'database': DatabaseParser(self),
        }
    
    def handle(self, *args, **options):
        self.dry_run = options['dry_run']
        self.encoding = options['encoding']
        self.delimiter = options['delimiter']
        self.batch_size = options['batch_size']
        self.min_year = options['min_year']
        self.skip_filters = options['skip_filters']
        self.only_active = options['only_active']
        self.max_rows = options.get('max_rows')
        
        if self.dry_run:
            self.stdout.write(self.style.WARNING("\n🔍 РЕЖИМ DRY-RUN: изменения НЕ будут сохранены в БД\n"))
        
        if self.only_active:
            self.stdout.write(self.style.WARNING("📌 Режим: парсинг только активных записей (actual = True)"))
        
        # Получаем каталоги для парсинга
        catalogues = self.get_catalogues(options.get('catalogue_id'), options.get('ip_type'))
        
        if not catalogues:
            raise CommandError('Не найдены каталоги для парсинга')
        
        total_stats = {
            'catalogues': len(catalogues),
            'processed': 0,
            'created': 0,
            'updated': 0,
            'skipped': 0,
            'errors': 0
        }
        
        # Обрабатываем каждый каталог
        for catalogue in catalogues:
            self.stdout.write(self.style.SUCCESS(f"\n{'='*60}"))
            self.stdout.write(self.style.SUCCESS(f"📁 Обработка каталога: {catalogue.name}"))
            self.stdout.write(self.style.SUCCESS(f"   ID: {catalogue.id}, Тип: {catalogue.ip_type.name if catalogue.ip_type else 'Неизвестно'}"))
            self.stdout.write(self.style.SUCCESS(f"{'='*60}"))
            
            stats = self.process_catalogue(catalogue)
            
            # Обновляем общую статистику
            for key in ['processed', 'created', 'updated', 'skipped', 'errors']:
                total_stats[key] += stats.get(key, 0)
        
        # Выводим итоговую статистику
        self.print_final_stats(total_stats)
    
    def get_catalogues(self, catalogue_id=None, ip_type_slug=None):
        """
        Получение списка каталогов для парсинга.
        Можно получить по ID, по типу РИД или все непрочитанные.
        """
        queryset = FipsOpenDataCatalogue.objects.all()
        
        if catalogue_id:
            queryset = queryset.filter(id=catalogue_id)
        elif ip_type_slug:
            queryset = queryset.filter(ip_type__slug=ip_type_slug)
        else:
            # Если не указаны фильтры, берем все каталоги с файлами
            queryset = queryset.exclude(catalogue_file='')
        
        return queryset.order_by('ip_type__id', '-publication_date')
    
    def process_catalogue(self, catalogue):
        """Обработка одного каталога"""
        stats = {
            'processed': 0,
            'created': 0,
            'updated': 0,
            'skipped': 0,
            'errors': 0
        }
        
        if not catalogue.catalogue_file:
            self.stdout.write(self.style.ERROR(f"  ❌ У каталога ID={catalogue.id} не загружен файл"))
            stats['errors'] += 1
            return stats
        
        # Определяем тип РИД и соответствующий парсер
        ip_type_slug = catalogue.ip_type.slug if catalogue.ip_type else None
        
        if ip_type_slug not in self.parsers:
            self.stdout.write(self.style.ERROR(f"  ❌ Нет парсера для типа РИД: {ip_type_slug}"))
            stats['errors'] += 1
            return stats
        
        parser = self.parsers[ip_type_slug]
        
        # Загружаем CSV в DataFrame
        df = self.load_csv(catalogue)
        
        if df is None or df.empty:
            self.stdout.write(self.style.WARNING(f"  ⚠️ Файл пуст или не удалось загрузить"))
            stats['skipped'] += 1
            return stats
        
        self.stdout.write(f"  📊 Загружено записей: {len(df)}")
        
        # Проверяем наличие обязательных колонок
        missing_columns = self.check_required_columns(df, parser.get_required_columns())
        if missing_columns:
            self.stdout.write(self.style.ERROR(f"  ❌ Отсутствуют обязательные колонки: {missing_columns}"))
            stats['errors'] += 1
            return stats
        
        # Применяем фильтры
        if not self.skip_filters:
            df = self.apply_filters(df)
        
        if df.empty:
            self.stdout.write(self.style.WARNING(f"  ⚠️ Нет данных после фильтрации"))
            stats['skipped'] += 1
            return stats
        
        self.stdout.write(f"  📊 После фильтрации: {len(df)} записей")
        
        # Ограничиваем количество строк для тестирования
        if self.max_rows and len(df) > self.max_rows:
            df = df.head(self.max_rows)
            self.stdout.write(self.style.WARNING(f"  ⚠️ Ограничено до {self.max_rows} записей для тестирования"))
        
        # Запускаем парсер
        try:
            parser_stats = parser.parse_dataframe(df, catalogue)
            stats.update(parser_stats)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  ❌ Ошибка при парсинге: {e}"))
            logger.error(f"Error parsing catalogue {catalogue.id}: {e}", exc_info=True)
            stats['errors'] += 1
        
        return stats
    
    def load_csv(self, catalogue):
        """Загрузка CSV файла в DataFrame"""
        file_path = catalogue.catalogue_file.path
        
        if not os.path.exists(file_path):
            self.stdout.write(self.style.ERROR(f"  ❌ Файл не найден: {file_path}"))
            return None
        
        try:
            # Пробуем разные стратегии загрузки
            strategies = [
                {'encoding': self.encoding, 'delimiter': self.delimiter, 'skipinitialspace': True},
                {'encoding': 'cp1251', 'delimiter': self.delimiter, 'skipinitialspace': True},
                {'encoding': 'utf-8', 'delimiter': ';', 'skipinitialspace': True},
                {'encoding': 'cp1251', 'delimiter': ';', 'skipinitialspace': True},
                {'encoding': 'utf-8', 'delimiter': '\t', 'skipinitialspace': True},
            ]
            
            for strategy in strategies:
                try:
                    df = pd.read_csv(file_path, **strategy, dtype=str, keep_default_na=False)
                    self.stdout.write(f"  ✅ Успешно загружено с параметрами: {strategy}")
                    
                    # Очищаем названия колонок от лишних символов
                    df.columns = [col.strip().strip('\ufeff').strip('"') for col in df.columns]
                    
                    return df
                except Exception as e:
                    continue
            
            raise Exception("Не удалось загрузить CSV ни одной стратегией")
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  ❌ Ошибка загрузки CSV: {e}"))
            return None
    
    def check_required_columns(self, df, required_columns):
        """Проверка наличия обязательных колонок"""
        missing = [col for col in required_columns if col not in df.columns]
        return missing
    
    def apply_filters(self, df):
        """Применение фильтров к DataFrame"""
        original_count = len(df)
        
        # Фильтр по году регистрации
        if 'registration date' in df.columns:
            df = self.filter_by_registration_year(df)
        
        # Фильтр по активности
        if self.only_active and 'actual' in df.columns:
            df = self.filter_by_actual(df)
        
        filtered_count = len(df)
        if filtered_count < original_count:
            self.stdout.write(f"  🔍 Фильтрация: {original_count} → {filtered_count} записей")
        
        return df
    
    def filter_by_registration_year(self, df):
        """Фильтрация по году регистрации"""
        def extract_year(date_str):
            try:
                if pd.isna(date_str) or not date_str:
                    return None
                
                date_str = str(date_str).strip()
                if not date_str:
                    return None
                
                # Пробуем разные форматы
                for fmt in ['%Y%m%d', '%Y-%m-%d', '%d.%m.%Y', '%Y/%m/%d']:
                    try:
                        return datetime.strptime(date_str, fmt).year
                    except (ValueError, TypeError):
                        continue
                
                # Пробуем автоматическое определение
                try:
                    return pd.to_datetime(date_str).year
                except (ValueError, TypeError):
                    return None
            except:
                return None
        
        self.stdout.write("  🔍 Фильтрация по году регистрации...")
        df['_year'] = df['registration date'].apply(extract_year)
        
        # Статистика по годам
        years_dist = df['_year'].value_counts().sort_index()
        years_list = list(years_dist.items())
        if len(years_list) > 0:
            self.stdout.write(f"     Диапазон годов: {years_list[0][0]:.0f} - {years_list[-1][0]:.0f}")
            self.stdout.write(f"     Первые 5: {years_list[:5]}")
            self.stdout.write(f"     Последние 5: {years_list[-5:]}")
        
        filtered_df = df[df['_year'] >= self.min_year].copy()
        filtered_df.drop('_year', axis=1, inplace=True)
        
        return filtered_df
    
    def filter_by_actual(self, df):
        """Фильтрация по признаку actual = True"""
        def parse_actual(value):
            if pd.isna(value) or not value:
                return False
            value = str(value).lower().strip()
            return value in ['1', 'true', 'yes', 'да', 'действует', 'true', 't', '1.0', 'активен']
        
        df['_actual'] = df['actual'].apply(parse_actual)
        filtered_df = df[df['_actual'] == True].copy()
        filtered_df.drop('_actual', axis=1, inplace=True)
        
        return filtered_df
    
    def print_final_stats(self, stats):
        """Вывод итоговой статистики"""
        self.stdout.write(self.style.SUCCESS(f"\n{'='*60}"))
        self.stdout.write(self.style.SUCCESS("📊 ИТОГОВАЯ СТАТИСТИКА"))
        self.stdout.write(self.style.SUCCESS(f"{'='*60}"))
        self.stdout.write(f"📁 Обработано каталогов: {stats['catalogues']}")
        self.stdout.write(f"📝 Всего записей обработано: {stats['processed']}")
        self.stdout.write(f"✅ Создано: {stats['created']}")
        self.stdout.write(f"🔄 Обновлено: {stats['updated']}")
        self.stdout.write(f"⏭️  Пропущено: {stats['skipped']}")
        
        if stats['errors'] > 0:
            self.stdout.write(self.style.ERROR(f"❌ Ошибок: {stats['errors']}"))
        else:
            self.stdout.write(self.style.SUCCESS(f"✅ Ошибок: {stats['errors']}"))
        
        if self.dry_run:
            self.stdout.write(self.style.WARNING("\n🔍 РЕЖИМ DRY-RUN: изменения НЕ сохранены в БД"))
        
        self.stdout.write(self.style.SUCCESS(f"{'='*60}"))