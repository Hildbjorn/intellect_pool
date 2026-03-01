"""
Базовый класс для всех парсеров каталогов ФИПС
Поддерживает параметр year для обработки по годам
"""

import logging
import re
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
import gc

from django.db import models
from django.utils.text import slugify
import pandas as pd

from intellectual_property.models import IPObject, IPType
from core.models import Person, Organization, Country

from .processors import (
    RussianTextProcessor,
    OrganizationNormalizer,
    PersonNameFormatter,
    RIDNameFormatter,
    EntityTypeDetector
)

from ..utils.progress import batch_iterator

logger = logging.getLogger(__name__)


class BaseFIPSParser:
    """Базовый класс для всех парсеров каталогов ФИПС"""

    def __init__(self, command):
        self.command = command
        self.stdout = command.stdout
        self.style = command.style

        # Инициализация процессоров
        self.processor = RussianTextProcessor()
        self.org_normalizer = OrganizationNormalizer()
        self.type_detector = EntityTypeDetector()
        self.person_formatter = PersonNameFormatter()
        self.rid_formatter = RIDNameFormatter()

        # Кэши для оптимизации
        self.country_cache = {}
        self.person_cache = {}
        self.organization_cache = {}
        self.foiv_cache = {}
        self.rf_rep_cache = {}
        self.city_cache = {}
        self.activity_type_cache = {}
        self.ceo_position_cache = {}

    def get_ip_type(self):
        """Должен быть переопределен в дочерних классах"""
        raise NotImplementedError

    def get_required_columns(self):
        """Возвращает список обязательных колонок"""
        raise NotImplementedError

    def parse_dataframe(self, df, catalogue, year=None):
        """
        Основной метод парсинга DataFrame
        
        Args:
            df: DataFrame с данными
            catalogue: объект каталога
            year: год для текущей обработки (опционально)
        """
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

        for fmt in ['%Y%m%d', '%Y-%m-%d', '%d.%m.%Y', '%Y/%m/%d']:
            try:
                return datetime.strptime(date_str, fmt).date()
            except (ValueError, TypeError):
                continue

        try:
            return pd.to_datetime(date_str).date()
        except (ValueError, TypeError):
            return None

    def parse_bool(self, value):
        """Парсинг булевого значения"""
        if pd.isna(value) or not value:
            return False
        value = str(value).lower().strip()
        return value in ['1', 'true', 'yes', 'да', 'действует', 't', '1.0', 'активен']

    def get_or_create_country(self, code):
        """Получение страны по коду"""
        if not code or pd.isna(code):
            return None

        code = str(code).upper().strip()
        if len(code) != 2:
            return None

        if code in self.country_cache:
            return self.country_cache[code]

        try:
            country = Country.objects.filter(code=code).first()
            if country:
                self.country_cache[code] = country
                return country

            country = Country.objects.filter(code_alpha3=code).first()
            if country:
                self.country_cache[code] = country
                return country

            return None

        except Exception as e:
            self.stdout.write(self.style.WARNING(f"  Ошибка поиска страны {code}: {e}"))
            return None

    def parse_authors(self, authors_str):
        """
        Парсинг строки с авторами
        Возвращает список словарей с данными авторов
        """
        if pd.isna(authors_str) or not authors_str:
            return []

        authors_str = str(authors_str)
        authors_list = re.split(r'[\n,]\s*', authors_str)

        result = []
        for author in authors_list:
            author = author.strip()
            if not author or author == '""' or author == 'null':
                continue

            author = author.strip('"')
            author = re.sub(r'\s*\([A-Z]{2}\)', '', author)
            author = self.person_formatter.format(author)

            parts = author.split()

            if len(parts) >= 2:
                last_name = parts[0]
                first_name = parts[1] if len(parts) > 1 else ''
                middle_name = parts[2] if len(parts) > 2 else ''

                first_name_clean = first_name.replace('.', '')
                middle_name_clean = middle_name.replace('.', '')

                result.append({
                    'last_name': last_name,
                    'first_name': first_name_clean,
                    'middle_name': middle_name_clean,
                    'full_name': author,
                })
            else:
                result.append({
                    'last_name': author,
                    'first_name': '',
                    'middle_name': '',
                    'full_name': author,
                })

        return result

    def parse_patent_holders(self, holders_str):
        """
        Парсинг строки с патентообладателями
        Возвращает список названий
        """
        if pd.isna(holders_str) or not holders_str:
            return []

        holders_str = str(holders_str)
        holders_list = re.split(r'[\n]\s*', holders_str)

        result = []
        for holder in holders_list:
            holder = holder.strip().strip('"')
            if not holder or holder == 'null' or holder == 'None':
                continue

            holder = re.sub(r'\s*\([A-Z]{2}\)', '', holder)
            result.append(holder)

        return result

    def find_or_create_person(self, person_data):
        """Поиск или создание физического лица"""
        cache_key = f"{person_data['last_name']}|{person_data['first_name']}|{person_data['middle_name']}"

        if cache_key in self.person_cache:
            return self.person_cache[cache_key]

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

        try:
            max_id = Person.objects.aggregate(models.Max('ceo_id'))['ceo_id__max'] or 0
            new_id = max_id + 1

            if 'full_name' in person_data:
                full_name = person_data['full_name']
            else:
                full_name_parts = [person_data['last_name'], person_data['first_name']]
                if person_data['middle_name']:
                    full_name_parts.append(person_data['middle_name'])
                full_name = ' '.join(full_name_parts)
                full_name = self.person_formatter.format(full_name)

            # Генерируем уникальный slug
            base_slug = slugify(f"{person_data['last_name']} {person_data['first_name']} {person_data['middle_name']}".strip())
            if not base_slug:
                base_slug = 'person'

            unique_slug = base_slug
            counter = 1
            while Person.objects.filter(slug=unique_slug).exists():
                unique_slug = f"{base_slug}-{counter}"
                counter += 1

            person = Person.objects.create(
                ceo_id=new_id,
                ceo=full_name,
                last_name=person_data['last_name'],
                first_name=person_data['first_name'],
                middle_name=person_data['middle_name'],
                slug=unique_slug
            )
            self.person_cache[cache_key] = person
            return person
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"  Ошибка создания Person: {e}"))
            return None

    def find_or_create_person_from_name(self, full_name):
        """Поиск или создание физического лица по полному имени"""
        if pd.isna(full_name) or not full_name:
            return None

        full_name = str(full_name).strip().strip('"')
        full_name = self.person_formatter.format(full_name)

        if full_name in self.person_cache:
            return self.person_cache[full_name]

        parts = full_name.split()

        if len(parts) >= 2:
            last_name = parts[0]
            first_name = parts[1] if len(parts) > 1 else ''
            middle_name = parts[2] if len(parts) > 2 else ''

            first_name_clean = first_name.replace('.', '')
            middle_name_clean = middle_name.replace('.', '')

            person_data = {
                'last_name': last_name,
                'first_name': first_name_clean,
                'middle_name': middle_name_clean,
                'full_name': full_name,
            }
        else:
            person_data = {
                'last_name': full_name,
                'first_name': '',
                'middle_name': '',
                'full_name': full_name,
            }

        return self.find_or_create_person(person_data)

    def find_similar_organization(self, org_name):
        """Усиленный поиск похожей организации"""
        if pd.isna(org_name) or not org_name:
            return None

        org_name = str(org_name).strip().strip('"')

        # Стратегия 1: Прямое совпадение
        direct_match = Organization.objects.filter(
            models.Q(name=org_name) |
            models.Q(full_name=org_name) |
            models.Q(short_name=org_name)
        ).first()
        if direct_match:
            return direct_match

        # Нормализуем название для поиска
        norm_data = self.org_normalizer.normalize_for_search(org_name)
        normalized = norm_data['normalized']
        keywords = norm_data['keywords']

        # Стратегия 2: Поиск по ключевым словам
        for keyword in keywords:
            if len(keyword) >= 3:
                similar = Organization.objects.filter(
                    models.Q(name__icontains=keyword) |
                    models.Q(full_name__icontains=keyword) |
                    models.Q(short_name__icontains=keyword)
                ).first()
                if similar:
                    return similar

        # Стратегия 3: Поиск по первым 30 символам
        if len(normalized) > 30:
            prefix = normalized[:30]
            similar = Organization.objects.filter(
                models.Q(name__icontains=prefix) |
                models.Q(full_name__icontains=prefix) |
                models.Q(short_name__icontains=prefix)
            ).first()
            if similar:
                return similar

        # Стратегия 4: Поиск по отдельным словам
        words = org_name.split()
        for word in words:
            if len(word) > 4:
                similar = Organization.objects.filter(
                    models.Q(name__icontains=word) |
                    models.Q(full_name__icontains=word)
                ).first()
                if similar:
                    return similar

        return None

    def find_or_create_organization(self, org_name):
        """Поиск или создание организации с сохранением оригинального названия"""
        if pd.isna(org_name) or not org_name:
            return None

        org_name = str(org_name).strip().strip('"')

        if not org_name or org_name == 'null' or org_name == 'None':
            return None

        # Проверяем кэш
        if org_name in self.organization_cache:
            return self.organization_cache[org_name]

        # Ищем похожие
        similar = self.find_similar_organization(org_name)
        if similar:
            self.organization_cache[org_name] = similar
            return similar

        # Не нашли - создаем новую с оригинальным названием
        try:
            max_id = Organization.objects.aggregate(models.Max('organization_id'))['organization_id__max'] or 0
            new_id = max_id + 1

            # Генерируем slug из оригинального названия
            base_slug = slugify(org_name[:50])
            if not base_slug:
                base_slug = 'organization'

            unique_slug = base_slug
            counter = 1
            while Organization.objects.filter(slug=unique_slug).exists():
                unique_slug = f"{base_slug}-{counter}"
                counter += 1

            # Сохраняем оригинальное название без изменений
            org = Organization.objects.create(
                organization_id=new_id,
                name=org_name,
                full_name=org_name,
                short_name=org_name[:500] if len(org_name) > 500 else org_name,
                slug=unique_slug,
                register_opk=False,
                strategic=False,
            )

            self.organization_cache[org_name] = org
            return org
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"  Ошибка создания Organization: {e}"))
            return None

    # =========================================================================
    # МЕТОДЫ ДЛЯ МАССОВОГО СОЗДАНИЯ ЛЮДЕЙ
    # =========================================================================

    def _create_persons_bulk(self, persons_df: pd.DataFrame) -> Dict[str, Person]:
        """
        Пакетное создание людей из DataFrame с индикацией прогресса
        
        Args:
            persons_df: DataFrame с колонкой 'entity_name'
            
        Returns:
            Словарь {имя: объект Person}
        """
        person_map = {}
        
        if persons_df.empty:
            self.stdout.write("      Нет людей для обработки")
            return person_map
        
        all_names = persons_df['entity_name'].tolist()
        total_names = len(all_names)
        
        self.stdout.write(f"      Всего уникальных людей для обработки: {total_names}")
        
        # ШАГ 1: Поиск существующих людей
        self.stdout.write(f"      Поиск существующих людей в БД...")
        
        name_to_parts = self._extract_name_parts(all_names)
        existing_persons = self._find_existing_persons(name_to_parts)
        
        # ШАГ 2: Определяем новых людей
        valid_names = list(name_to_parts.keys())
        new_names = [name for name in valid_names if name not in existing_persons]
        new_count = len(new_names)
        
        self.stdout.write(f"      Новых людей для создания: {new_count}")
        
        # ШАГ 3: Создаем новых людей
        if new_names:
            new_persons_map = self._create_new_persons(new_names)
            person_map.update(new_persons_map)
        
        # ШАГ 4: Добавляем существующих людей в маппинг
        person_map.update(existing_persons)
        
        self.stdout.write(f"      ✅ Обработано людей: {len(person_map)}")
        
        return person_map

    def _extract_name_parts(self, names: List[str]) -> Dict[str, Tuple[str, str, str]]:
        """
        Извлечение частей ФИО из списка имен
        
        Returns:
            Словарь {полное_имя: (фамилия, имя, отчество)}
        """
        name_to_parts = {}
        for name in names:
            if pd.isna(name) or not name:
                continue
            name = str(name).strip()
            if not name:
                continue
            
            parts = name.split()
            if len(parts) >= 2:
                last = parts[0]
                first = parts[1]
                middle = parts[2] if len(parts) > 2 else ''
                name_to_parts[name] = (last, first, middle)
        
        return name_to_parts

    def _find_existing_persons(self, name_to_parts: Dict[str, Tuple[str, str, str]]) -> Dict[str, Person]:
        """
        Поиск существующих людей в БД
        
        Returns:
            Словарь {имя: объект Person}
        """
        existing_persons = {}
        found_count = 0
        batch_size = 100
        all_names_list = list(name_to_parts.keys())
        
        for i in range(0, len(all_names_list), batch_size):
            batch_names = all_names_list[i:i+batch_size]
            
            # Строим условия поиска
            name_conditions = models.Q()
            batch_name_to_parts = {}
            
            for name in batch_names:
                last, first, middle = name_to_parts[name]
                batch_name_to_parts[name] = (last, first, middle)
                
                if middle:
                    name_conditions |= models.Q(
                        last_name=last, 
                        first_name=first, 
                        middle_name=middle
                    )
                else:
                    name_conditions |= models.Q(
                        last_name=last, 
                        first_name=first
                    ) & (models.Q(middle_name='') | models.Q(middle_name__isnull=True))
            
            # Ищем людей
            for person in Person.objects.filter(name_conditions).only(
                'ceo_id', 'last_name', 'first_name', 'middle_name', 'ceo', 'slug'
            ):
                for name, (last, first, middle) in batch_name_to_parts.items():
                    if (person.last_name == last and 
                        person.first_name == first and 
                        (not middle or person.middle_name == middle)):
                        existing_persons[name] = person
                        self.person_cache[name] = person
                        found_count += 1
                        break
            
            if (i + len(batch_names)) % 500 == 0 or (i + len(batch_names)) >= len(all_names_list):
                self.stdout.write(f"         Обработано {i + len(batch_names)}/{len(all_names_list)} имен")
        
        self.stdout.write(f"      Найдено существующих: {found_count}")
        return existing_persons

    def _create_new_persons(self, new_names: List[str]) -> Dict[str, Person]:
        """
        Создание новых людей
        
        Returns:
            Словарь {имя: объект Person}
        """
        self.stdout.write(f"      Подготовка данных для создания...")
        
        # Получаем все существующие slugs
        existing_slugs = set(Person.objects.values_list('slug', flat=True))
        self.stdout.write(f"         Существующих slug-ов в БД: {len(existing_slugs)}")
        
        people_to_create = []
        
        for name in new_names:
            if pd.isna(name) or not name:
                continue
            
            name = str(name).strip()
            parts = name.split()
            
            if len(parts) >= 2:
                last_name = parts[0]
                first_name = parts[1]
                middle_name = parts[2] if len(parts) > 2 else ''
                
                # Формируем базовый slug
                name_parts_list = [last_name, first_name]
                if middle_name:
                    name_parts_list.append(middle_name)
                
                base_slug = slugify(' '.join(name_parts_list))
                if not base_slug:
                    base_slug = 'person'
                
                # Генерируем уникальный slug
                unique_slug, existing_slugs = self._generate_unique_slug(base_slug, existing_slugs)
                
                # Создаем объект без ID (ID будет назначен при bulk_create)
                person = Person(
                    ceo=name,
                    last_name=last_name,
                    first_name=first_name,
                    middle_name=middle_name or '',
                    slug=unique_slug
                )
                people_to_create.append(person)
        
        # Создаем людей
        return self._bulk_create_persons(people_to_create, len(new_names))

    def _generate_unique_slug(self, base_slug: str, existing_slugs: set) -> Tuple[str, set]:
        """
        Генерация уникального slug
        
        Returns:
            Tuple[уникальный_slug, обновленное_множество_slugs]
        """
        unique_slug = base_slug
        counter = 1
        while unique_slug in existing_slugs:
            unique_slug = f"{base_slug}-{counter}"
            counter += 1
        
        existing_slugs.add(unique_slug)
        return unique_slug, existing_slugs

    def _bulk_create_persons(self, people_to_create: List[Person], total_count: int) -> Dict[str, Person]:
        """
        Массовое создание людей с обработкой ошибок
        
        Returns:
            Словарь {имя: объект Person}
        """
        if not people_to_create:
            return {}
        
        self.stdout.write(f"      Создание людей пачками по 500...")
        
        BATCH_SIZE = 500
        created_count = 0
        created_map = {}
        
        for i in range(0, len(people_to_create), BATCH_SIZE):
            batch = people_to_create[i:i+BATCH_SIZE]
            
            # Получаем актуальный max_id перед каждой пачкой
            max_id = Person.objects.aggregate(models.Max('ceo_id'))['ceo_id__max'] or 0
            next_id = max_id + 1
            
            # Назначаем ID для текущей пачки
            for j, person in enumerate(batch):
                person.ceo_id = next_id + j
            
            # Фильтруем дубликаты в пачке
            batch = self._filter_duplicate_persons(batch)
            if not batch:
                continue
            
            # Пробуем создать пачкой
            try:
                Person.objects.bulk_create(batch, batch_size=BATCH_SIZE, ignore_conflicts=True)
                created_count += len(batch)
                self.stdout.write(self.style.SUCCESS(f"         ✅ Создана пачка из {len(batch)} человек"))
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"         Ошибка при создании пачки: {e}"))
                created_count += self._create_persons_one_by_one(batch)
            
            if created_count % 5000 == 0 or created_count >= total_count:
                percent = (created_count / total_count) * 100 if total_count > 0 else 0
                self.stdout.write(f"         Прогресс: {created_count}/{total_count} ({percent:.1f}%)")
        
        # Получаем созданных людей для маппинга
        if created_count > 0:
            created_names = [p.ceo for p in people_to_create[:created_count]]
            created_map = self._fetch_created_persons(created_names)
        
        return created_map

    def _filter_duplicate_persons(self, batch: List[Person]) -> List[Person]:
        """
        Фильтрация дубликатов в пачке по ceo_id и slug
        """
        batch_ceo_ids = [p.ceo_id for p in batch]
        batch_slugs = [p.slug for p in batch]
        
        existing_by_ceo = set(Person.objects.filter(ceo_id__in=batch_ceo_ids).values_list('ceo_id', flat=True))
        existing_by_slug = set(Person.objects.filter(slug__in=batch_slugs).values_list('slug', flat=True))
        
        if existing_by_ceo or existing_by_slug:
            self.stdout.write(self.style.WARNING(f"         Найдены дубликаты в пачке:"))
            if existing_by_ceo:
                self.stdout.write(self.style.WARNING(f"            по ceo_id: {list(existing_by_ceo)[:5]}..."))
            if existing_by_slug:
                self.stdout.write(self.style.WARNING(f"            по slug: {list(existing_by_slug)[:5]}..."))
            
            batch = [p for p in batch 
                    if p.ceo_id not in existing_by_ceo 
                    and p.slug not in existing_by_slug]
        
        return batch

    def _create_persons_one_by_one(self, batch: List[Person]) -> int:
        """
        Создание людей по одному в случае ошибки пачки
        """
        created = 0
        for person in batch:
            for attempt in range(10):
                try:
                    # Получаем свежий max_id перед каждой попыткой
                    current_max = Person.objects.aggregate(models.Max('ceo_id'))['ceo_id__max'] or 0
                    person.ceo_id = current_max + 1
                    
                    # Проверяем и обновляем slug при необходимости
                    if Person.objects.filter(slug=person.slug).exists():
                        base_slug = person.slug.split('-')[0]
                        counter = 1
                        new_slug = f"{base_slug}-{counter}"
                        while Person.objects.filter(slug=new_slug).exists():
                            counter += 1
                            new_slug = f"{base_slug}-{counter}"
                        person.slug = new_slug
                    
                    person.save()
                    created += 1
                    self.stdout.write(self.style.SUCCESS(f"            ✅ Создан: {person.ceo}"))
                    break
                except Exception as e:
                    if attempt == 9:
                        self.stdout.write(self.style.ERROR(f"            ❌ Не удалось создать {person.ceo}: {e}"))
                    continue
        return created

    def _fetch_created_persons(self, names: List[str]) -> Dict[str, Person]:
        """
        Получение созданных людей из БД для маппинга
        """
        person_map = {}
        for batch in batch_iterator(names, 1000):
            for person in Person.objects.filter(ceo__in=batch).only('ceo_id', 'ceo', 'slug'):
                person_map[person.ceo] = person
                self.person_cache[person.ceo] = person
        return person_map

    # =========================================================================
    # МЕТОДЫ ДЛЯ МАССОВОГО СОЗДАНИЯ ОРГАНИЗАЦИЙ
    # =========================================================================

    def _create_organizations_bulk(self, orgs_df: pd.DataFrame) -> Dict[str, Organization]:
        """
        Пакетное создание организаций из DataFrame с индикацией прогресса
        
        Args:
            orgs_df: DataFrame с колонкой 'entity_name'
            
        Returns:
            Словарь {название: объект Organization}
        """
        org_map = {}
        
        if orgs_df.empty:
            self.stdout.write("      Нет организаций для обработки")
            return org_map
        
        all_names = orgs_df['entity_name'].tolist()
        total_names = len(all_names)
        
        self.stdout.write(f"      Всего уникальных организаций для обработки: {total_names}")
        
        # ШАГ 1: Поиск существующих организаций
        self.stdout.write(f"      Поиск существующих организаций в БД...")
        
        existing_orgs = self._find_existing_organizations(all_names)
        
        # ШАГ 2: Определяем новые организации
        new_names = [name for name in all_names if name not in existing_orgs]
        new_count = len(new_names)
        
        self.stdout.write(f"      Новых организаций для создания: {new_count}")
        
        # ШАГ 3: Создаем новые организации
        if new_names:
            new_orgs_map = self._create_new_organizations(new_names)
            org_map.update(new_orgs_map)
        
        # ШАГ 4: Добавляем существующие организации
        org_map.update(existing_orgs)
        
        self.stdout.write(f"      ✅ Обработано организаций: {len(org_map)}")
        
        return org_map

    def _find_existing_organizations(self, names: List[str]) -> Dict[str, Organization]:
        """
        Поиск существующих организаций в БД
        """
        existing_orgs = {}
        batch_size = 100
        
        for i in range(0, len(names), batch_size):
            batch_names = names[i:i+batch_size]
            
            for org in Organization.objects.filter(name__in=batch_names).only('organization_id', 'name', 'slug'):
                existing_orgs[org.name] = org
                self.organization_cache[org.name] = org
            
            if (i + len(batch_names)) % 500 == 0 or (i + len(batch_names)) >= len(names):
                self.stdout.write(f"         Обработано {i + len(batch_names)}/{len(names)} названий")
        
        self.stdout.write(f"      Найдено существующих: {len(existing_orgs)}")
        return existing_orgs

    def _create_new_organizations(self, new_names: List[str]) -> Dict[str, Organization]:
        """
        Создание новых организаций
        """
        self.stdout.write(f"      Подготовка данных для создания...")
        
        max_id = Organization.objects.aggregate(models.Max('organization_id'))['organization_id__max'] or 0
        
        # Получаем все существующие slugs
        existing_slugs = set(Organization.objects.values_list('slug', flat=True))
        self.stdout.write(f"      Всего существующих slug: {len(existing_slugs)}")
        
        orgs_to_create = []
        used_slugs_in_batch = set()
        
        for name in new_names:
            base_slug = slugify(name[:50]) or 'organization'
            unique_slug = base_slug
            counter = 1
            
            # Проверяем И существующие slugs, И уже использованные в этом батче
            while unique_slug in existing_slugs or unique_slug in used_slugs_in_batch:
                unique_slug = f"{base_slug}-{counter}"
                counter += 1
            
            used_slugs_in_batch.add(unique_slug)
            existing_slugs.add(unique_slug)
            
            org = Organization(
                organization_id=max_id + len(orgs_to_create) + 1,
                name=name,
                full_name=name,
                short_name=name[:500] if len(name) > 500 else name,
                slug=unique_slug,
                register_opk=False,
                strategic=False,
            )
            orgs_to_create.append(org)
        
        # Создаем организации
        return self._bulk_create_organizations(orgs_to_create, len(new_names))

    def _bulk_create_organizations(self, orgs_to_create: List[Organization], total_count: int) -> Dict[str, Organization]:
        """
        Массовое создание организаций с обработкой ошибок
        """
        org_map = {}
        batch_size = 500
        created_count = 0
        
        for batch in batch_iterator(orgs_to_create, batch_size):
            try:
                # Пробуем создать пачкой с ignore_conflicts
                Organization.objects.bulk_create(batch, batch_size=batch_size, ignore_conflicts=True)
                created_count += len(batch)
            except Exception as e:
                self.stdout.write(f"         Ошибка при создании батча: {e}")
                # В случае ошибки создаем по одному
                for org in batch:
                    try:
                        org.save()
                        created_count += 1
                    except Exception as e2:
                        self.stdout.write(f"         Не удалось создать организацию {org.name}: {e2}")
            
            if created_count % 5000 == 0 or created_count == total_count:
                percent = (created_count / total_count) * 100 if total_count > 0 else 0
                self.stdout.write(f"         Создано {created_count}/{total_count} ({percent:.1f}%)")
        
        # Получаем созданные организации для маппинга
        if created_count > 0:
            created_names = [o.name for o in orgs_to_create[:created_count]]
            org_map = self._fetch_created_organizations(created_names)
        
        return org_map

    def _fetch_created_organizations(self, names: List[str]) -> Dict[str, Organization]:
        """
        Получение созданных организаций из БД для маппинга
        """
        org_map = {}
        for batch in batch_iterator(names, 1000):
            for org in Organization.objects.filter(name__in=batch).only('organization_id', 'name', 'slug'):
                org_map[org.name] = org
                self.organization_cache[org.name] = org
        return org_map

    # =========================================================================
    # МЕТОДЫ ДЛЯ РАБОТЫ СО СВЯЗЯМИ (ОБЩИЕ ДЛЯ ВСЕХ ПАРСЕРОВ)
    # =========================================================================

    def _process_relations_dataframe(self, relations_data: List[Dict], reg_to_ip: Dict):
        """
        Обработка всех связей через единый DataFrame
        Этот метод может быть переопределен в дочерних классах при необходимости
        """
        if not relations_data:
            self.stdout.write("   Нет данных для обработки связей")
            return

        self.stdout.write("   Создание DataFrame связей")
        df_relations = pd.DataFrame(relations_data)
        
        self.stdout.write(f"   Всего записей связей: {len(df_relations)}")
        self.stdout.write(f"   Уникальных регистрационных номеров: {df_relations['reg_number'].nunique()}")

        self.stdout.write("   Добавление ID объектов")
        df_relations['ip_id'] = df_relations['reg_number'].map(reg_to_ip)

        missing_ip = df_relations['ip_id'].isna().sum()
        if missing_ip > 0:
            self.stdout.write(self.style.WARNING(f"   ⚠️ Пропущено {missing_ip} связей с отсутствующими ID объектов"))
            df_relations = df_relations.dropna(subset=['ip_id']).copy()
        
        df_relations['ip_id'] = df_relations['ip_id'].astype(int)

        # Определение типов для правообладателей
        self.stdout.write("   Определение типов сущностей через Natasha")
        
        unique_entities = df_relations[['entity_name', 'entity_type']].drop_duplicates()
        holders_to_check = unique_entities[unique_entities['entity_type'].isna()]['entity_name'].tolist()

        if holders_to_check:
            self.stdout.write(f"   Определение типов для {len(holders_to_check)} правообладателей")
            entity_type_map = self.type_detector.detect_type_batch(holders_to_check)

            mask = df_relations['entity_type'].isna()
            df_relations.loc[mask, 'entity_type'] = \
                df_relations.loc[mask, 'entity_name'].map(entity_type_map)

        type_stats = df_relations['entity_type'].value_counts().to_dict()
        self.stdout.write(f"   Распределение типов: люди={type_stats.get('person', 0)}, "
                         f"организации={type_stats.get('organization', 0)}")

        # Группировка по сущностям
        unique_entities = df_relations[['entity_name', 'entity_type']].drop_duplicates()
        
        persons_df = unique_entities[unique_entities['entity_type'] == 'person']
        orgs_df = unique_entities[unique_entities['entity_type'] == 'organization']

        person_map = {}
        if not persons_df.empty:
            self.stdout.write(f"   Обработка {len(persons_df)} уникальных людей")
            person_map = self._create_persons_bulk(persons_df)

        org_map = {}
        if not orgs_df.empty:
            self.stdout.write(f"   Обработка {len(orgs_df)} уникальных организаций")
            org_map = self._create_organizations_bulk(orgs_df)

        # Подготовка связей
        self.stdout.write("   Подготовка связей для вставки в БД")

        authors_df = df_relations[df_relations['relation_type'] == 'author'].copy()
        holders_df = df_relations[df_relations['relation_type'] == 'holder'].copy()

        # Авторы
        author_relations = self._prepare_author_relations(authors_df, person_map)
        
        # Правообладатели (люди и организации)
        holder_person_relations, holder_org_relations = self._prepare_holder_relations(
            holders_df, person_map, org_map
        )

        # Создание связей
        self._create_all_relations(author_relations, holder_person_relations, holder_org_relations)

        self.stdout.write(self.style.SUCCESS("   ✅ Обработка всех связей завершена"))

    def _prepare_author_relations(self, authors_df: pd.DataFrame, person_map: Dict) -> List[Tuple[int, int]]:
        """Подготовка связей авторов"""
        if authors_df.empty:
            return []
        
        person_id_map = {name: p.ceo_id for name, p in person_map.items()}
        authors_df['person_id'] = authors_df['entity_name'].map(person_id_map)
        authors_df = authors_df.dropna(subset=['person_id'])
        authors_df['person_id'] = authors_df['person_id'].astype(int)
        
        authors_unique = authors_df[['ip_id', 'person_id']].drop_duplicates()
        relations = [(row['ip_id'], row['person_id']) for _, row in authors_unique.iterrows()]
        
        self.stdout.write(f"   Подготовлено {len(relations)} уникальных связей авторов")
        return relations

    def _prepare_holder_relations(self, holders_df: pd.DataFrame, person_map: Dict, org_map: Dict) -> Tuple[List[Tuple[int, int]], List[Tuple[int, int]]]:
        """Подготовка связей правообладателей"""
        person_relations = []
        org_relations = []

        if holders_df.empty:
            return person_relations, org_relations

        # Правообладатели-люди
        holders_persons = holders_df[holders_df['entity_type'] == 'person'].copy()
        if not holders_persons.empty:
            person_id_map = {name: p.ceo_id for name, p in person_map.items()}
            holders_persons['person_id'] = holders_persons['entity_name'].map(person_id_map)
            holders_persons = holders_persons.dropna(subset=['person_id'])
            holders_persons['person_id'] = holders_persons['person_id'].astype(int)
            
            holders_persons_unique = holders_persons[['ip_id', 'person_id']].drop_duplicates()
            person_relations = [(row['ip_id'], row['person_id']) for _, row in holders_persons_unique.iterrows()]
            self.stdout.write(f"   Подготовлено {len(person_relations)} связей правообладателей-людей")

        # Правообладатели-организации
        holders_orgs = holders_df[holders_df['entity_type'] == 'organization'].copy()
        if not holders_orgs.empty:
            org_id_map = {name: o.organization_id for name, o in org_map.items()}
            holders_orgs['org_id'] = holders_orgs['entity_name'].map(org_id_map)
            holders_orgs = holders_orgs.dropna(subset=['org_id'])
            holders_orgs['org_id'] = holders_orgs['org_id'].astype(int)
            
            holders_orgs_unique = holders_orgs[['ip_id', 'org_id']].drop_duplicates()
            org_relations = [(row['ip_id'], row['org_id']) for _, row in holders_orgs_unique.iterrows()]
            self.stdout.write(f"   Подготовлено {len(org_relations)} связей правообладателей-организаций")

        return person_relations, org_relations

    def _create_all_relations(self, author_relations: List[Tuple[int, int]], 
                             holder_person_relations: List[Tuple[int, int]], 
                             holder_org_relations: List[Tuple[int, int]]):
        """Создание всех типов связей"""
        if author_relations:
            self.stdout.write("   Создание связей авторов")
            ip_ids = list(set(ip_id for ip_id, _ in author_relations))
            with tqdm(total=len(ip_ids), desc="   Удаление старых связей авторов", unit="ip") as pbar:
                self._delete_author_relations(ip_ids, pbar)
            
            with tqdm(total=len(author_relations), desc="   Создание новых связей авторов", unit="св") as pbar:
                self._create_author_relations(author_relations, pbar)

        if holder_person_relations:
            self.stdout.write("   Создание связей правообладателей (люди)")
            ip_ids = list(set(ip_id for ip_id, _ in holder_person_relations))
            with tqdm(total=len(ip_ids), desc="   Удаление старых связей", unit="ip") as pbar:
                self._delete_holder_person_relations(ip_ids, pbar)
            
            with tqdm(total=len(holder_person_relations), desc="   Создание новых связей", unit="св") as pbar:
                self._create_holder_person_relations(holder_person_relations, pbar)

        if holder_org_relations:
            self.stdout.write("   Создание связей правообладателей (организации)")
            ip_ids = list(set(ip_id for ip_id, _ in holder_org_relations))
            with tqdm(total=len(ip_ids), desc="   Удаление старых связей", unit="ip") as pbar:
                self._delete_holder_org_relations(ip_ids, pbar)
            
            with tqdm(total=len(holder_org_relations), desc="   Создание новых связей", unit="св") as pbar:
                self._create_holder_org_relations(holder_org_relations, pbar)

    # Методы для удаления связей
    def _delete_author_relations(self, ip_ids: List[int], pbar):
        """Удаление связей авторов"""
        delete_batch_size = 500
        for i in range(0, len(ip_ids), delete_batch_size):
            batch_ids = ip_ids[i:i+delete_batch_size]
            IPObject.authors.through.objects.filter(
                ipobject_id__in=batch_ids
            ).delete()
            pbar.update(len(batch_ids))

    def _delete_holder_person_relations(self, ip_ids: List[int], pbar):
        """Удаление связей правообладателей-людей"""
        delete_batch_size = 500
        for i in range(0, len(ip_ids), delete_batch_size):
            batch_ids = ip_ids[i:i+delete_batch_size]
            IPObject.owner_persons.through.objects.filter(
                ipobject_id__in=batch_ids
            ).delete()
            pbar.update(len(batch_ids))

    def _delete_holder_org_relations(self, ip_ids: List[int], pbar):
        """Удаление связей правообладателей-организаций"""
        delete_batch_size = 500
        for i in range(0, len(ip_ids), delete_batch_size):
            batch_ids = ip_ids[i:i+delete_batch_size]
            IPObject.owner_organizations.through.objects.filter(
                ipobject_id__in=batch_ids
            ).delete()
            pbar.update(len(batch_ids))

    # Методы для создания связей
    def _create_author_relations(self, relations: List[Tuple[int, int]], pbar):
        """Создание связей авторов"""
        create_batch_size = 2000
        for batch in batch_iterator(relations, create_batch_size):
            through_objs = [
                IPObject.authors.through(
                    ipobject_id=ip_id,
                    person_id=person_id
                )
                for ip_id, person_id in batch
            ]
            IPObject.authors.through.objects.bulk_create(
                through_objs, batch_size=2000, ignore_conflicts=True
            )
            pbar.update(len(batch))

    def _create_holder_person_relations(self, relations: List[Tuple[int, int]], pbar):
        """Создание связей правообладателей-людей"""
        create_batch_size = 2000
        for batch in batch_iterator(relations, create_batch_size):
            through_objs = [
                IPObject.owner_persons.through(
                    ipobject_id=ip_id,
                    person_id=person_id
                )
                for ip_id, person_id in batch
            ]
            IPObject.owner_persons.through.objects.bulk_create(
                through_objs, batch_size=2000, ignore_conflicts=True
            )
            pbar.update(len(batch))

    def _create_holder_org_relations(self, relations: List[Tuple[int, int]], pbar):
        """Создание связей правообладателей-организаций"""
        create_batch_size = 2000
        for batch in batch_iterator(relations, create_batch_size):
            through_objs = [
                IPObject.owner_organizations.through(
                    ipobject_id=ip_id,
                    organization_id=org_id
                )
                for ip_id, org_id in batch
            ]
            IPObject.owner_organizations.through.objects.bulk_create(
                through_objs, batch_size=2000, ignore_conflicts=True
            )
            pbar.update(len(batch))