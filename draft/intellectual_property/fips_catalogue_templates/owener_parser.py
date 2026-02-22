import csv
import signal
import sys
import os
from datetime import datetime

class PatentHolderParser:
    def __init__(self, input_file, output_file, batch_size=1000):
        """
        Инициализация парсера с пакетной обработкой
        
        Args:
            input_file (str): входной CSV файл
            output_file (str): выходной текстовый файл
            batch_size (int): размер пакета для записи
        """
        self.input_file = input_file
        self.output_file = output_file
        self.batch_size = batch_size
        self.processed_count = 0
        self.patent_holders = set()  # используем set для автоматического удаления дубликатов
        self.interrupted = False
        self.temp_file = output_file + '.temp'
        self.backup_file = output_file + '.backup'
        
        # Настройка обработчика прерывания
        signal.signal(signal.SIGINT, self.signal_handler)
        
    def signal_handler(self, sig, frame):
        """Обработчик сигнала прерывания (Ctrl+C)"""
        print("\n\n⚠️  Получен сигнал прерывания!")
        print("💾 Сохраняем промежуточные результаты...")
        self.interrupted = True
        
    def save_batch(self, batch_data, is_final=False):
        """Сохраняет пакет данных в файл"""
        mode = 'a' if os.path.exists(self.output_file) else 'w'
        
        with open(self.output_file, mode, encoding='utf-8') as f:
            # Если файл новый, добавляем заголовок
            if mode == 'w':
                f.write(f"СПИСОК ПРАВООБЛАДАТЕЛЕЙ\n")
                f.write(f"Создан: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Источник: {self.input_file}\n")
                f.write("=" * 60 + "\n\n")
            
            # Записываем пакет данных
            for holder in batch_data:
                f.write(f"{holder}\n")
        
        # Создаем бэкап после каждого пакета
        if not is_final:
            import shutil
            shutil.copy2(self.output_file, self.backup_file)
            print(f"   💾 Промежуточный файл сохранен (бэкап: {self.backup_file})")
    
    def save_checkpoint(self):
        """Сохраняет чекпоинт с текущим прогрессом"""
        checkpoint_file = self.output_file + '.checkpoint'
        with open(checkpoint_file, 'w', encoding='utf-8') as f:
            f.write(f"processed={self.processed_count}\n")
            f.write(f"unique_holders={len(self.patent_holders)}\n")
            f.write(f"timestamp={datetime.now().isoformat()}\n")
        print(f"   📍 Чекпоинт сохранен: {checkpoint_file}")
    
    def load_checkpoint(self):
        """Загружает чекпоинт если существует"""
        checkpoint_file = self.output_file + '.checkpoint'
        if os.path.exists(checkpoint_file):
            try:
                with open(checkpoint_file, 'r', encoding='utf-8') as f:
                    data = {}
                    for line in f:
                        key, value = line.strip().split('=')
                        data[key] = value
                
                print(f"📦 Найден чекпоинт от {data.get('timestamp', 'неизвестно')}")
                print(f"   Обработано записей: {data.get('processed', '0')}")
                print(f"   Найдено правообладателей: {data.get('unique_holders', '0')}")
                
                response = input("🔄 Продолжить с этого места? (y/n): ").lower()
                if response == 'y':
                    return int(data.get('processed', 0))
            except Exception as e:
                print(f"⚠️  Ошибка при загрузке чекпоинта: {e}")
        
        return 0
    
    def process(self):
        """Основной метод обработки"""
        print("🔍 ПАРСЕР ПРАВООБЛАДАТЕЛЕЙ (пакетная обработка)")
        print("=" * 60)
        print(f"📁 Входной файл: {self.input_file}")
        print(f"📁 Выходной файл: {self.output_file}")
        print(f"📦 Размер пакета: {self.batch_size} записей")
        print("=" * 60)
        
        # Проверяем наличие чекпоинта
        start_from = self.load_checkpoint()
        
        # Шаг 1: Подсчет общего количества строк
        print("\n⏳ Анализ файла...")
        try:
            with open(self.input_file, 'r', encoding='utf-8-sig') as csvfile:
                total_lines = sum(1 for line in csvfile) - 1  # минус заголовок
            print(f"   Всего записей в файле: {total_lines}")
            
            if start_from > 0:
                print(f"   Пропускаем {start_from} уже обработанных записей")
                
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            return
        
        # Шаг 2: Обработка данных
        print("\n⏳ Начинаем обработку (нажмите Ctrl+C для прерывания)...")
        
        try:
            with open(self.input_file, 'r', encoding='utf-8-sig') as csvfile:
                reader = csv.DictReader(csvfile, delimiter=',')
                
                # Проверяем наличие колонки
                if 'patent holders' not in reader.fieldnames:
                    print("❌ Ошибка: Нет колонки 'patent holders'")
                    return
                
                batch = []
                batch_num = 0
                
                for row_num, row in enumerate(reader, start=1):
                    # Пропускаем уже обработанные записи
                    if row_num <= start_from:
                        continue
                    
                    # Проверка на прерывание
                    if self.interrupted:
                        print("\n⚠️  Процесс прерван пользователем")
                        break
                    
                    # Обновляем прогресс
                    self.processed_count = row_num
                    percent = (row_num / total_lines) * 100
                    
                    # Показываем прогресс
                    bar_length = 40
                    filled = int(bar_length * row_num // total_lines)
                    bar = '█' * filled + '░' * (bar_length - filled)
                    status = f"\r   [{bar}] {row_num}/{total_lines} ({percent:.1f}%) | Найдено: {len(self.patent_holders)}"
                    print(status, end='', flush=True)
                    
                    # Обрабатываем строку
                    if row and row.get('patent holders'):
                        holder = row['patent holders'].strip()
                        holders_list = [h.strip() for h in holder.split('\n') if h.strip()]
                        
                        for h in holders_list:
                            if h:  # Проверяем что не пустое
                                self.patent_holders.add(h)  # set автоматически удаляет дубликаты
                                batch.append(h)
                    
                    # Проверяем размер пакета
                    if len(batch) >= self.batch_size:
                        batch_num += 1
                        print(f"\n   📦 Сохраняем пакет #{batch_num} ({len(batch)} записей)...")
                        self.save_batch(batch)
                        self.save_checkpoint()
                        batch = []  # очищаем пакет
                
                print()  # перевод строки после прогресс-бара
                
                # Сохраняем остаток
                if batch and not self.interrupted:
                    batch_num += 1
                    print(f"\n📦 Сохраняем финальный пакет #{batch_num} ({len(batch)} записей)...")
                    self.save_batch(batch, is_final=True)
                elif self.interrupted:
                    if batch:
                        print(f"\n📦 Сохраняем последний пакет ({len(batch)} записей)...")
                        self.save_batch(batch)
                        self.save_checkpoint()
                
                # Удаляем временные файлы если обработка завершена успешно
                if not self.interrupted:
                    self.cleanup_temp_files()
                
        except Exception as e:
            print(f"\n❌ Ошибка при обработке: {e}")
            print("💾 Пытаемся сохранить промежуточные результаты...")
            if batch:
                self.save_batch(batch)
                self.save_checkpoint()
            return
        
        # Итог
        self.print_summary(total_lines)
    
    def cleanup_temp_files(self):
        """Удаляет временные файлы после успешной обработки"""
        temp_files = [self.backup_file, self.output_file + '.checkpoint']
        for temp_file in temp_files:
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                    print(f"   🧹 Удален временный файл: {temp_file}")
                except:
                    pass
    
    def print_summary(self, total_lines):
        """Выводит итоговую статистику"""
        print("\n" + "=" * 60)
        if self.interrupted:
            print("⚠️  ПРОЦЕСС ПРЕРВАН ДОСРОЧНО")
        else:
            print("✅ ОБРАБОТКА ЗАВЕРШЕНА УСПЕШНО")
        print("=" * 60)
        print("📊 СТАТИСТИКА:")
        print(f"   • Обработано записей: {self.processed_count}/{total_lines}")
        print(f"   • Найдено уникальных правообладателей: {len(self.patent_holders)}")
        print(f"   • Результат сохранен в: {self.output_file}")
        
        if os.path.exists(self.backup_file):
            print(f"   • Бэкап: {self.backup_file}")
        
        # Показываем пример результатов
        if self.patent_holders:
            print("\n📋 ПЕРВЫЕ 5 ЗАПИСЕЙ:")
            holders_list = sorted(list(self.patent_holders))[:5]
            for i, holder in enumerate(holders_list, 1):
                short_holder = holder if len(holder) < 70 else holder[:67] + "..."
                print(f"   {i}. {short_holder}")

def main():
    """Основная функция"""
    input_filename = 'invention-20260202.csv'
    output_filename = 'pravoobladateli.txt'
    
    # Можно изменить размер пакета через аргумент
    batch_size = 1000  # По умолчанию 1000 записей
    
    # Создаем парсер и запускаем обработку
    parser = PatentHolderParser(input_filename, output_filename, batch_size)
    parser.process()

if __name__ == "__main__":
    main()