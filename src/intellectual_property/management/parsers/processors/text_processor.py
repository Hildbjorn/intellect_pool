"""
Процессор для русских текстов с использованием natasha
Оптимизированная версия с кэшированием и контролем памяти
"""

from natasha import (
    Segmenter,
    MorphVocab,
    NewsEmbedding,
    NewsMorphTagger,
    NewsSyntaxParser,
    NewsNERTagger,
    Doc,
    NamesExtractor
)


class RussianTextProcessor:
    """
    Процессор для русских текстов с использованием natasha
    """

    # Список римских цифр
    ROMAN_NUMERALS = {
        'I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X',
        'XI', 'XII', 'XIII', 'XIV', 'XV', 'XVI', 'XVII', 'XVIII', 'XIX', 'XX',
        'XXI', 'XXII', 'XXIII', 'XXIV', 'XXV', 'XXX', 'XL', 'L', 'LX', 'XC',
        'C', 'CD', 'D', 'DC', 'CM', 'M'
    }

    # Аббревиатуры для поиска организаций
    ORG_ABBR = {
        'ООО', 'ЗАО', 'ОАО', 'АО', 'ПАО', 'НАО',
        'ФГУП', 'ФГБУ', 'ФГАОУ', 'ФГАУ', 'ФГКУ',
        'НИИ', 'КБ', 'ОКБ', 'СКБ', 'ЦКБ', 'ПКБ',
        'НПО', 'НПП', 'НПФ', 'НПЦ', 'НИЦ',
        'МУП', 'ГУП', 'ИЧП', 'ТОО', 'АОЗТ', 'АООТ',
        'РФ', 'РАН', 'СО РАН', 'УрО РАН', 'ДВО РАН',
        'МГУ', 'СПбГУ', 'МФТИ', 'МИФИ', 'МГТУ', 'МАИ',
        'ЛТД', 'ИНК', 'КО', 'ГМБХ', 'АГ', 'СА', 'НВ', 'БВ', 'СЕ',
        'Ко', 'Ltd', 'Inc', 'GmbH', 'AG', 'SA', 'NV', 'BV', 'SE',
    }

    def __init__(self):
        # Инициализация компонентов natasha
        self.segmenter = Segmenter()
        self.morph_vocab = MorphVocab()
        self.emb = NewsEmbedding()
        self.morph_tagger = NewsMorphTagger(self.emb)
        self.syntax_parser = NewsSyntaxParser(self.emb)
        self.ner_tagger = NewsNERTagger(self.emb)
        self.names_extractor = NamesExtractor(self.morph_vocab)

        # Кэши с ограничением размера
        self.doc_cache = {}
        self.person_cache = {}
        self.max_cache_size = 5000  # Ограничиваем размер кэша документов
        
        # Счетчики
        self.doc_cache_hits = 0
        self.doc_cache_misses = 0

        # Добавляем римские цифры в аббревиатуры
        self.ORG_ABBR.update(self.ROMAN_NUMERALS)

    def get_doc(self, text: str):
        """Получение или создание документа с кэшированием"""
        if not text:
            return None

        # Не кэшируем очень длинные тексты
        if len(text) > 10000:
            return self._create_doc(text)

        # Проверяем кэш
        if text in self.doc_cache:
            self.doc_cache_hits += 1
            return self.doc_cache[text]

        self.doc_cache_misses += 1
        doc = self._create_doc(text)

        # Управление размером кэша
        if len(self.doc_cache) >= self.max_cache_size:
            # Удаляем 20% самых старых записей
            items = list(self.doc_cache.items())
            self.doc_cache = dict(items[-int(self.max_cache_size * 0.8):])

        self.doc_cache[text] = doc
        return doc

    def _create_doc(self, text: str):
        """Создание документа"""
        doc = Doc(text)
        doc.segment(self.segmenter)
        doc.tag_morph(self.morph_tagger)
        doc.parse_syntax(self.syntax_parser)
        doc.tag_ner(self.ner_tagger)

        # Лемматизация
        for token in doc.tokens:
            token.lemmatize(self.morph_vocab)

        for span in doc.spans:
            span.normalize(self.morph_vocab)

        return doc

    def is_roman_numeral(self, text: str) -> bool:
        """Проверка на римскую цифру"""
        if not text:
            return False
        clean_text = text.strip('.,;:!?()').upper()
        return clean_text in self.ROMAN_NUMERALS

    def is_abbr(self, text: str) -> bool:
        """Проверка на аббревиатуру организации"""
        if not text:
            return False
        clean_text = text.strip('.,;:!?()').upper()
        return clean_text in self.ORG_ABBR

    def is_person(self, text: str) -> bool:
        """Определение, является ли текст ФИО человека"""
        if not text or len(text) < 6:
            return False

        # Проверяем кэш
        if text in self.person_cache:
            return self.person_cache[text]

        # Если есть явные признаки организации
        if any(ind in text for ind in self.ORG_ABBR if len(ind) > 2):
            self.person_cache[text] = False
            return False

        org_indicators = ['Общество', 'Компания', 'Корпорация', 'Завод',
                         'Институт', 'Университет', 'Академия', 'Лаборатория',
                         'Фирма', 'Центр']

        if any(ind.lower() in text.lower() for ind in org_indicators):
            self.person_cache[text] = False
            return False

        # Проверка через NER
        doc = self.get_doc(text)
        if doc and doc.spans:
            for span in doc.spans:
                if span.type == 'PER':
                    self.person_cache[text] = True
                    return True

        # Паттерны ФИО
        words = text.split()
        if 2 <= len(words) <= 4:
            name_like = 0
            for word in words:
                clean = word.rstrip('.,')
                if clean and clean[0].isupper() and len(clean) > 1:
                    name_like += 1
            result = name_like >= len(words) - 1
            self.person_cache[text] = result
            return result

        self.person_cache[text] = False
        return False

    def extract_person_parts(self, text: str) -> dict:
        """Извлечение частей ФИО с помощью natasha"""
        matches = list(self.names_extractor(text))
        if matches:
            fact = matches[0].fact
            parts = []
            if fact.last:
                parts.append(fact.last)
            if fact.first:
                parts.append(fact.first)
            if fact.middle:
                parts.append(fact.middle)

            return {
                'last': fact.last or '',
                'first': fact.first or '',
                'middle': fact.middle or '',
                'full': ' '.join(parts)
            }

        # Fallback: ручной парсинг
        return self._parse_name_manually(text)

    def _parse_name_manually(self, text: str) -> dict:
        """Ручной парсинг имени"""
        words = text.split()

        if len(words) == 3:
            return {
                'last': words[0],
                'first': words[1],
                'middle': words[2],
                'full': text
            }
        elif len(words) == 2:
            return {
                'last': words[0],
                'first': words[1],
                'middle': '',
                'full': text
            }
        else:
            return {
                'last': text,
                'first': '',
                'middle': '',
                'full': text
            }

    def format_person_name(self, name: str) -> str:
        """Форматирование ФИО человека"""
        if not name:
            return name

        parts = self.extract_person_parts(name)
        if parts.get('full'):
            return parts['full']

        return name

    def clear_cache(self):
        """Очистка кэшей для освобождения памяти"""
        self.doc_cache.clear()
        self.person_cache.clear()
        self.doc_cache_hits = 0
        self.doc_cache_misses = 0

    def get_cache_stats(self):
        """Статистика кэша"""
        total = self.doc_cache_hits + self.doc_cache_misses
        return {
            'doc_cache_size': len(self.doc_cache),
            'person_cache_size': len(self.person_cache),
            'doc_cache_hits': self.doc_cache_hits,
            'doc_cache_misses': self.doc_cache_misses,
            'hit_ratio': self.doc_cache_hits / total if total > 0 else 0
        }