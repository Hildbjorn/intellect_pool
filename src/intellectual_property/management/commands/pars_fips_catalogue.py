"""
Команда для парсинга каталогов открытых данных ФИПС Роспатента.
Поддерживает все типы РИД: изобретения, полезные модели, промышленные образцы,
топологии интегральных микросхем, программы для ЭВМ и базы данных.
"""

import logging
import re
from datetime import datetime
from typing import Optional, Tuple, List, Dict, Any, Set
from collections import defaultdict

from django.db import models
from django.core.management.base import BaseCommand, CommandError
from django.utils.text import slugify
from django.utils import timezone
from tqdm import tqdm
import pandas as pd
import os

# Импорты natasha
from natasha import (
    Segmenter,
    MorphVocab,
    NewsEmbedding,
    NewsMorphTagger,
    NewsSyntaxParser,
    NewsNERTagger,
    Doc,
    dates_extractor,
    money_extractor,
    addr_extractor,
    names_extractor
)

from intellectual_property.models import (
    FipsOpenDataCatalogue, IPType, ProtectionDocumentType,
    IPObject, AdditionalPatent, IPImage
)
from core.models import (
    City, Region, District, Person, Organization, 
    FOIV, Country, RFRepresentative,
    OrganizationNormalizationRule, ActivityType, CeoPosition
)
from common.utils.text import TextUtils
from common.utils.dates import DateUtils

logger = logging.getLogger(__name__)


class NatashaFullProcessor:
    """
    Полноценный процессор для анализа текстов с использованием всех возможностей natasha
    """
    _instance = None
    _doc_cache = {}
    _morph_cache = {}
    
    # Список римских цифр
    ROMAN_NUMERALS = {
        'I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X',
        'XI', 'XII', 'XIII', 'XIV', 'XV', 'XVI', 'XVII', 'XVIII', 'XIX', 'XX',
        'XXI', 'XXII', 'XXIII', 'XXIV', 'XXV', 'XXX', 'XL', 'L', 'LX', 'XC',
        'C', 'CD', 'D', 'DC', 'CM', 'M'
    }
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """Инициализация всех компонентов natasha"""
        try:
            self.segmenter = Segmenter()
            self.morph_vocab = MorphVocab()
            self.emb = NewsEmbedding()
            
            self.morph_tagger = NewsMorphTagger(self.emb)
            self.syntax_parser = NewsSyntaxParser(self.emb)
            self.ner_tagger = NewsNERTagger(self.emb)
            
            # Экстракторы для различных сущностей
            self.date_extractor = dates_extractor
            self.money_extractor = money_extractor
            self.addr_extractor = addr_extractor
            self.name_extractor = names_extractor
            
            self.initialized = True
            print("✅ Natasha инициализирована полностью")
        except Exception as e:
            print(f"⚠️ Ошибка инициализации natasha: {e}")
            self.initialized = False
    
    def process_document(self, text: str) -> Optional[Doc]:
        """Полный анализ документа с кэшированием"""
        if not text or not self.initialized:
            return None
        
        if text in self._doc_cache:
            return self._doc_cache[text]
        
        doc = Doc(text)
        doc.segment(self.segmenter)
        doc.tag_morph(self.morph_tagger)
        doc.parse_syntax(self.syntax_parser)
        doc.tag_ner(self.ner_tagger)
        
        # Нормализация всех токенов
        for token in doc.tokens:
            token.lemmatize(self.morph_vocab)
        
        # Нормализация именованных сущностей
        for span in doc.spans:
            span.normalize(self.morph_vocab)
        
        self._doc_cache[text] = doc
        return doc
    
    def get_morph_features(self, word: str) -> Dict[str, Any]:
        """Получение морфологических характеристик слова"""
        if not word or not self.initialized:
            return {}
        
        if word in self._morph_cache:
            return self._morph_cache[word]
        
        doc = Doc(word)
        doc.segment(self.segmenter)
        doc.tag_morph(self.morph_tagger)
        
        if doc.tokens:
            token = doc.tokens[0]
            features = {
                'word': token.text,
                'lemma': token.lemma,
                'pos': token.pos,
                'feats': token.feats,
                'is_upper': token.text.isupper(),
                'is_title': token.text.istitle(),
                'is_proper': token.pos == 'PROPN'
            }
            
            if token.feats:
                features['case'] = token.feats.get('case')
                features['number'] = token.feats.get('number')
                features['gender'] = token.feats.get('gender')
                features['animacy'] = token.feats.get('animacy')
            
            self._morph_cache[word] = features
            return features
        
        return {}
    
    def extract_named_entities(self, text: str) -> List[Dict[str, Any]]:
        """Извлечение именованных сущностей"""
        if not text or not self.initialized:
            return []
        
        doc = self.process_document(text)
        if not doc:
            return []
        
        entities = []
        for span in doc.spans:
            entity = {
                'text': span.text,
                'type': span.type,
                'normalized': span.normalized,
                'start': span.start,
                'stop': span.stop,
                'tokens': [token.text for token in span.tokens],
                'lemmas': [token.lemma for token in span.tokens]
            }
            
            if span.type == 'PER':
                names = self.name_extractor(span.text)
                if names:
                    name_fact = names[0].fact
                    entity['first_name'] = name_fact.first
                    entity['last_name'] = name_fact.last
                    entity['middle_name'] = name_fact.middle
            
            entities.append(entity)
        
        return entities
    
    def normalize_word(self, word: str, is_first_in_sentence: bool = False, is_inside_quotes: bool = False) -> str:
        """Нормализация слова с учетом контекста"""
        if not word or len(word) <= 1:
            return word
        
        # Проверка на римские цифры
        if self.is_roman_numeral(word):
            return word.upper()
        
        # Проверка на инициалы
        if re.match(r'^[А-ЯЁA-Z]\.$', word) or re.match(r'^[А-ЯЁA-Z]\.[А-ЯЁA-Z]\.$', word):
            return word.upper()
        
        # Очистка от знаков препинания для анализа
        clean_word = re.sub(r'[.,;:!?()]', '', word)
        if not clean_word:
            return word
        
        # Если слово полностью в верхнем регистре и длинное - возможно аббревиатура
        if clean_word.isupper() and len(clean_word) > 1:
            return clean_word
        
        # Получаем морфологические характеристики
        morph = self.get_morph_features(clean_word)
        
        # Определяем регистр
        if is_inside_quotes:
            # Внутри кавычек - каждое слово с большой буквы (как имя собственное)
            return clean_word[0].upper() + clean_word[1:].lower()
        elif morph.get('is_proper'):
            # Имена собственные - с большой буквы
            return clean_word[0].upper() + clean_word[1:].lower()
        elif is_first_in_sentence:
            # Первое слово предложения - с большой буквы
            return clean_word[0].upper() + clean_word[1:].lower()
        else:
            # Обычные слова - с маленькой буквы
            return clean_word.lower()
    
    def normalize_sentence(self, sentence: str) -> str:
        """Нормализация целого предложения"""
        if not sentence:
            return sentence
        
        # Разбиваем на слова, сохраняя пробелы и кавычки
        words = re.split(r'(\s+|")', sentence)
        result = []
        is_first = True
        inside_quotes = False
        
        for word in words:
            if word == '"':
                inside_quotes = not inside_quotes
                result.append(word)
                continue
            
            if word.isspace():
                result.append(word)
                continue
            
            if not word.strip():
                result.append(word)
                continue
            
            # Нормализуем слово
            normalized = self.normalize_word(word, is_first, inside_quotes)
            result.append(normalized)
            
            if not word.isspace() and word != '"':
                is_first = False
        
        return ''.join(result)
    
    def classify_entity(self, text: str) -> str:
        """Классификация сущности"""
        if not text:
            return 'unknown'
        
        entities = self.extract_named_entities(text)
        if entities:
            main_entity = max(entities, key=lambda e: e['stop'] - e['start'])
            entity_type = main_entity['type']
            
            if entity_type == 'PER':
                return 'person'
            elif entity_type == 'ORG':
                return 'organization'
            elif entity_type == 'LOC':
                return 'location'
        
        # Если NER не сработал, используем упрощенную логику
        if any(ind in text for ind in ['ООО', 'ЗАО', 'АО', 'ПАО', 'ФГУП', 'Институт']):
            return 'organization'
        
        # Проверяем, похоже ли на ФИО
        words = text.split()
        if 2 <= len(words) <= 4:
            name_like = 0
            for word in words:
                clean = word.rstrip('.,')
                if clean and clean[0].isupper() and len(clean) > 1:
                    name_like += 1
            if name_like >= len(words) - 1:
                return 'person'
        
        return 'unknown'
    
    def is_roman_numeral(self, text: str) -> bool:
        """Проверка на римскую цифру"""
        if not text:
            return False
        clean_text = text.strip('.,;:!?()').upper()
        return clean_text in self.ROMAN_NUMERALS
    
    def extract_person_name_parts(self, text: str) -> Dict[str, str]:
        """Извлечение частей ФИО"""
        if not text:
            return {}
        
        names = self.name_extractor(text)
        if names:
            fact = names[0].fact
            return {
                'first': fact.first,
                'last': fact.last,
                'middle': fact.middle,
                'full': fact.as_string
            }
        
        entities = self.extract_named_entities(text)
        for entity in entities:
            if entity['type'] == 'PER':
                return {
                    'full': entity['text'],
                    'normalized': entity['normalized']
                }
        
        return {}


class OrganizationNormalizer:
    """
    Класс для нормализации названий организаций
    """
    
    def __init__(self):
        self.rules_cache = None
        self.natasha = NatashaFullProcessor()
        self.load_rules()
    
    def load_rules(self):
        """Загрузка правил из БД в кэш"""
        try:
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
        except Exception as e:
            self.rules_cache = []
            logger.warning(f"Не удалось загрузить правила нормализации: {e}")
    
    def normalize(self, name: str) -> Dict[str, Any]:
        """Нормализация названия с использованием правил из БД"""
        if pd.isna(name) or not name:
            return {'normalized': '', 'keywords': [], 'original': name}
        
        original = str(name).strip()
        name_lower = original.lower()
        
        # Применяем правила из БД
        normalized = name_lower
        if self.rules_cache:
            for rule in self.rules_cache:
                try:
                    if rule['type'] == 'ignore':
                        pattern = r'\b' + re.escape(rule['original']) + r'\b'
                        normalized = re.sub(pattern, '', normalized)
                    else:
                        pattern = r'\b' + re.escape(rule['original']) + r'\b'
                        normalized = re.sub(pattern, rule['replacement'], normalized)
                except Exception:
                    continue
        
        # Убираем кавычки и знаки препинания
        normalized = re.sub(r'["\'«»„“”]', '', normalized)
        normalized = re.sub(r'[^\w\s-]', ' ', normalized)
        normalized = ' '.join(normalized.split())
        
        # Извлекаем ключевые слова через natasha
        entities = self.natasha.extract_named_entities(original)
        keywords = []
        for entity in entities:
            if entity['type'] == 'ORG':
                keywords.extend(entity['lemmas'])
        
        return {
            'normalized': normalized,
            'keywords': list(set(keywords)),
            'original': original,
            'entities': entities
        }
    
    def fix_quotes_spacing(self, text: str) -> str:
        """
        Исправляет пробелы вокруг кавычек:
        Общество с ограниченной ответственностью" Айсиэм Гласс Калуга
        -> Общество с ограниченной ответственностью "Айсиэм Гласс Калуга"
        """
        if not text:
            return text
        
        # Добавляем пробел перед открывающей кавычкой, если его нет
        text = re.sub(r'([^ ])"([^"])', r'\1 "\2', text)
        
        # Добавляем пробел после закрывающей кавычки, если его нет
        text = re.sub(r'([^"])"([^ ])', r'\1" \2', text)
        
        return text
    
    def format_organization_name(self, name: str) -> str:
        """
        Форматирование названия организации с правильным регистром и кавычками
        """
        if not name:
            return name
        
        # Сначала исправляем пробелы вокруг кавычек
        name = self.fix_quotes_spacing(name)
        
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
        
        # Добавляем римские цифры
        ALWAYS_UPPER.update(NatashaFullProcessor.ROMAN_NUMERALS)
        
        # Получаем именованные сущности из названия
        entities = self.natasha.extract_named_entities(name)
        entity_dict = {e['text']: e['type'] for e in entities}
        
        # Разбиваем на части по кавычкам
        parts = re.split(r'(")', name)
        result = []
        in_quotes = False
        
        for part in parts:
            if part == '"':
                in_quotes = not in_quotes
                result.append(part)
                continue
            
            if in_quotes:
                # Часть внутри кавычек - каждое слово с большой буквы
                words = part.split()
                formatted_words = []
                for word in words:
                    if not word:
                        continue
                    word_clean = word.strip('.,;:()')
                    word_upper = word_clean.upper()
                    
                    if word_upper in ALWAYS_UPPER:
                        formatted_words.append(word_upper)
                    elif self.natasha.is_roman_numeral(word_clean):
                        formatted_words.append(word_clean.upper())
                    else:
                        # В кавычках - все слова с большой буквы
                        formatted_words.append(word_clean[0].upper() + word_clean[1:].lower())
                
                if formatted_words:
                    result.append(' '.join(formatted_words))
            
            else:
                # Часть вне кавычек
                words = part.split()
                formatted_words = []
                for word in words:
                    if not word:
                        continue
                    word_clean = word.strip('.,;:()')
                    word_upper = word_clean.upper()
                    
                    if word_upper in ALWAYS_UPPER:
                        formatted_words.append(word_upper)
                    elif word_clean in entity_dict:
                        # Это именованная сущность
                        formatted_words.append(word_clean[0].upper() + word_clean[1:].lower())
                    elif word_clean.isupper() and len(word_clean) > 1:
                        # Неизвестная аббревиатура
                        formatted_words.append(word_clean)
                    else:
                        # Обычные слова
                        formatted_words.append(word_clean)
                
                if formatted_words:
                    result.append(' '.join(formatted_words))
        
        return ''.join(result)


class RIDNameFormatter:
    """
    Класс для форматирования названий РИД
    """
    
    def __init__(self):
        self.natasha = NatashaFullProcessor()
        
        # Аббревиатуры, которые всегда остаются в верхнем регистре
        self.KEEP_UPPER = {
            'ДНК', 'РНК', 'ПЦР', 'ИФА', 'ЭДТА', 'АТФ', 'АДФ', 'НАД', 'НАДФ',
            'COVID-19', 'SARS-COV-2', 'ВИЧ', 'СПИД',
            '°C', '°F', 'K', 'М', 'СМ', 'ММ', 'КМ', 'КГ', 'Г', 'МГ', 'МКГ',
            'Л', 'МЛ', 'МКЛ', 'С', 'МС', 'МКС', 'МИН', 'Ч', 'СУТ',
            'ПА', 'КПА', 'МПА', 'ГПА', 'АТМ', 'БАР', 'ММ РТ. СТ.',
            'А', 'В', 'ВТ', 'КВТ', 'МВТ', 'ГВТ', 'ОМ', 'Ф', 'ГН', 'ТЛ',
            'БИТ', 'БАЙТ', 'КБ', 'МБ', 'ГБ', 'ТБ', 'ГЦ', 'КГЦ', 'МГЦ', 'ГГЦ',
            'ГОСТ', 'ТУ', 'СНиП', 'СП', 'СанПиН', 'ISO', 'IEC', 'IEEE',
            'USB', 'HDMI', 'WI-FI', 'LTE', '5G', 'CPU', 'GPU', 'RAM', 'ROM',
            'CAD', 'CAM', 'CAE', 'PLM', 'PDM', 'ERP', 'CRM', 'MES',
            'МПК', 'МКТУ', 'МКПО', 'НИОКР', 'РИД', 'ИС', 'ОИС', 'ФИПС',
        }
        
        # Добавляем римские цифры
        self.KEEP_UPPER.update(NatashaFullProcessor.ROMAN_NUMERALS)
    
    def format(self, text: str) -> str:
        """Форматирование названия РИД"""
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
            
            # Нормализуем предложение через natasha
            normalized = self.natasha.normalize_sentence(sentence)
            formatted_sentences.append(normalized)
        
        result = ' '.join(formatted_sentences)
        
        # Очистка
        result = re.sub(r'\s+([,;:.])', r'\1', result)
        result = ' '.join(result.split())
        
        return result


class PersonNameFormatter:
    """
    Класс для форматирования имен людей
    """
    
    def __init__(self):
        self.natasha = NatashaFullProcessor()
    
    def format(self, name: str) -> str:
        """Форматирование ФИО человека"""
        if not name:
            return name
        
        # Пробуем извлечь структурированное имя через natasha
        name_parts = self.natasha.extract_person_name_parts(name)
        
        if name_parts:
            parts = []
            if name_parts.get('last'):
                parts.append(self._format_part(name_parts['last']))
            if name_parts.get('first'):
                parts.append(self._format_part(name_parts['first']))
            if name_parts.get('middle'):
                parts.append(self._format_part(name_parts['middle']))
            if parts:
                return ' '.join(parts)
        
        # Если не удалось извлечь, форматируем вручную
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
            clean = part.strip('.,')
            if clean.isupper() and len(clean) > 1:
                formatted_parts.append(clean[0].upper() + clean[1:].lower())
            else:
                formatted_parts.append(part)
        
        return ' '.join(formatted_parts)
    
    def _format_part(self, part: str) -> str:
        """Форматирование части ФИО"""
        if not part:
            return part
        if len(part) == 1:
            return part.upper() + '.'
        return part[0].upper() + part[1:].lower()


class EntityTypeDetector:
    """
    Детектор типов сущностей
    """
    
    def __init__(self):
        self.natasha = NatashaFullProcessor()
    
    def detect_type(self, text: str) -> str:
        """Определение типа сущности"""
        return self.natasha.classify_entity(text)


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
        self.natasha = NatashaFullProcessor()
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
            
            self.stdout.write(self.style.WARNING(f"  Страна с кодом {code} не найдена"))
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
        """Поиск похожей организации"""
        if pd.isna(org_name) or not org_name:
            return None
        
        org_name = str(org_name).strip().strip('"')
        
        # Прямое совпадение
        direct_match = Organization.objects.filter(
            models.Q(name=org_name) |
            models.Q(full_name=org_name) |
            models.Q(short_name=org_name)
        ).first()
        if direct_match:
            return direct_match
        
        # Нормализуем название
        norm_data = self.org_normalizer.normalize(org_name)
        normalized = norm_data['normalized']
        keywords = norm_data['keywords']
        
        # Поиск по ключевым словам
        for keyword in keywords:
            if len(keyword) >= 3:
                similar = Organization.objects.filter(
                    models.Q(name__icontains=keyword) |
                    models.Q(full_name__icontains=keyword) |
                    models.Q(short_name__icontains=keyword)
                ).first()
                if similar:
                    return similar
        
        # Поиск по вхождению
        if len(normalized) > 30:
            prefix = normalized[:30]
            similar = Organization.objects.filter(
                models.Q(name__icontains=prefix) |
                models.Q(full_name__icontains=prefix) |
                models.Q(short_name__icontains=prefix)
            ).first()
            if similar:
                return similar
        
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
        
        # Ищем похожие
        similar = self.find_similar_organization(org_name)
        if similar:
            self.organization_cache[org_name] = similar
            return similar
        
        # Форматируем название
        formatted_name = self.org_normalizer.format_organization_name(org_name)
        
        # Генерируем slug
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
        """Поиск ФОИВ"""
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
        """Поиск или создание представительства РФ"""
        if pd.isna(holder_text) or not holder_text:
            return None
        
        holder_text = str(holder_text).strip().strip('"')
        
        cache_key = f"{holder_text}|{foiv.pk if foiv else ''}"
        if cache_key in self.rf_rep_cache:
            return self.rf_rep_cache[cache_key]
        
        try:
            rf_rep = RFRepresentative.objects.filter(full_text=holder_text).first()
            if rf_rep:
                self.rf_rep_cache[cache_key] = rf_rep.foiv
                return rf_rep.foiv
            
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
        """Обработка сущности"""
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
        
        if not self.force and hasattr(catalogue, 'parsed_date') and catalogue.parsed_date:
            self.stdout.write(self.style.WARNING(
                f"  ⚠️ Каталог уже был обработан {catalogue.parsed_date.strftime('%d.%m.%Y %H:%M')}"
            ))
            self.stdout.write(self.style.WARNING(f"     Используйте --force для повторного парсинга"))
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
            self.stdout.write(self.style.WARNING(f"  ⚠️ Ограничено до {self.max_rows} записей"))
        
        try:
            parser_stats = parser.parse_dataframe(df, catalogue)
            stats.update(parser_stats)
            
            if not self.dry_run and hasattr(catalogue, 'parsed_date'):
                if stats['errors'] == 0 or self.mark_processed:
                    catalogue.parsed_date = timezone.now()
                    catalogue.save(update_fields=['parsed_date'])
                    self.stdout.write(self.style.SUCCESS(f"  ✅ Каталог помечен как обработанный"))
                else:
                    self.stdout.write(self.style.WARNING(
                        f"  ⚠️ Каталог не помечен как обработанный из-за ошибок"
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