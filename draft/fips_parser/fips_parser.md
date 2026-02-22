# Файл: fips_parser\config.py

```
# Конфигурация парсера ФИПС

# Настройки задержек
DELAY_CONFIG = {
    'min_delay': 2,           # Минимальная задержка между запросами (сек)
    'max_delay': 3,           # Максимальная задержка между запросами (сек)
    'long_delay_frequency': 250, # Каждые N запросов - длинная пауза
    'long_delay_min': 30,     # Минимальная длинная пауза (сек)
    'long_delay_max': 60,     # Максимальная длинная пауза (сек)
    'requests_per_minute': 15, # Максимальное количество запросов в минуту
}

# Настройки повторных попыток
RETRY_CONFIG = {
    'max_retries': 3,
    'backoff_factor': 1,
    'status_forcelist': [429, 500, 502, 503, 504],
    'allowed_methods': ["GET"],
}

# Настройки HTTP-запросов
REQUEST_CONFIG = {
    'timeout': 30,
    'encoding': 'windows-1251',
}

# Заголовки HTTP
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
}

# Настройки файлов
FILE_CONFIG = {
    'input_dir': '../data',
    'output_dir': '../data',
    'backup_dir': '../backups',
    'input_file': 'fips1.xlsx',
    'output_file': 'fips1_parsed.xlsx',
}

# Настройки парсера
PARSER_CONFIG = {
    'save_progress_after_each': True,
    'default_start_row': 0,
    'max_requests_per_run': None,
}
```


-----

# Файл: fips_parser\fips_parser.py

```
# fips_parser.py - ОБНОВЛЕННЫЙ ФАЙЛ С ЛЕНИВОЙ ЗАГРУЗКОЙ ПАРСЕРОВ
import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urlparse, parse_qs
import os
import sys
from datetime import datetime, timedelta
import time
import random
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Импорт конфигурации
try:
    from config import (
        DELAY_CONFIG, 
        RETRY_CONFIG, 
        REQUEST_CONFIG,
        HEADERS, 
        FILE_CONFIG,
        PARSER_CONFIG
    )
    CONFIG_LOADED = True
except ImportError as e:
    print(f"⚠️ Ошибка загрузки конфигурации: {e}")
    print("⚠️ Будут использованы значения по умолчанию")
    CONFIG_LOADED = False
    # Значения по умолчанию на случай ошибки
    DELAY_CONFIG = {
        'min_delay': 3, 'max_delay': 7, 'long_delay_frequency': 10,
        'long_delay_min': 30, 'long_delay_max': 60, 'requests_per_minute': 15
    }
    RETRY_CONFIG = {
        'max_retries': 3, 'backoff_factor': 1,
        'status_forcelist': [429, 500, 502, 503, 504], 'allowed_methods': ["GET"]
    }
    REQUEST_CONFIG = {'timeout': 30, 'encoding': 'windows-1251'}
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    }
    FILE_CONFIG = {
        'input_dir': '../data', 'output_dir': '../data', 'backup_dir': '../backups',
        'input_file': 'fips1.xlsx', 'output_file': 'fips1_parsed.xlsx'
    }
    PARSER_CONFIG = {
        'save_progress_after_each': True, 'default_start_row': 0, 'max_requests_per_run': None
    }

class ParserLoader:
    """Класс для ленивой загрузки парсеров"""
    
    _parsers = {}
    
    @classmethod
    def get_parser(cls, rid_type):
        """Получает парсер по типу РИД (ленивая загрузка)"""
        if rid_type not in cls._parsers:
            cls._load_parser(rid_type)
        return cls._parsers.get(rid_type)
    
    @classmethod
    def _load_parser(cls, rid_type):
        """Загружает конкретный парсер по типу РИД"""
        try:
            if rid_type == 'Изобретение':
                from parsers.invention_parser import parse_invention
                cls._parsers[rid_type] = parse_invention
                print(f"✅ Загружен парсер для изобретений")
                
            elif rid_type == 'Полезная модель':
                from parsers.utility_model_parser import parse_utility_model
                cls._parsers[rid_type] = parse_utility_model
                print(f"✅ Загружен парсер для полезных моделей")
                
            elif rid_type == 'Промышленный образец':
                from parsers.industrial_design_parser import parse_industrial_design
                cls._parsers[rid_type] = parse_industrial_design
                print(f"✅ Загружен парсер для промышленных образцов")
                
            elif rid_type == 'Программа для ЭВМ':
                from parsers.computer_program_parser import parse_computer_program
                cls._parsers[rid_type] = parse_computer_program
                print(f"✅ Загружен парсер для программ ЭВМ")
                
            elif rid_type == 'База данных':
                from parsers.database_parser import parse_database
                cls._parsers[rid_type] = parse_database
                print(f"✅ Загружен парсер для баз данных")
                
            elif rid_type == 'Топология интегральной микросхемы':
                from parsers.topology_parser import parse_topology
                cls._parsers[rid_type] = parse_topology
                print(f"✅ Загружен парсер для топологий микросхем")
                
            else:
                cls._parsers[rid_type] = cls._default_parser
                print(f"⚠️ Парсер для типа {rid_type} не найден, используется заглушка")
                
        except ImportError as e:
            print(f"❌ Ошибка загрузки парсера для {rid_type}: {e}")
            cls._parsers[rid_type] = cls._default_parser
    
    @staticmethod
    def _default_parser(html):
        """Парсер-заглушка для неизвестных типов"""
        return {'Примечания': f'Парсер для данного типа РИД не реализован'}

class FIPSParser:
    def __init__(self):
        self.session = requests.Session()
        self.parser_loader = ParserLoader()
        
        # Настраиваем повторные попытки из конфигурации
        retry_strategy = Retry(
            total=RETRY_CONFIG['max_retries'],
            status_forcelist=RETRY_CONFIG['status_forcelist'],
            allowed_methods=RETRY_CONFIG['allowed_methods'],
            backoff_factor=RETRY_CONFIG['backoff_factor']
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Устанавливаем заголовки из конфигурации
        self.session.headers.update(HEADERS)
        
        # Инициализация счетчиков
        self.request_count = 0
        self.start_time = time.time()
        self.last_request_time = 0
        
    def determine_rid_type(self, url):
        """Определение типа РИД по параметру DB в URL"""
        if not url or pd.isna(url):
            return 'Неизвестный тип'
            
        parsed_url = urlparse(url)
        query_params = parse_qs(parsed_url.query)
        db_value = query_params.get('DB', [''])[0]
        
        type_mapping = {
            'RUPAT': 'Изобретение',
            'RUPM': 'Полезная модель', 
            'RUDE': 'Промышленный образец',
            'TIMS': 'Топология интегральной микросхемы',
            'EVM': 'Программа для ЭВМ',
            'DB': 'База данных'
        }
        
        return type_mapping.get(db_value, 'Неизвестный тип')
    
    def get_parser_function(self, rid_type):
        """Получение функции парсера по типу РИД (ленивая загрузка)"""
        return self.parser_loader.get_parser(rid_type)
    
    def smart_delay(self):
        """Умная задержка между запросами с использованием конфигурации"""
        current_time = time.time()
        
        # Базовая задержка между запросами из конфигурации
        base_delay = random.uniform(
            DELAY_CONFIG['min_delay'], 
            DELAY_CONFIG['max_delay']
        )
        
        # Увеличиваем счетчик запросов
        self.request_count += 1
        
        # Длинная пауза из конфигурации
        if self.request_count % DELAY_CONFIG['long_delay_frequency'] == 0:
            long_delay = random.uniform(
                DELAY_CONFIG['long_delay_min'], 
                DELAY_CONFIG['long_delay_max']
            )
            print(f"🔁 Большая пауза {long_delay:.1f} сек после {self.request_count} запросов...")
            time.sleep(long_delay)
        else:
            # Случайная задержка для имитации человеческого поведения
            time.sleep(base_delay)
        
        # Ограничение скорости из конфигурации
        elapsed = current_time - self.start_time
        if elapsed < 60 and self.request_count >= DELAY_CONFIG['requests_per_minute']:
            excess_delay = 60 - elapsed
            if excess_delay > 0:
                print(f"⏳ Превышен лимит запросов, ждем {excess_delay:.1f} сек...")
                time.sleep(excess_delay)
                # Сбрасываем счетчик
                self.start_time = time.time()
                self.request_count = 0
        
        self.last_request_time = current_time
    
    def fetch_page(self, url):
        """Загрузка страницы с обработкой ошибок и настройками из конфигурации"""
        try:
            print(f"📡 Загружаем страницу: {url}")
            response = self.session.get(
                url, 
                timeout=REQUEST_CONFIG['timeout']
            )
            response.encoding = REQUEST_CONFIG['encoding']
            
            if response.status_code == 200:
                print("✅ Страница успешно загружена")
                return response.text
            elif response.status_code == 429:
                print("⚠️ Превышен лимит запросов. Ждем 60 секунд...")
                time.sleep(60)
                return None
            else:
                print(f"❌ Ошибка HTTP {response.status_code} для URL: {url}")
                return None
                
        except requests.exceptions.Timeout:
            print(f"⏰ Таймаут при загрузке {url}")
            return None
        except requests.exceptions.ConnectionError:
            print(f"🔌 Ошибка соединения для {url}")
            return None
        except requests.exceptions.RequestException as e:
            print(f"🚫 Ошибка запроса для {url}: {e}")
            return None
        except Exception as e:
            print(f"💥 Неожиданная ошибка при загрузке {url}: {e}")
            return None
    
    def parse_single_record(self, url):
        """Парсинг одной записи по URL"""
        if not url or pd.isna(url):
            result = {col: '' for col in self.get_columns()}
            result['Примечания'] = 'Пустой URL'
            return result
        
        rid_type = self.determine_rid_type(url)
        print(f"🔍 Определен тип РИД: {rid_type}")
        parser_function = self.get_parser_function(rid_type)
        
        if not parser_function:
            result = {col: '' for col in self.get_columns()}
            result['Тип РИД'] = rid_type
            result['Примечания'] = f'Парсер для типа {rid_type} не реализован'
            return result
        
        # Задержка перед запросом
        self.smart_delay()
        
        html_content = self.fetch_page(url)
        if not html_content:
            result = {col: '' for col in self.get_columns()}
            result['Тип РИД'] = rid_type
            result['Примечания'] = f'Не удалось загрузить страницу'
            return result
        
        try:
            print("🔄 Парсим данные...")
            result = parser_function(html_content)
            result['Тип РИД'] = rid_type
            # Убедимся, что все поля присутствуют
            for col in self.get_columns():
                if col not in result:
                    result[col] = ''
            print("✅ Данные успешно распарсены")
            return result
        except Exception as e:
            print(f"❌ Ошибка парсинга: {e}")
            result = {col: '' for col in self.get_columns()}
            result['Тип РИД'] = rid_type
            result['Примечания'] = f'Ошибка парсинга: {str(e)}'
            return result
    
    def get_columns(self):
        """Возвращает список всех колонок таблицы"""
        return [
            'Тип РИД', 'Название', 'Номер регистрации/патента', 'Дата регистрации',
            'Номер заявки', 'Дата подачи заявки', 'Дата публикации', 'Авторы',
            'Правообладатель/Патентообладатель', 'Реферат', 'Контактные реквизиты/Адрес для переписки',
            'Статус', 'Дата изменения статуса', 'Информация о пошлинах', 'Язык программирования',
            'СУБД', 'Объем', 'Формула', 'Цитируемые документы', 'Описание внешнего вида',
            'Срок действия права', 'Примечания'
        ]
    
    def ensure_string_columns(self, df):
        """Убеждаемся, что все колонки имеют строковый тип"""
        for col in self.get_columns():
            if col in df.columns:
                # Преобразуем колонку в строковый тип, заменяя NaN на пустые строки
                df[col] = df[col].astype(str).replace('nan', '')
        return df
    
    def process_excel(self, input_file=None, output_file=None, start_from=None, max_requests=None):
        """Обработка Excel файла с использованием конфигурации"""
        # Используем значения из конфигурации, если параметры не указаны
        if input_file is None:
            input_file = os.path.join(FILE_CONFIG['input_dir'], FILE_CONFIG['input_file'])
        if output_file is None:
            output_file = os.path.join(FILE_CONFIG['output_dir'], FILE_CONFIG['output_file'])
        if start_from is None:
            start_from = PARSER_CONFIG['default_start_row']
        if max_requests is None:
            max_requests = PARSER_CONFIG['max_requests_per_run']
        
        try:
            df = pd.read_excel(input_file)
            print(f"📁 Загружен файл {input_file} с {len(df)} записями")
        except Exception as e:
            print(f"❌ Ошибка чтения файла {input_file}: {e}")
            return
        
        # Создаем все необходимые колонки, если их нет
        for col in self.get_columns():
            if col not in df.columns:
                df[col] = ''
        
        # Преобразуем все колонки в строковый тип чтобы избежать предупреждений
        df = self.ensure_string_columns(df)
        
        total = len(df)
        processed = 0
        successful = 0
        
        for index, row in df.iterrows():
            if index < start_from:
                continue
                
            # Ограничение на количество запросов (для тестирования)
            if max_requests and processed >= max_requests:
                print(f"⏹️ Достигнут лимит в {max_requests} запросов")
                break
                
            url = row['Ссылка на Роспатент']
            print(f"\n🎯 Обработка {index + 1}/{total}")
            print(f"   URL: {url}")
            
            result = self.parse_single_record(url)
            
            # Заполняем данные в DataFrame
            for key, value in result.items():
                if key in df.columns:
                    # Явно преобразуем значение в строку
                    str_value = str(value) if value is not None else ''
                    df.at[index, key] = str_value
            
            # Увеличиваем счетчик успешных обработок
            if not result.get('Примечания') or 'ошибка' not in result.get('Примечания', '').lower():
                successful += 1
            
            # Сохраняем прогресс после каждой записи (если включено в конфиге)
            if PARSER_CONFIG['save_progress_after_each']:
                try:
                    # Перед сохранением убеждаемся, что все колонки строковые
                    df = self.ensure_string_columns(df)
                    df.to_excel(output_file, index=False)
                    print(f"💾 Сохранен прогресс для записи {index + 1}")
                except Exception as e:
                    print(f"❌ Ошибка сохранения: {e}")
            
            processed += 1
            
            # Статистика
            elapsed = time.time() - self.start_time
            req_per_min = (self.request_count / elapsed * 60) if elapsed > 0 else 0
            print(f"📊 Статистика: {self.request_count} запросов, {req_per_min:.1f} запр/мин, успешно: {successful}/{processed}")
        
        # Финальное сохранение
        try:
            df = self.ensure_string_columns(df)
            df.to_excel(output_file, index=False)
            print(f"💾 Финальный результат сохранен в {output_file}")
        except Exception as e:
            print(f"❌ Ошибка финального сохранения: {e}")
        
        print(f"\n🎉 Обработка завершена! Обработано {processed} записей, успешно: {successful}")

def main():
    parser = FIPSParser()
    
    # Определяем пути к файлам из конфигурации
    base_dir = os.path.dirname(os.path.abspath(__file__))
    input_file = os.path.join(base_dir, FILE_CONFIG['input_dir'], FILE_CONFIG['input_file'])
    output_file = os.path.join(base_dir, FILE_CONFIG['output_dir'], FILE_CONFIG['output_file'])
    
    # Создаем папки если их нет
    os.makedirs(os.path.dirname(input_file), exist_ok=True)
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    if not os.path.exists(input_file):
        print(f"❌ Файл {input_file} не найден")
        print(f"📂 Текущая рабочая директория: {os.getcwd()}")
        print(f"📂 Директория скрипта: {base_dir}")
        
        # Попробуем найти файл в других местах
        possible_paths = [
            os.path.join(base_dir, FILE_CONFIG['input_file']),
            os.path.join(os.getcwd(), FILE_CONFIG['input_file']),
            os.path.join(os.getcwd(), FILE_CONFIG['input_dir'], FILE_CONFIG['input_file']),
        ]
        for path in possible_paths:
            if os.path.exists(path):
                input_file = path
                print(f"✅ Найден файл: {input_file}")
                break
        else:
            print("❌ Файл не найден ни в одном из возможных местоположений")
            return
    
    print(f"🚀 Начало обработки файла: {input_file}")
    print(f"💡 Результат будет сохранен в: {output_file}")
    print(f"⚙️  Конфигурация загружена: {'Да' if CONFIG_LOADED else 'Нет'}")
    print("🔄 Парсеры будут загружаться по мере необходимости")
    print("⚠️  Парсер использует задержки для избежания блокировки")
    
    # Параметры запуска из конфигурации
    start_from = PARSER_CONFIG['default_start_row']
    max_requests = PARSER_CONFIG['max_requests_per_run']
    
    # Обработка аргументов командной строки (переопределяют конфиг)
    if len(sys.argv) > 1:
        try:
            start_from = int(sys.argv[1])
            print(f"🔁 Начинаем с записи {start_from} (из аргументов командной строки)")
        except ValueError:
            print("❌ Неверный номер стартовой записи")
    
    if len(sys.argv) > 2:
        try:
            max_requests = int(sys.argv[2])
            print(f"⏹️ Ограничение: {max_requests} запросов (из аргументов командной строки)")
        except ValueError:
            print("❌ Неверное ограничение запросов")
    
    try:
        parser.process_excel(input_file, output_file, start_from, max_requests)
    except KeyboardInterrupt:
        print("\n⏹️ Обработка прервана пользователем")
    except Exception as e:
        print(f"💥 Критическая ошибка: {e}")

if __name__ == "__main__":
    main()
```


-----

# Файл: fips_parser\parsers\computer_program_parser.py

```
def parse_computer_program(html_content):
    """Заглушка для парсера программ для ЭВМ"""
    return {'Примечания': 'Парсер для программ ЭВМ в разработке'}
```


-----

# Файл: fips_parser\parsers\database_parser.py

```
def parse_database(html_content):
    """Заглушка для парсера баз данных"""
    return {'Примечания': 'Парсер для баз данных в разработке'}
```


-----

# Файл: fips_parser\parsers\industrial_design_parser.py

```
import re
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

def parse_industrial_design(html_content):
    """Парсер для промышленных образцов"""
    
    # Внутренние вспомогательные функции для изоляции
    def find_element_containing_text(soup, search_text):
        """Находит элемент, содержащий указанный текст"""
        elements = soup.find_all(string=re.compile(re.escape(search_text)))
        for element in elements:
            return element.parent
        return None

    def find_text_after(soup, search_text):
        """Находит текст после указанного текста"""
        elements = soup.find_all(string=re.compile(re.escape(search_text)))
        for element in elements:
            parent = element.parent
            if parent:
                full_text = parent.get_text()
                if search_text in full_text:
                    return full_text.split(search_text)[-1].strip()
        return None

    def find_b_tag_after(soup, search_text):
        """Находит тег <b> после указанного текста"""
        elements = soup.find_all(string=re.compile(re.escape(search_text)))
        for element in elements:
            parent = element.parent
            if parent:
                b_tag = parent.find('b')
                if b_tag:
                    return b_tag
        return None

    def extract_date(text):
        """Извлекает дату в формате ДД.ММ.ГГГГ из текста"""
        if text:
            date_match = re.search(r'(\d{2}\.\d{2}\.\d{4})', text)
            return date_match.group(1) if date_match else ''
        return ''

    def format_names(text):
        """Форматирует список имен, убирая лишние пробелы и переносы"""
        text = re.sub(r'\s*<br\s*/?>\s*', ', ', text)
        text = re.sub(r'\s+', ' ', text)
        names = [name.strip() for name in text.split(',') if name.strip()]
        seen = set()
        unique_names = []
        for name in names:
            if name not in seen:
                seen.add(name)
                unique_names.append(name)
        return ', '.join(unique_names)

    soup = BeautifulSoup(html_content, 'html.parser')
    result = {
        'Название': '',
        'Номер регистрации/патента': '',
        'Дата регистрации': '',
        'Номер заявки': '',
        'Дата подачи заявки': '',
        'Дата публикации': '',
        'Авторы': '',
        'Правообладатель/Патентообладатель': '',
        'Реферат': '#Н/П',
        'Контактные реквизиты/Адрес для переписки': '',
        'Статус': '',
        'Дата изменения статуса': '',
        'Информация о пошлинах': '',
        'Язык программирования': '#Н/П',
        'СУБД': '#Н/П',
        'Объем': '#Н/П',
        'Формула': '#Н/П',
        'Цитируемые документы': '#Н/П',
        'Описание внешнего вида': '#Н/Загр',
        'Срок действия права': '',
        'Примечания': ''
    }
    
    errors = []
    
    try:
        # Номер регистрации/патента
        reg_elem = soup.find('a', title=lambda x: x and 'Ссылка на реестр' in x)
        if reg_elem:
            result['Номер регистрации/патента'] = reg_elem.get_text(strip=True).replace(' ', '')
        
        # Название
        title_elem = soup.find('p', id='B542')
        if title_elem:
            title_text = title_elem.get_text(strip=True)
            if '(54)' in title_text:
                result['Название'] = title_text.split('(54)')[-1].strip()
        
        # Дата регистрации
        reg_date_elem = find_element_containing_text(soup, '(15) Дата регистрации:')
        if reg_date_elem:
            reg_date_text = reg_date_elem.get_text()
            if '(15) Дата регистрации:' in reg_date_text:
                date_part = reg_date_text.split('(15) Дата регистрации:')[-1].strip()
                result['Дата регистрации'] = extract_date(date_part)
        
        # Номер заявки
        app_number_elem = find_element_containing_text(soup, '(21) Номер заявки:')
        if app_number_elem:
            app_number_text = app_number_elem.get_text()
            if '(21) Номер заявки:' in app_number_text:
                number_part = app_number_text.split('(21) Номер заявки:')[-1].strip()
                # Убираем возможные лишние символы
                number_part = re.sub(r'[^\d]', '', number_part)
                result['Номер заявки'] = number_part
        
        # Дата подачи заявки
        app_date_elem = find_element_containing_text(soup, '(22) Дата подачи заявки:')
        if app_date_elem:
            app_date_text = app_date_elem.get_text()
            if '(22) Дата подачи заявки:' in app_date_text:
                date_part = app_date_text.split('(22) Дата подачи заявки:')[-1].strip()
                result['Дата подачи заявки'] = extract_date(date_part)
        
        # Дата публикации
        pub_date_elem = find_element_containing_text(soup, '(45) Дата публикации:')
        if pub_date_elem:
            pub_date_text = pub_date_elem.get_text()
            if '(45) Дата публикации:' in pub_date_text:
                date_part = pub_date_text.split('(45) Дата публикации:')[-1].strip()
                # Убираем текст "Бюл" если присутствует
                if 'Бюл' in date_part:
                    date_part = date_part.split('Бюл')[0].strip()
                result['Дата публикации'] = extract_date(date_part)
        
        # Авторы
        authors_elem = find_element_containing_text(soup, '(72) Автор(ы):')
        if authors_elem:
            authors_text = authors_elem.get_text()
            authors_clean = re.sub(r'<[^>]+>', '', str(authors_elem))
            authors_clean = authors_clean.replace('(72) Автор(ы):', '').strip()
            result['Авторы'] = format_names(authors_clean)
        
        # Патентообладатель
        owner_elem = find_element_containing_text(soup, '(73) Патентообладатель(и):')
        if owner_elem:
            owner_text = owner_elem.get_text()
            owner_clean = re.sub(r'<[^>]+>', '', str(owner_elem))
            owner_clean = owner_clean.replace('(73) Патентообладатель(и):', '').strip()
            result['Правообладатель/Патентообладатель'] = format_names(owner_clean)
        
        # Контактные реквизиты
        address_elem = find_element_containing_text(soup, 'Адрес для переписки:')
        if address_elem:
            address_text = address_elem.get_text()
            if 'Адрес для переписки:' in address_text:
                address_part = address_text.split('Адрес для переписки:')[-1].strip()
                result['Контактные реквизиты/Адрес для переписки'] = address_part
        
        # Статус и дата изменения статуса
        status_rows = soup.find_all('tr')
        for row in status_rows:
            status_label = row.find('td', id='StatusL')
            if status_label and 'Статус:' in status_label.get_text():
                status_value = row.find('td', id='StatusR')
                if status_value:
                    status_text = status_value.get_text(strip=True)
                    if '(' in status_text:
                        result['Статус'] = status_text.split('(')[0].strip()
                        date_match = re.search(r'\(([^)]+)\)', status_text)
                        if date_match:
                            date_str = date_match.group(1)
                            date_match2 = re.search(r'(\d{2}\.\d{2}\.\d{4})', date_str)
                            if date_match2:
                                result['Дата изменения статуса'] = date_match2.group(1)
                    else:
                        result['Статус'] = status_text
        
        # Информация о пошлинах
        for row in status_rows:
            status_label = row.find('td', id='StatusL')
            if status_label and 'Пошлина:' in status_label.get_text():
                status_value = row.find('td', id='StatusR')
                if status_value:
                    # Извлекаем текст после <br> тега, который соответствует пошлине
                    status_html = str(status_value)
                    if '<br/>' in status_html:
                        parts = status_html.split('<br/>')
                        if len(parts) > 1:
                            # Берем вторую часть (после <br/>) и очищаем от тегов
                            fee_part = BeautifulSoup(parts[1], 'html.parser').get_text(strip=True)
                            result['Информация о пошлинах'] = fee_part
                    else:
                        # Если нет <br/>, берем весь текст
                        result['Информация о пошлинах'] = status_value.get_text(strip=True)
        
        # Срок действия права (дата подачи заявки + 5 лет)
        if result['Дата подачи заявки']:
            try:
                app_date = datetime.strptime(result['Дата подачи заявки'], '%d.%m.%Y')
                expiry_date = app_date + timedelta(days=365*5)
                result['Срок действия права'] = expiry_date.strftime('%d.%m.%Y')
            except ValueError as e:
                errors.append(f"Ошибка расчета срока действия права: {str(e)}")
        else:
            errors.append("Не найдена дата подачи заявки для расчета срока действия")
        
    except Exception as e:
        errors.append(f"Общая ошибка парсинга: {str(e)}")
    
    # Проверяем заполненность полей и добавляем ошибки
    required_fields = ['Номер заявки', 'Дата подачи заявки', 'Авторы', 'Правообладатель/Патентообладатель']
    for field in required_fields:
        if not result[field]:
            errors.append(f"Не заполнено поле: {field}")
    
    if errors:
        result['Примечания'] = '; '.join(errors)
    
    return result

# Для автономной работы
if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        with open(sys.argv[1], 'r', encoding='utf-8') as f:
            html_content = f.read()
        result = parse_industrial_design(html_content)
        print("Результаты парсинга промышленного образца:")
        print("=" * 50)
        for key, value in result.items():
            if value and value != '#Н/П' and value != '#Н/Загр':  # Показываем только заполненные поля
                print(f"{key}: {value}")
```


-----

# Файл: fips_parser\parsers\invention_parser.py

```
import re
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

def parse_invention(html_content):
    """Парсер для изобретений"""
    
    # Внутренние вспомогательные функции для изоляции
    def find_element_containing_text(soup, search_text):
        """Находит элемент, содержащий указанный текст"""
        elements = soup.find_all(string=re.compile(re.escape(search_text)))
        for element in elements:
            return element.parent
        return None

    def find_element_after_text(soup, search_text):
        """Находит элемент после указанного текста"""
        elements = soup.find_all(string=re.compile(re.escape(search_text)))
        for element in elements:
            return element
        return None

    def extract_date(text):
        """Извлекает дату в формате ДД.ММ.ГГГГ из текста"""
        date_match = re.search(r'(\d{2}\.\d{2}\.\d{4})', text)
        return date_match.group(1) if date_match else ''

    def format_names(text):
        """Форматирует список имен, убирая лишние пробелы и переносы"""
        text = re.sub(r'\s*<br\s*/?>\s*', ', ', text)
        text = re.sub(r'\s+', ' ', text)
        names = [name.strip() for name in text.split(',') if name.strip()]
        seen = set()
        unique_names = []
        for name in names:
            if name not in seen:
                seen.add(name)
                unique_names.append(name)
        return ', '.join(unique_names)

    soup = BeautifulSoup(html_content, 'html.parser')
    result = {
        'Название': '',
        'Номер регистрации/патента': '',
        'Дата регистрации': '',
        'Номер заявки': '',
        'Дата подачи заявки': '',
        'Дата публикации': '',
        'Авторы': '',
        'Правообладатель/Патентообладатель': '',
        'Реферат': '',
        'Контактные реквизиты/Адрес для переписки': '',
        'Статус': '',
        'Дата изменения статуса': '',
        'Информация о пошлинах': '',
        'Язык программирования': '#Н/П',
        'СУБД': '#Н/П',
        'Объем': '#Н/П',
        'Формула': '',
        'Цитируемые документы': '',
        'Описание внешнего вида': '#Н/П',
        'Срок действия права': '',
        'Примечания': ''
    }
    
    errors = []
    
    try:
        # Номер регистрации/патента
        reg_elem = soup.find('a', title=lambda x: x and 'Ссылка на реестр' in x)
        if reg_elem:
            result['Номер регистрации/патента'] = reg_elem.get_text(strip=True).replace(' ', '')
        
        # Название
        title_elem = soup.find('p', id='B542')
        if title_elem:
            title_text = title_elem.get_text(strip=True)
            if '(54)' in title_text:
                result['Название'] = title_text.split('(54)')[-1].strip()
        
        # Дата регистрации
        reg_date_elem = find_element_after_text(soup, 'Дата регистрации:')
        if reg_date_elem:
            b_tag = reg_date_elem.find_next('b')
            if b_tag:
                result['Дата регистрации'] = extract_date(b_tag.get_text(strip=True))
        
        # Номер заявки и дата подачи
        application_elem = find_element_containing_text(soup, '(21)(22) Заявка:')
        if application_elem:
            app_link = application_elem.find('a')
            if app_link:
                result['Номер заявки'] = app_link.get_text(strip=True)
            
            app_text = application_elem.get_text()
            if ',' in app_text:
                date_part = app_text.split(',')[-1].strip()
                result['Дата подачи заявки'] = extract_date(date_part)
        
        # Дата публикации
        pub_elem = find_element_containing_text(soup, '(45) Опубликовано:')
        if pub_elem:
            pub_link = pub_elem.find('a')
            if pub_link:
                result['Дата публикации'] = extract_date(pub_link.get_text(strip=True))
        
        # Авторы
        authors_elem = find_element_containing_text(soup, '(72) Автор(ы):')
        if authors_elem:
            authors_text = authors_elem.get_text()
            authors_clean = re.sub(r'<[^>]+>', '', str(authors_elem))
            authors_clean = authors_clean.replace('(72) Автор(ы):', '').strip()
            result['Авторы'] = format_names(authors_clean)
        
        # Патентообладатель
        owner_elem = find_element_containing_text(soup, '(73) Патентообладатель(и):')
        if owner_elem:
            owner_text = owner_elem.get_text()
            owner_clean = re.sub(r'<[^>]+>', '', str(owner_elem))
            owner_clean = owner_clean.replace('(73) Патентообладатель(и):', '').strip()
            result['Правообладатель/Патентообладатель'] = format_names(owner_clean)
        
        # Реферат
        abs_div = soup.find('div', id='Abs')
        if abs_div:
            abs_text = abs_div.get_text(strip=True)
            if 'Реферат:' in abs_text:
                abs_text = abs_text.split('Реферат:', 1)[-1].strip()
            result['Реферат'] = abs_text
        
        # Контактные реквизиты
        address_elem = find_element_after_text(soup, 'Адрес для переписки:')
        if address_elem:
            b_tag = address_elem.find_next('b')
            if b_tag:
                result['Контактные реквизиты/Адрес для переписки'] = b_tag.get_text(strip=True)
        
        # Статус и дата изменения статуса
        status_rows = soup.find_all('tr')
        for row in status_rows:
            status_label = row.find('td', id='StatusL')
            if status_label and 'Статус:' in status_label.get_text():
                status_value = row.find('td', id='StatusR')
                if status_value:
                    status_text = status_value.get_text(strip=True)
                    if '(' in status_text:
                        result['Статус'] = status_text.split('(')[0].strip()
                        date_match = re.search(r'\(([^)]+)\)', status_text)
                        if date_match:
                            date_str = date_match.group(1)
                            date_match2 = re.search(r'(\d{2}\.\d{2}\.\d{4})', date_str)
                            if date_match2:
                                result['Дата изменения статуса'] = date_match2.group(1)
                    else:
                        result['Статус'] = status_text
        
        # Информация о пошлинах
        for row in status_rows:
            status_label = row.find('td', id='StatusL')
            if status_label and 'Пошлина:' in status_label.get_text():
                status_value = row.find('td', id='StatusR')
                if status_value:
                    result['Информация о пошлинах'] = status_value.get_text(strip=True)
        
        # Формула изобретения
        formula_start = soup.find('p', class_='TitCla', string=re.compile('Формула изобретения'))
        if formula_start:
            formula_content = []
            next_elem = formula_start.find_next_sibling()
            while next_elem and not (hasattr(next_elem, 'name') and next_elem.name == 'a' and 'ClEnd' in next_elem.get('href', '')):
                if hasattr(next_elem, 'get_text'):
                    text = next_elem.get_text(strip=True)
                    if text:
                        formula_content.append(text)
                next_elem = next_elem.find_next_sibling()
            result['Формула'] = '\n'.join(formula_content)
        
        # Цитируемые документы
        cited_elem = find_element_containing_text(soup, 'Список документов, цитированных в отчете о поиске:')
        if cited_elem:
            cited_text = cited_elem.get_text()
            if 'Список документов, цитированных в отчете о поиске:' in cited_text:
                docs_part = cited_text.split('Список документов, цитированных в отчете о поиске:')[-1].strip()
                b_tag = cited_elem.find('b')
                if b_tag:
                    result['Цитируемые документы'] = b_tag.get_text(strip=True)
                else:
                    result['Цитируемые документы'] = docs_part
        
        # Срок действия права (дата подачи заявки + 20 лет)
        if result['Дата подачи заявки']:
            try:
                app_date = datetime.strptime(result['Дата подачи заявки'], '%d.%m.%Y')
                expiry_date = app_date + timedelta(days=365*20)
                result['Срок действия права'] = expiry_date.strftime('%d.%m.%Y')
            except ValueError as e:
                errors.append(f"Ошибка расчета срока действия права: {str(e)}")
        else:
            errors.append("Не найдена дата подачи заявки для расчета срока действия")
        
    except Exception as e:
        errors.append(f"Общая ошибка парсинга: {str(e)}")
    
    # Проверяем заполненность полей и добавляем ошибки
    required_fields = ['Номер заявки', 'Дата подачи заявки', 'Авторы', 'Правообладатель/Патентообладатель', 'Реферат']
    for field in required_fields:
        if not result[field]:
            errors.append(f"Не заполнено поле: {field}")
    
    if errors:
        result['Примечания'] = '; '.join(errors)
    
    return result

# Для автономной работы
if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        with open(sys.argv[1], 'r', encoding='utf-8') as f:
            html_content = f.read()
        result = parse_invention(html_content)
        print("Результаты парсинга изобретения:")
        print("=" * 50)
        for key, value in result.items():
            if value:  # Показываем только заполненные поля
                print(f"{key}: {value}")
```


-----

# Файл: fips_parser\parsers\topology_parser.py

```
def parse_topology(html_content):
    """Заглушка для парсера топологий микросхем"""
    return {'Примечания': 'Парсер для топологий микросхем в разработке'}
```


-----

# Файл: fips_parser\parsers\utility_model_parser.py

```
import re
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

def parse_utility_model(html_content):
    """Парсер для полезных моделей"""
    
    # Внутренние вспомогательные функции для изоляции
    def find_element_containing_text(soup, search_text):
        """Находит элемент, содержащий указанный текст"""
        elements = soup.find_all(string=re.compile(re.escape(search_text)))
        for element in elements:
            return element.parent
        return None

    def find_text_after(soup, search_text):
        """Находит текст после указанного текста"""
        elements = soup.find_all(string=re.compile(re.escape(search_text)))
        for element in elements:
            parent = element.parent
            if parent:
                full_text = parent.get_text()
                if search_text in full_text:
                    return full_text.split(search_text)[-1].strip()
        return None

    def find_b_tag_after(soup, search_text):
        """Находит тег <b> после указанного текста"""
        elements = soup.find_all(string=re.compile(re.escape(search_text)))
        for element in elements:
            parent = element.parent
            if parent:
                b_tag = parent.find('b')
                if b_tag:
                    return b_tag
        return None

    def extract_date(text):
        """Извлекает дату в формате ДД.ММ.ГГГГ из текста"""
        if text:
            date_match = re.search(r'(\d{2}\.\d{2}\.\d{4})', text)
            return date_match.group(1) if date_match else ''
        return ''

    def format_names(text):
        """Форматирует список имен, убирая лишние пробелы и переносы"""
        text = re.sub(r'\s*<br\s*/?>\s*', ', ', text)
        text = re.sub(r'\s+', ' ', text)
        names = [name.strip() for name in text.split(',') if name.strip()]
        seen = set()
        unique_names = []
        for name in names:
            if name not in seen:
                seen.add(name)
                unique_names.append(name)
        return ', '.join(unique_names)

    soup = BeautifulSoup(html_content, 'html.parser')
    result = {
        'Название': '',
        'Номер регистрации/патента': '',
        'Дата регистрации': '',
        'Номер заявки': '',
        'Дата подачи заявки': '',
        'Дата публикации': '',
        'Авторы': '',
        'Правообладатель/Патентообладатель': '',
        'Реферат': '',
        'Контактные реквизиты/Адрес для переписки': '',
        'Статус': '',
        'Дата изменения статуса': '',
        'Информация о пошлинах': '',
        'Язык программирования': '#Н/П',
        'СУБД': '#Н/П',
        'Объем': '#Н/П',
        'Формула': '',
        'Цитируемые документы': '',
        'Описание внешнего вида': '#Н/П',
        'Срок действия права': '',
        'Примечания': ''
    }
    
    errors = []
    
    try:
        # Номер регистрации/патента
        reg_elem = soup.find('a', title=lambda x: x and 'Ссылка на реестр' in x)
        if reg_elem:
            result['Номер регистрации/патента'] = reg_elem.get_text(strip=True).replace(' ', '')
        
        # Название
        title_elem = soup.find('p', id='B542')
        if title_elem:
            title_text = title_elem.get_text(strip=True)
            if '(54)' in title_text:
                result['Название'] = title_text.split('(54)')[-1].strip()
        
        # Дата регистрации
        reg_date_elem = find_element_containing_text(soup, 'Дата регистрации:')
        if reg_date_elem:
            b_tag = reg_date_elem.find('b')
            if b_tag:
                result['Дата регистрации'] = extract_date(b_tag.get_text(strip=True))
        
        # Номер заявки и дата подачи
        application_elem = find_element_containing_text(soup, '(21)(22) Заявка:')
        if application_elem:
            app_b_tag = application_elem.find('b')
            if app_b_tag:
                app_text = app_b_tag.get_text(strip=True)
                if ',' in app_text:
                    parts = app_text.split(',')
                    result['Номер заявки'] = parts[0].strip()
                    result['Дата подачи заявки'] = extract_date(parts[1].strip() if len(parts) > 1 else '')
        
        # Дата публикации
        pub_elem = find_element_containing_text(soup, '(45) Опубликовано:')
        if pub_elem:
            pub_link = pub_elem.find('a')
            if pub_link:
                result['Дата публикации'] = extract_date(pub_link.get_text(strip=True))
        
        # Авторы
        authors_elem = find_element_containing_text(soup, '(72) Автор(ы):')
        if authors_elem:
            authors_text = authors_elem.get_text()
            authors_clean = re.sub(r'<[^>]+>', '', str(authors_elem))
            authors_clean = authors_clean.replace('(72) Автор(ы):', '').strip()
            result['Авторы'] = format_names(authors_clean)
        
        # Патентообладатель
        owner_elem = find_element_containing_text(soup, '(73) Патентообладатель(и):')
        if owner_elem:
            owner_text = owner_elem.get_text()
            owner_clean = re.sub(r'<[^>]+>', '', str(owner_elem))
            owner_clean = owner_clean.replace('(73) Патентообладатель(и):', '').strip()
            result['Правообладатель/Патентообладатель'] = format_names(owner_clean)
        
        # Реферат
        abs_div = soup.find('div', id='Abs')
        if abs_div:
            abs_text = abs_div.get_text(strip=True)
            if 'Реферат:' in abs_text:
                abs_text = abs_text.split('Реферат:', 1)[-1].strip()
            result['Реферат'] = abs_text
        
        # Контактные реквизиты
        address_elem = find_element_containing_text(soup, 'Адрес для переписки:')
        if address_elem:
            b_tag = address_elem.find('b')
            if b_tag:
                result['Контактные реквизиты/Адрес для переписки'] = b_tag.get_text(strip=True)
        
        # Статус и дата изменения статуса
        status_rows = soup.find_all('tr')
        for row in status_rows:
            status_label = row.find('td', id='StatusL')
            if status_label and 'Статус:' in status_label.get_text():
                status_value = row.find('td', id='StatusR')
                if status_value:
                    status_text = status_value.get_text(strip=True)
                    if '(' in status_text:
                        result['Статус'] = status_text.split('(')[0].strip()
                        date_match = re.search(r'\(([^)]+)\)', status_text)
                        if date_match:
                            date_str = date_match.group(1)
                            date_match2 = re.search(r'(\d{2}\.\d{2}\.\d{4})', date_str)
                            if date_match2:
                                result['Дата изменения статуса'] = date_match2.group(1)
                    else:
                        result['Статус'] = status_text
        
        # Информация о пошлинах
        for row in status_rows:
            status_label = row.find('td', id='StatusL')
            if status_label and 'Пошлина:' in status_label.get_text():
                status_value = row.find('td', id='StatusR')
                if status_value:
                    result['Информация о пошлинах'] = status_value.get_text(strip=True)
        
        # Формула полезной модели
        formula_start = soup.find('p', class_='TitCla', string=re.compile('Формула полезной модели'))
        if formula_start:
            formula_content = []
            next_elem = formula_start.find_next_sibling()
            while next_elem and not (hasattr(next_elem, 'name') and next_elem.name == 'a' and 'ClEnd' in next_elem.get('href', '')):
                if hasattr(next_elem, 'get_text'):
                    text = next_elem.get_text(strip=True)
                    if text:
                        formula_content.append(text)
                next_elem = next_elem.find_next_sibling()
            result['Формула'] = '\n'.join(formula_content)
        
        # Цитируемые документы
        cited_elem = find_element_containing_text(soup, 'Список документов, цитированных в отчете о поиске:')
        if cited_elem:
            cited_text = cited_elem.get_text()
            if 'Список документов, цитированных в отчете о поиске:' in cited_text:
                docs_part = cited_text.split('Список документов, цитированных в отчете о поиске:')[-1].strip()
                b_tag = cited_elem.find('b')
                if b_tag:
                    result['Цитируемые документы'] = b_tag.get_text(strip=True)
                else:
                    result['Цитируемые документы'] = docs_part
        
        # Срок действия права (дата подачи заявки + 10 лет)
        if result['Дата подачи заявки']:
            try:
                app_date = datetime.strptime(result['Дата подачи заявки'], '%d.%m.%Y')
                expiry_date = app_date + timedelta(days=365*10)
                result['Срок действия права'] = expiry_date.strftime('%d.%m.%Y')
            except ValueError as e:
                errors.append(f"Ошибка расчета срока действия права: {str(e)}")
        else:
            errors.append("Не найдена дата подачи заявки для расчета срока действия")
        
    except Exception as e:
        errors.append(f"Общая ошибка парсинга: {str(e)}")
    
    # Проверяем заполненность полей и добавляем ошибки
    required_fields = ['Номер заявки', 'Дата подачи заявки', 'Авторы', 'Правообладатель/Патентообладатель', 'Реферат']
    for field in required_fields:
        if not result[field]:
            errors.append(f"Не заполнено поле: {field}")
    
    if errors:
        result['Примечания'] = '; '.join(errors)
    
    return result

# Для автономной работы
if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        with open(sys.argv[1], 'r', encoding='utf-8') as f:
            html_content = f.read()
        result = parse_utility_model(html_content)
        print("Результаты парсинга полезной модели:")
        print("=" * 50)
        for key, value in result.items():
            if value:  # Показываем только заполненные поля
                print(f"{key}: {value}")
```


-----

# Файл: fips_parser\parsers\__init__.py

```

```
