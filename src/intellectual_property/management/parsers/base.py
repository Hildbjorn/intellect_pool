"""
Базовый класс для всех парсеров каталогов ФИПС
"""

import logging
import re
from datetime import datetime
from typing import Optional, List, Dict, Any
import gc

from django.db import models
from django.utils.text import slugify
import pandas as pd

from intellectual_property.models import IPObject, IPType
from core.models import Person, Organization, Country

# ИСПРАВЛЕНО: импортируем процессоры из текущего пакета (.processors)
from .processors import (
    RussianTextProcessor,
    OrganizationNormalizer,
    PersonNameFormatter,
    RIDNameFormatter,
    EntityTypeDetector
)

# ИСПРАВЛЕНО: импортируем утилиты из родительского пакета (..utils)
from ..utils.progress import ProgressManager, batch_iterator

logger = logging.getLogger(__name__)


class BaseFIPSParser:
    """Базовый класс для всех парсеров каталогов ФИПС"""

    def __init__(self, command):
        self.command = command
        self.stdout = command.stdout
        self.style = command.style

        # Инициализация менеджера прогресса
        self.progress = ProgressManager(file=self.stdout)

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
            self.progress.warning(f"Ошибка поиска страны {code}: {e}")
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
            self.progress.warning(f"Ошибка создания Person: {e}")
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
            self.progress.warning(f"Ошибка создания Organization: {e}")
            return None
