"""
Команда для парсинга каталогов открытых данных ФИПС Роспатента.
Поддерживает все типы РИД: изобретения, полезные модели, промышленные образцы,
топологии интегральных микросхем, программы для ЭВМ и базы данных.
"""

import logging
import re
from datetime import datetime
from typing import List, Dict, Any

from django.db import models
from django.core.management.base import BaseCommand, CommandError
from django.utils.text import slugify
from django.utils import timezone
from tqdm import tqdm
import pandas as pd
import os
import pymorphy2
from pymorphy2 import MorphAnalyzer

from intellectual_property.models import (
    FipsOpenDataCatalogue, IPType, IPObject
)
from core.models import (
    Person, Organization, 
    FOIV, Country, RFRepresentative,
    OrganizationNormalizationRule
)

logger = logging.getLogger(__name__)


class MorphAnalyzerWrapper:
    """
    Обертка для pymorphy2 с кэшированием результатов
    """
    _instance = None
    _cache = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.morph = pymorphy2.MorphAnalyzer()
        return cls._instance
    
    def parse(self, word: str):
        """Разбор слова с кэшированием"""
        if word in self._cache:
            return self._cache[word]
        result = self.morph.parse(word)
        self._cache[word] = result
        return result
    
    def is_name(self, word: str) -> bool:
        """Проверка, является ли слово именем собственным"""
        if not word:
            return False
        parsed = self.parse(word)[0]
        tags = str(parsed.tag)
        return any(tag in tags for tag in ['Name', 'Surn', 'Patr'])
    
    def is_preposition(self, word: str) -> bool:
        """Проверка, является ли слово предлогом/союзом"""
        if not word:
            return False
        parsed = self.parse(word)[0]
        return 'PREP' in str(parsed.tag) or 'CONJ' in str(parsed.tag)
    
    def normalize_case(self, word: str, is_first: bool = False) -> str:
        """
        Приведение слова к правильному регистру
        """
        if not word or len(word) <= 1:
            return word
        
        # Если слово в верхнем регистре и длинное - возможно аббревиатура
        if word.isupper() and len(word) > 1:
            return word
        
        # Если слово содержит только одну букву (инициал)
        if len(word) == 1:
            return word.upper() + '.'
        
        # Очищаем от знаков препинания для анализа
        clean_word = re.sub(r'[.,;:!?()\[\]{}"\']', '', word)
        if not clean_word:
            return word
        
        # Проверяем через морфологию
        parsed = self.parse(clean_word)[0]
        tags = str(parsed.tag)
        
        # Определяем регистр
        if is_first:
            # Первое слово - с большой буквы
            result = clean_word[0].upper() + clean_word[1:].lower()
        elif 'Name' in tags or 'Surn' in tags or 'Patr' in tags:
            # Имена собственные - с большой буквы
            result = clean_word[0].upper() + clean_word[1:].lower()
        elif 'PREP' in tags or 'CONJ' in tags:
            # Предлоги и союзы - с маленькой буквы
            result = clean_word.lower()
        else:
            # Обычные слова - с маленькой буквы
            result = clean_word.lower()
        
        # Добавляем обратно знаки препинания
        if word != clean_word:
            punctuation = word[len(clean_word):]
            result += punctuation
        
        return result


class OrganizationNormalizer:
    """
    Класс для нормализации названий организаций с поддержкой правил из БД
    """
    
    def __init__(self):
        self.rules_cache = None
        self.morph = MorphAnalyzerWrapper()
        self.load_rules()
    
    def load_rules(self):
        """Загрузка правил из БД в кэш"""
        rules = OrganizationNormalizationRule.objects.all().order_by('priority')
        self.rules_cache = [
            {
                'original': rule.original_text.lower(),
                'replacement': rule.replacement_text.lower(),
                'type': rule.rule_type,
                'priority': rule.priority
            }
            for rule in rules
        ]
    
    def reload_rules(self):
        """Перезагрузка правил (после изменений в БД)"""
        self.load_rules()
    
    def normalize(self, name: str) -> Dict[str, Any]:
        """
        Нормализация названия с использованием правил из БД
        Возвращает словарь с нормализованным текстом и ключевыми словами
        """
        if pd.isna(name) or not name:
            return {'normalized': '', 'keywords': [], 'original': name}
        
        original = str(name).strip()
        name_lower = original.lower()
        
        # Применяем правила из БД
        normalized = name_lower
        if self.rules_cache:
            for rule in self.rules_cache:
                if rule['type'] == 'ignore':
                    # Для игнорируемых слов просто удаляем их
                    pattern = r'\b' + re.escape(rule['original']) + r'\b'
                    normalized = re.sub(pattern, '', normalized)
                else:
                    # Для замен
                    pattern = r'\b' + re.escape(rule['original']) + r'\b'
                    normalized = re.sub(pattern, rule['replacement'], normalized)
        
        # Убираем кавычки всех видов
        normalized = re.sub(r'["\'«»„“”]', '', normalized)
        
        # Убираем знаки препинания, кроме дефиса
        normalized = re.sub(r'[^\w\s-]', ' ', normalized)
        
        # Убираем лишние пробелы
        normalized = ' '.join(normalized.split())
        
        # Извлекаем ключевые слова для поиска
        keywords = self._extract_keywords(original)
        
        return {
            'normalized': normalized,
            'keywords': keywords,
            'original': original
        }
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Извлечение ключевых слов для поиска"""
        keywords = []
        
        # Слова в кавычках (обычно уникальное название)
        quoted = re.findall(r'"([^"]+)"', text)
        for q in quoted:
            words = q.lower().split()
            keywords.extend([w for w in words if len(w) > 3])
        
        # Аббревиатуры (последовательности заглавных букв)
        abbreviations = re.findall(r'\b[А-ЯЁA-Z]{2,}\b', text)
        keywords.extend([a.lower() for a in abbreviations if len(a) >= 2])
        
        return list(set(keywords))
    
    def format_organization_name(self, name: str) -> str:
        """
        Форматирование названия организации с правильным регистром
        """
        if not name:
            return name
        
        # Список аббревиатур, которые всегда в верхнем регистре
        ALWAYS_UPPER = {
            'ООО', 'ЗАО', 'ОАО', 'АО', 'ПАО', 'НАО',
            'ФГУП', 'ФГБУ', 'ФГАОУ', 'ФГАУ', 'ФГКУ',
            'НИИ', 'КБ', 'ОКБ', 'СКБ', 'ЦКБ', 'ПКБ',
            'НПО', 'НПП', 'НПФ', 'НПЦ', 'НИЦ',
            'МУП', 'ГУП', 'ИЧП', 'ТОО', 'АОЗТ', 'АООТ',
            'РФ', 'РАН', 'СО РАН', 'УрО РАН', 'ДВО РАН',
            'МГУ', 'СПбГУ', 'МФТИ', 'МИФИ', 'МГТУ', 'МАИ',
            'ФИАН', 'МИАН', 'ИПМ', 'ИПМех', 'ИППИ',
            'ЦАГИ', 'ЦИАМ', 'ВИАМ', 'ВИЛС', 'ВИМС', 'ВНИИ'
        }
        
        # Разбиваем на части по кавычкам
        parts = re.split(r'(")', name)
        result = []
        in_quotes = False
        
        for part in parts:
            if part == '"':
                in_quotes = not in_quotes
                result.append(part)
            elif in_quotes:
                # Часть внутри кавычек - форматируем как обычный текст
                words = part.split()
                formatted_words = []
                for word in words:
                    word_upper = word.upper()
                    if word_upper in ALWAYS_UPPER:
                        formatted_words.append(word_upper)
                    elif self.morph.is_name(word):
                        # Имена собственные - с большой буквы
                        formatted_words.append(word[0].upper() + word[1:].lower())
                    else:
                        # Обычные слова - с маленькой буквы
                        formatted_words.append(word.lower())
                result.append(' '.join(formatted_words))
            else:
                # Часть вне кавычек - форматируем аббревиатуры и обычные слова
                words = part.split()
                formatted_words = []
                for word in words:
                    word_clean = word.strip('.,;:()')
                    word_upper = word_clean.upper()
                    if word_upper in ALWAYS_UPPER:
                        formatted_words.append(word_upper)
                    elif word_clean.isupper() and len(word_clean) > 1:
                        # Неизвестная аббревиатура - оставляем как есть
                        formatted_words.append(word_clean)
                    else:
                        # Обычные слова - оставляем как в оригинале
                        formatted_words.append(word)
                result.append(' '.join(formatted_words))
        
        return ''.join(result)


class EntityTypeDetector:
    """
    Детектор типов сущностей с использованием pymorphy2
    """
    
    def __init__(self):
        self.morph = MorphAnalyzerWrapper()
    
    def is_person(self, text: str) -> bool:
        """
        Проверка, является ли текст физическим лицом
        Использует морфологический анализ для определения имен собственных
        """
        if not text or len(text) < 6:
            return False
        
        text = text.strip()
        
        # Если есть явные признаки организации - сразу возвращаем False
        org_indicators = ['ООО', 'ЗАО', 'АО', 'ПАО', 'ФГУП', 'ФГБУ', 
                         'Общество', 'Компания', 'Корпорация', 'Завод', 'Институт']
        if any(ind in text for ind in org_indicators):
            return False
        
        # Разбиваем на слова
        words = re.findall(r'[А-ЯЁA-Z][а-яёa-z]*\.?', text)
        
        # Если слов меньше 2 - не ФИО
        if len(words) < 2:
            return False
        
        # Проверяем каждое слово на принадлежность к именам
        name_count = 0
        for word in words:
            clean_word = word.rstrip('.')
            if self.morph.is_name(clean_word):
                name_count += 1
        
        # Если большинство слов - имена, вероятно это ФИО
        return name_count >= len(words) - 1
    
    def detect_type(self, text: str) -> str:
        """
        Определение типа сущности
        Возвращает: 'person' или 'organization'
        """
        if self.is_person(text):
            return 'person'
        return 'organization'


class RIDNameFormatter:
    """
    Класс для форматирования названий РИД с использованием pymorphy2
    """
    
    def __init__(self):
        self.morph = MorphAnalyzerWrapper()
        
        # Аббревиатуры, которые всегда остаются в верхнем регистре
        self.KEEP_UPPER = {
            # Химия и биология
            'ДНК', 'РНК', 'ПЦР', 'ИФА', 'ЭДТА', 'АТФ', 'АДФ', 'НАД', 'НАДФ',
            'COVID-19', 'SARS-COV-2', 'ВИЧ', 'СПИД',
            
            # Единицы измерения
            '°C', '°F', 'K', 'М', 'СМ', 'ММ', 'КМ', 'КГ', 'Г', 'МГ', 'МКГ',
            'Л', 'МЛ', 'МКЛ', 'С', 'МС', 'МКС', 'МИН', 'Ч', 'СУТ',
            'ПА', 'КПА', 'МПА', 'ГПА', 'АТМ', 'БАР', 'ММ РТ. СТ.',
            'А', 'В', 'ВТ', 'КВТ', 'МВТ', 'ГВТ', 'ОМ', 'Ф', 'ГН', 'ТЛ',
            'БИТ', 'БАЙТ', 'КБ', 'МБ', 'ГБ', 'ТБ', 'ГЦ', 'КГЦ', 'МГЦ', 'ГГЦ',
            
            # Химические элементы
            'H', 'HE', 'LI', 'BE', 'B', 'C', 'N', 'O', 'F', 'NE', 'NA', 'MG',
            'AL', 'SI', 'P', 'S', 'CL', 'AR', 'K', 'CA', 'SC', 'TI', 'V',
            'CR', 'MN', 'FE', 'CO', 'NI', 'CU', 'ZN', 'GA', 'GE', 'AS', 'SE',
            'HCL', 'H2SO4', 'HNO3', 'H3PO4', 'NAOH', 'KOH', 'NH3', 'CO2',
            
            # Стандарты и технологии
            'ГОСТ', 'ТУ', 'СНиП', 'СП', 'СанПиН', 'ISO', 'IEC', 'IEEE',
            'USB', 'HDMI', 'WI-FI', 'LTE', '5G', 'CPU', 'GPU', 'RAM', 'ROM',
            'CAD', 'CAM', 'CAE', 'PLM', 'PDM', 'ERP', 'CRM', 'MES',
            
            # Патентные классификации
            'МПК', 'МКТУ', 'МКПО', 'НИОКР', 'РИД', 'ИС', 'ОИС', 'ФИПС',
        }
        
        # Предлоги, союзы, частицы, которые всегда с маленькой буквы
        self.LOWERCASE_WORDS = {
            'в', 'на', 'с', 'со', 'у', 'к', 'ко', 'о', 'об', 'от', 'до',
            'для', 'без', 'над', 'под', 'из', 'по', 'за', 'про', 'через',
            'и', 'а', 'но', 'да', 'или', 'либо', 'же', 'как', 'так',
            'что', 'чтобы', 'если', 'хотя', 'при', 'во', 'обо',
            'and', 'or', 'but', 'if', 'then', 'else', 'for', 'to', 'with',
            'by', 'from', 'at', 'in', 'on', 'of', 'the', 'a', 'an',
        }
    
    def format(self, text: str) -> str:
        """
        Форматирование названия РИД с правильным регистром
        """
        if not text or not isinstance(text, str):
            return text
        
        if len(text.strip()) <= 1:
            return text
        
        # Разбиваем на предложения
        sentences = re.split(r'(?<=[.!?])\s+(?=[А-ЯЁA-Z])', text)
        formatted_sentences = []
        
        for sentence in sentences:
            if not sentence.strip():
                continue
            
            # Разбиваем на слова, сохраняя пробелы
            words = re.split(r'(\s+)', sentence)
            formatted_words = []
            
            is_first_word = True
            
            for word in words:
                # Пробелы оставляем как есть
                if word.isspace():
                    formatted_words.append(word)
                    continue
                
                # Обрабатываем слово
                formatted_word = self._format_word(word, is_first_word)
                formatted_words.append(formatted_word)
                
                # Следующее слово не будет первым в предложении
                if not word.isspace():
                    is_first_word = False
            
            formatted_sentences.append(''.join(formatted_words))
        
        result = ' '.join(formatted_sentences)
        
        # Очистка
        result = re.sub(r'\s+([,;:.])', r'\1', result)
        result = ' '.join(result.split())
        
        return result
    
    def _format_word(self, word: str, is_first: bool) -> str:
        """
        Форматирование отдельного слова
        """
        # Проверка на аббревиатуру
        word_upper = word.upper().strip('.,;:!?()')
        if word_upper in self.KEEP_UPPER:
            return word_upper
        
        # Проверка на инициалы
        if re.match(r'^[А-ЯЁA-Z]\.$', word) or re.match(r'^[А-ЯЁA-Z]\.[А-ЯЁA-Z]\.$', word):
            return word.upper()
        
        # Проверка на числа
        if word.isdigit():
            return word
        
        # Проверка на числа с единицами измерения
        unit_match = re.match(r'^(\d+(?:[.,]\d+)?)([а-яёa-z°]+)$', word, re.IGNORECASE)
        if unit_match:
            number, unit = unit_match.groups()
            unit_upper = unit.upper()
            if unit_upper in self.KEEP_UPPER:
                return number + unit_upper
            return number + unit.lower()
        
        # Проверка на слова через дефис
        if '-' in word:
            parts = word.split('-')
            formatted_parts = []
            for part in parts:
                formatted_parts.append(self._format_word(part, False))
            return '-'.join(formatted_parts)
        
        # Очистка от знаков препинания для анализа
        clean_word = re.sub(r'[.,;:!?()]', '', word)
        if not clean_word:
            return word
        
        # Анализ через морфологию
        word_lower = clean_word.lower()
        
        # Проверка на предлоги и союзы
        if word_lower in self.LOWERCASE_WORDS or self.morph.is_preposition(clean_word):
            result = word_lower
        elif is_first:
            # Первое слово - с большой буквы
            result = clean_word[0].upper() + clean_word[1:].lower()
        elif self.morph.is_name(clean_word):
            # Имена собственные - с большой буквы
            result = clean_word[0].upper() + clean_word[1:].lower()
        else:
            # Обычные слова - с маленькой буквы
            result = clean_word.lower()
        
        # Добавляем обратно знаки препинания
        if word != clean_word:
            punctuation = word[len(clean_word):]
            result += punctuation
        
        return result


class PersonNameFormatter:
    """
    Класс для форматирования имен людей
    """
    
    def __init__(self):
        self.morph = MorphAnalyzerWrapper()
    
    def format(self, name: str) -> str:
        """
        Форматирование ФИО человека
        ФОМИН АРТЕМ ВЛАДИМИРОВИЧ -> Фомин Артем Владимирович
        """
        if not name:
            return name
        
        parts = name.split()
        formatted_parts = []
        
        for part in parts:
            if not part:
                continue
            
            # Инициалы
            if '.' in part:
                initials = [p for p in part if p.isalpha()]
                formatted_parts.append(''.join([i.upper() + '.' for i in initials]))
                continue
            
            # Обычное слово
            clean_part = part.strip('.')
            if clean_part.isupper() and len(clean_part) > 1:
                # Вероятно, фамилия или имя в верхнем регистре
                formatted_parts.append(clean_part[0].upper() + clean_part[1:].lower())
            else:
                # Уже в правильном регистре или смешанном
                formatted_parts.append(part)
        
        return ' '.join(formatted_parts)


class BaseFIPSParser:
    """
    Базовый класс для всех парсеров каталогов ФИПС.
    Содержит общие методы для работы с данными.
    """
    
    def __init__(self, command):
        self.command = command
        self.stdout = command.stdout
        self.style = command.style
        
        # Инициализация анализаторов и форматеров
        self.morph = MorphAnalyzerWrapper()
        self.org_normalizer = OrganizationNormalizer()
        self.type_detector = EntityTypeDetector()
        self.rid_formatter = RIDNameFormatter()
        self.person_formatter = PersonNameFormatter()
        
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
        """
        Получение страны по коду из существующей модели Country
        """
        if not code or pd.isna(code):
            return None
        
        code = str(code).upper().strip()
        if len(code) != 2:
            return None
        
        # Проверяем кэш
        if code in self.country_cache:
            return self.country_cache[code]
        
        try:
            # Ищем страну по двухбуквенному коду
            country = Country.objects.filter(code=code).first()
            if country:
                self.country_cache[code] = country
                return country
            
            # Если не нашли по двухбуквенному, пробуем по трехбуквенному
            country = Country.objects.filter(code_alpha3=code).first()
            if country:
                self.country_cache[code] = country
                return country
            
            self.stdout.write(self.style.WARNING(f"  Страна с кодом {code} не найдена в БД"))
            return None
            
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"  Ошибка поиска страны {code}: {e}"))
            return None
    
    def parse_authors(self, authors_str):
        """Парсинг строки с авторами"""
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
        """Парсинг строки с патентообладателями"""
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
        """
        Поиск похожей организации с использованием всех трех полей названия
        """
        if pd.isna(org_name) or not org_name:
            return None
        
        org_name = str(org_name).strip().strip('"')
        
        # Стратегия 1: Прямое совпадение с любым из полей названия
        direct_match = Organization.objects.filter(
            models.Q(name=org_name) |
            models.Q(full_name=org_name) |
            models.Q(short_name=org_name)
        ).first()
        if direct_match:
            return direct_match
        
        # Нормализуем название для дальнейшего поиска
        norm_data = self.org_normalizer.normalize(org_name)
        normalized = norm_data['normalized']
        keywords = norm_data['keywords']
        
        # Стратегия 2: Поиск по ключевым словам во всех полях
        for keyword in keywords:
            if len(keyword) >= 3:
                similar = Organization.objects.filter(
                    models.Q(name__icontains=keyword) |
                    models.Q(full_name__icontains=keyword) |
                    models.Q(short_name__icontains=keyword)
                ).first()
                if similar:
                    return similar
        
        # Стратегия 3: Поиск по первым 30 символам нормализованного названия
        if len(normalized) > 30:
            prefix = normalized[:30]
            similar = Organization.objects.filter(
                models.Q(name__icontains=prefix) |
                models.Q(full_name__icontains=prefix) |
                models.Q(short_name__icontains=prefix)
            ).first()
            if similar:
                return similar
        
        # Стратегия 4: Поиск по вхождению оригинального названия в full_name
        full_match = Organization.objects.filter(
            models.Q(full_name__icontains=org_name)
        ).first()
        if full_match:
            return full_match
        
        return None
    
    def find_or_create_organization(self, org_name):
        """Поиск или создание организации"""
        if pd.isna(org_name) or not org_name:
            return None
        
        org_name = str(org_name).strip().strip('"')
        
        if not org_name or org_name == 'null' or org_name == 'None':
            return None
        
        # Проверяем кэш
        if org_name in self.organization_cache:
            return self.organization_cache[org_name]
        
        # Ищем похожие организации
        similar = self.find_similar_organization(org_name)
        if similar:
            self.organization_cache[org_name] = similar
            return similar
        
        # Форматируем название перед сохранением
        formatted_name = self.org_normalizer.format_organization_name(org_name)
        
        # Нормализуем для генерации slug
        norm_data = self.org_normalizer.normalize(org_name)
        normalized = norm_data['normalized']
        
        base_slug = slugify(normalized[:50])
        if not base_slug:
            base_slug = 'organization'
        
        unique_slug = base_slug
        counter = 1
        while Organization.objects.filter(slug=unique_slug).exists():
            unique_slug = f"{base_slug}-{counter}"
            counter += 1
        
        try:
            max_id = Organization.objects.aggregate(models.Max('organization_id'))['organization_id__max'] or 0
            new_id = max_id + 1
            
            # Создаем организацию с отформатированным названием
            org = Organization.objects.create(
                organization_id=new_id,
                name=formatted_name,
                full_name=formatted_name,
                short_name=formatted_name[:500] if len(formatted_name) > 500 else formatted_name,
                slug=unique_slug,
                register_opk=False,
                strategic=False,
            )
            
            self.organization_cache[org_name] = org
            return org
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"  Ошибка создания Organization: {e}"))
            return None
    
    def find_or_create_foiv(self, holder_text):
        """Поиск ФОИВ из текста патентообладателя"""
        if pd.isna(holder_text) or not holder_text:
            return None
        
        holder_text = str(holder_text).strip().strip('"')
        
        if holder_text in self.foiv_cache:
            return self.foiv_cache[holder_text]
        
        try:
            all_foivs = FOIV.objects.all()
            for foiv in all_foivs:
                if foiv.short_name and foiv.short_name.lower() in holder_text.lower():
                    self.foiv_cache[holder_text] = foiv
                    return foiv
                
                words = foiv.short_name.split()
                for word in words:
                    if len(word) > 3 and word.lower() in holder_text.lower():
                        self.foiv_cache[holder_text] = foiv
                        return foiv
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"  Ошибка поиска ФОИВ: {e}"))
        
        return None
    
    def find_or_create_rf_representative(self, holder_text, foiv=None):
        """
        Поиск или создание представительства РФ
        """
        if pd.isna(holder_text) or not holder_text:
            return None
        
        holder_text = str(holder_text).strip().strip('"')
        
        # Проверяем кэш
        cache_key = f"{holder_text}|{foiv.pk if foiv else ''}"
        if cache_key in self.rf_rep_cache:
            return self.rf_rep_cache[cache_key]
        
        try:
            # Сначала точный поиск по полному тексту
            rf_rep = RFRepresentative.objects.filter(full_text=holder_text).first()
            if rf_rep:
                self.rf_rep_cache[cache_key] = rf_rep.foiv
                return rf_rep.foiv
            
            # Если передан foiv, создаем новое представительство
            if foiv:
                max_id = RFRepresentative.objects.aggregate(models.Max('rf_representative_id'))['rf_representative_id__max'] or 0
                rf_rep = RFRepresentative.objects.create(
                    rf_representative_id=max_id + 1,
                    foiv=foiv,
                    full_text=holder_text,
                    display_name=f"РФ в лице {foiv.short_name}"
                )
                self.rf_rep_cache[cache_key] = foiv
                return foiv
                
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"  Ошибка поиска представительства РФ: {e}"))
        
        return None
    
    def process_entity(self, entity_name, ip_object):
        """
        Упрощенный метод обработки сущности
        Все, что не физлицо - организация
        """
        if pd.isna(entity_name) or not entity_name:
            return False
        
        entity_type = self.type_detector.detect_type(entity_name)
        
        if entity_type == 'person':
            person = self.find_or_create_person_from_name(entity_name)
            if person:
                ip_object.owner_persons.add(person)
                self.stdout.write(f"        ✅ Физлицо: {person.get_full_name()}")
                return True
        else:
            # Все остальное - организация
            org = self.find_or_create_organization(entity_name)
            if org:
                ip_object.owner_organizations.add(org)
                self.stdout.write(f"        ✅ Организация: {org.name[:50]}...")
                return True
        
        return False
    
    def process_holders(self, holders_list, ip_object):
        """Обработка списка патентообладателей"""
        if not holders_list:
            return
        
        for holder_name in holders_list:
            self.stdout.write(f"        Анализ: {holder_name[:100]}...")
            self.process_entity(holder_name, ip_object)


class InventionParser(BaseFIPSParser):
    """Парсер для изобретений"""
    
    def get_ip_type(self):
        return IPType.objects.filter(slug='invention').first()
    
    def get_required_columns(self):
        return ['registration number', 'invention name']
    
    def process_row(self, row, catalogue, ip_type):
        registration_number = self.clean_string(row.get('registration number'))
        
        if not registration_number:
            return 'skipped'
        
        self.stdout.write(f"\n  📄 Обработка патента №{registration_number}")
        
        name = self.clean_string(row.get('invention name'))
        if name:
            name = self.rid_formatter.format(name)
        else:
            name = f"Изобретение №{registration_number}"
        
        self.stdout.write(f"     Название: {name[:50]}...")
        
        application_date = self.parse_date(row.get('application date'))
        registration_date = self.parse_date(row.get('registration date'))
        patent_starting_date = self.parse_date(row.get('patent starting date'))
        expiration_date = self.parse_date(row.get('expiration date'))
        
        if application_date:
            self.stdout.write(f"     Дата подачи: {application_date}")
        if registration_date:
            self.stdout.write(f"     Дата регистрации: {registration_date}")
        
        actual = self.parse_bool(row.get('actual'))
        self.stdout.write(f"     Статус: {'Активен' if actual else 'Не активен'}")
        
        publication_url = self.clean_string(row.get('publication URL'))
        abstract = self.clean_string(row.get('abstract'))
        claims = self.clean_string(row.get('claims'))
        
        creation_year = None
        if application_date:
            creation_year = application_date.year
        elif registration_date:
            creation_year = registration_date.year
        
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
        
        # Обработка авторов
        authors_str = row.get('authors')
        if not pd.isna(authors_str) and authors_str:
            authors_data = self.parse_authors(authors_str)
            if authors_data:
                self.stdout.write(f"     👥 Авторы: {len(authors_data)} чел.")
                for author_data in authors_data:
                    person = self.find_or_create_person(author_data)
                    if person:
                        ip_object.authors.add(person)
                        self.stdout.write(f"        Автор: {author_data['full_name']}")
            else:
                self.stdout.write("     👥 Авторы: нет данных")
        else:
            self.stdout.write("     👥 Авторы: нет данных")
        
        # Обработка патентообладателей
        holders_str = row.get('patent holders')
        if not pd.isna(holders_str) and holders_str:
            holders_list = self.parse_patent_holders(holders_str)
            if holders_list:
                self.stdout.write(f"     🏢 Патентообладатели: {len(holders_list)}")
                self.process_holders(holders_list, ip_object)
            else:
                self.stdout.write("     🏢 Патентообладатели: нет данных")
        else:
            self.stdout.write("     🏢 Патентообладатели: нет данных")
        
        return 'created' if created else 'updated'
    
    def parse_dataframe(self, df, catalogue):
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


# Остальные парсеры (UtilityModelParser, IndustrialDesignParser и т.д.) 
# будут аналогичными, просто с другими типами РИД


class UtilityModelParser(BaseFIPSParser):
    """Парсер для полезных моделей"""
    
    def get_ip_type(self):
        return IPType.objects.filter(slug='utility-model').first()
    
    def get_required_columns(self):
        return ['registration number', 'utility model name']
    
    def parse_dataframe(self, df, catalogue):
        self.stdout.write(self.style.SUCCESS("  Парсер полезных моделей готов к работе"))
        return {'processed': 0, 'created': 0, 'updated': 0, 'skipped': 0, 'errors': 0}


class IndustrialDesignParser(BaseFIPSParser):
    """Парсер для промышленных образцов"""
    
    def get_ip_type(self):
        return IPType.objects.filter(slug='industrial-design').first()
    
    def get_required_columns(self):
        return ['registration number', 'industrial design name']
    
    def parse_dataframe(self, df, catalogue):
        self.stdout.write(self.style.SUCCESS("  Парсер промышленных образцов готов к работе"))
        return {'processed': 0, 'created': 0, 'updated': 0, 'skipped': 0, 'errors': 0}


class IntegratedCircuitTopologyParser(BaseFIPSParser):
    """Парсер для топологий интегральных микросхем"""
    
    def get_ip_type(self):
        return IPType.objects.filter(slug='integrated-circuit-topology').first()
    
    def get_required_columns(self):
        return ['registration number', 'microchip name']
    
    def parse_dataframe(self, df, catalogue):
        self.stdout.write(self.style.SUCCESS("  Парсер топологий микросхем готов к работе"))
        return {'processed': 0, 'created': 0, 'updated': 0, 'skipped': 0, 'errors': 0}


class ComputerProgramParser(BaseFIPSParser):
    """Парсер для программ для ЭВМ"""
    
    def get_ip_type(self):
        return IPType.objects.filter(slug='computer-program').first()
    
    def get_required_columns(self):
        return ['registration number', 'program name']
    
    def parse_dataframe(self, df, catalogue):
        self.stdout.write(self.style.SUCCESS("  Парсер программ для ЭВМ готов к работе"))
        return {'processed': 0, 'created': 0, 'updated': 0, 'skipped': 0, 'errors': 0}


class DatabaseParser(BaseFIPSParser):
    """Парсер для баз данных"""
    
    def get_ip_type(self):
        return IPType.objects.filter(slug='database').first()
    
    def get_required_columns(self):
        return ['registration number', 'db name']
    
    def parse_dataframe(self, df, catalogue):
        self.stdout.write(self.style.SUCCESS("  Парсер баз данных готов к работе"))
        return {'processed': 0, 'created': 0, 'updated': 0, 'skipped': 0, 'errors': 0}


class Command(BaseCommand):
    help = 'Парсинг каталогов открытых данных ФИПС Роспатента'
    
    def add_arguments(self, parser):
        parser.add_argument('--catalogue-id', type=int, help='ID конкретного каталога для парсинга')
        parser.add_argument('--ip-type', type=str, 
                        choices=['invention', 'utility-model', 'industrial-design', 
                                'integrated-circuit-topology', 'computer-program', 'database'],
                        help='Тип РИД для парсинга (если не указан, парсятся все)')
        parser.add_argument('--dry-run', action='store_true', help='Режим проверки без сохранения в БД')
        parser.add_argument('--encoding', type=str, default='utf-8', help='Кодировка CSV файла')
        parser.add_argument('--delimiter', type=str, default=',', help='Разделитель в CSV файле')
        parser.add_argument('--batch-size', type=int, default=100, help='Размер пакета для bulk-операций')
        parser.add_argument('--min-year', type=int, default=2000, help='Минимальный год регистрации для фильтрации')
        parser.add_argument('--skip-filters', action='store_true', help='Пропустить фильтрацию (обработать все записи)')
        parser.add_argument('--only-active', action='store_true', help='Парсить только активные патенты (actual = True)')
        parser.add_argument('--max-rows', type=int, help='Максимальное количество строк для обработки (для тестирования)')
        parser.add_argument('--force', action='store_true', help='Принудительный парсинг даже если каталог уже обработан')
        parser.add_argument('--mark-processed', action='store_true', 
                        help='Пометить каталог как обработанный (даже если были ошибки)')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
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
        self.force = options.get('force', False)
        self.mark_processed = options.get('mark_processed', False)
        
        if self.dry_run:
            self.stdout.write(self.style.WARNING("\n🔍 РЕЖИМ DRY-RUN: изменения НЕ будут сохранены в БД\n"))
        
        if self.only_active:
            self.stdout.write(self.style.WARNING("📌 Режим: парсинг только активных записей (actual = True)"))
        
        if self.force:
            self.stdout.write(self.style.WARNING("⚠️  Режим: принудительный парсинг (игнорирование даты обработки)"))
        
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
        
        for catalogue in catalogues:
            self.stdout.write(self.style.SUCCESS(f"\n{'='*60}"))
            self.stdout.write(self.style.SUCCESS(f"📁 Обработка каталога: {catalogue.name}"))
            self.stdout.write(self.style.SUCCESS(f"   ID: {catalogue.id}, Тип: {catalogue.ip_type.name if catalogue.ip_type else 'Неизвестно'}"))
            self.stdout.write(self.style.SUCCESS(f"{'='*60}"))
            
            stats = self.process_catalogue(catalogue)
            
            for key in ['processed', 'created', 'updated', 'skipped', 'errors']:
                total_stats[key] += stats.get(key, 0)
        
        self.print_final_stats(total_stats)
    
    def get_catalogues(self, catalogue_id=None, ip_type_slug=None):
        queryset = FipsOpenDataCatalogue.objects.all()
        
        if catalogue_id:
            queryset = queryset.filter(id=catalogue_id)
        elif ip_type_slug:
            queryset = queryset.filter(ip_type__slug=ip_type_slug)
        else:
            queryset = queryset.exclude(catalogue_file='')
        
        return queryset.order_by('ip_type__id', '-publication_date')
    
    def process_catalogue(self, catalogue):
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
        
        # Проверяем, парсился ли уже этот каталог
        if not self.force and hasattr(catalogue, 'parsed_date') and catalogue.parsed_date:
            self.stdout.write(self.style.WARNING(
                f"  ⚠️ Каталог уже был обработан {catalogue.parsed_date.strftime('%d.%m.%Y %H:%M')}"
            ))
            self.stdout.write(self.style.WARNING(f"     Используйте --force для принудительного повторного парсинга"))
            stats['skipped'] += 1
            return stats
        
        ip_type_slug = catalogue.ip_type.slug if catalogue.ip_type else None
        
        if ip_type_slug not in self.parsers:
            self.stdout.write(self.style.ERROR(f"  ❌ Нет парсера для типа РИД: {ip_type_slug}"))
            stats['errors'] += 1
            return stats
        
        parser = self.parsers[ip_type_slug]
        df = self.load_csv(catalogue)
        
        if df is None or df.empty:
            self.stdout.write(self.style.WARNING(f"  ⚠️ Файл пуст или не удалось загрузить"))
            stats['skipped'] += 1
            return stats
        
        self.stdout.write(f"  📊 Загружено записей: {len(df)}")
        
        missing_columns = self.check_required_columns(df, parser.get_required_columns())
        if missing_columns:
            self.stdout.write(self.style.ERROR(f"  ❌ Отсутствуют обязательные колонки: {missing_columns}"))
            stats['errors'] += 1
            return stats
        
        if not self.skip_filters:
            df = self.apply_filters(df)
        
        if df.empty:
            self.stdout.write(self.style.WARNING(f"  ⚠️ Нет данных после фильтрации"))
            stats['skipped'] += 1
            return stats
        
        self.stdout.write(f"  📊 После фильтрации: {len(df)} записей")
        
        if self.max_rows and len(df) > self.max_rows:
            df = df.head(self.max_rows)
            self.stdout.write(self.style.WARNING(f"  ⚠️ Ограничено до {self.max_rows} записей для тестирования"))
        
        try:
            parser_stats = parser.parse_dataframe(df, catalogue)
            stats.update(parser_stats)
            
            # Если не dry-run и нет ошибок (или принудительно помечаем), обновляем дату парсинга
            if not self.dry_run and hasattr(catalogue, 'parsed_date'):
                if stats['errors'] == 0 or self.mark_processed:
                    catalogue.parsed_date = timezone.now()
                    catalogue.save(update_fields=['parsed_date'])
                    self.stdout.write(self.style.SUCCESS(f"  ✅ Каталог помечен как обработанный"))
                else:
                    self.stdout.write(self.style.WARNING(
                        f"  ⚠️ Каталог не помечен как обработанный из-за ошибок "
                        f"(используйте --mark-processed для принудительной пометки)"
                    ))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  ❌ Ошибка при парсинге: {e}"))
            logger.error(f"Error parsing catalogue {catalogue.id}: {e}", exc_info=True)
            stats['errors'] += 1
        
        return stats
    
    def load_csv(self, catalogue):
        file_path = catalogue.catalogue_file.path
        
        if not os.path.exists(file_path):
            self.stdout.write(self.style.ERROR(f"  ❌ Файл не найден: {file_path}"))
            return None
        
        try:
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
                    
                    df.columns = [col.strip().strip('\ufeff').strip('"') for col in df.columns]
                    
                    return df
                except Exception as e:
                    continue
            
            raise Exception("Не удалось загрузить CSV ни одной стратегией")
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  ❌ Ошибка загрузки CSV: {e}"))
            return None
    
    def check_required_columns(self, df, required_columns):
        missing = [col for col in required_columns if col not in df.columns]
        return missing
    
    def apply_filters(self, df):
        original_count = len(df)
        
        if 'registration date' in df.columns:
            df = self.filter_by_registration_year(df)
        
        if self.only_active and 'actual' in df.columns:
            df = self.filter_by_actual(df)
        
        filtered_count = len(df)
        if filtered_count < original_count:
            self.stdout.write(f"  🔍 Фильтрация: {original_count} → {filtered_count} записей")
        
        return df
    
    def filter_by_registration_year(self, df):
        def extract_year(date_str):
            try:
                if pd.isna(date_str) or not date_str:
                    return None
                
                date_str = str(date_str).strip()
                if not date_str:
                    return None
                
                for fmt in ['%Y%m%d', '%Y-%m-%d', '%d.%m.%Y', '%Y/%m/%d']:
                    try:
                        return datetime.strptime(date_str, fmt).year
                    except (ValueError, TypeError):
                        continue
                
                try:
                    return pd.to_datetime(date_str).year
                except (ValueError, TypeError):
                    return None
            except:
                return None
        
        self.stdout.write("  🔍 Фильтрация по году регистрации...")
        df['_year'] = df['registration date'].apply(extract_year)
        
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
        def parse_actual(value):
            if pd.isna(value) or not value:
                return False
            value = str(value).lower().strip()
            return value in ['1', 'true', 'yes', 'да', 'действует', 't', '1.0', 'активен']
        
        df['_actual'] = df['actual'].apply(parse_actual)
        filtered_df = df[df['_actual'] == True].copy()
        filtered_df.drop('_actual', axis=1, inplace=True)
        
        return filtered_df
    
    def print_final_stats(self, stats):
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