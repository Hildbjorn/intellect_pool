"""
Утилиты для работы с файлами и изображениями.
"""

import os
import re
from typing import Tuple
from PIL import Image
import pytils


class FileUtils:
    """Утилиты для работы с файлами."""
    
    @staticmethod
    def generate_file_path(
        instance, 
        filename: str, 
        directory: str = 'files'
    ) -> str:
        """
        Генерирует путь для сохранения файла.
        
        Args:
            instance: Объект модели
            filename: Имя оригинального файла
            directory: Поддиректория для файлов
            
        Returns:
            Путь для сохранения файла
        """
        try:
            # Транслитерация и очистка имени файла
            transliterated = pytils.translit.translify(filename)
            name, ext = os.path.splitext(transliterated)
            name = re.sub(r'[\W]+', '_', name.strip())
            file_name = f'{name}{ext}'.lower()
            
            # Определение имени класса
            class_name = instance.__class__.__name__.lower()
            
            # Определение именной папки
            named_folder = (
                getattr(instance, 'slug', None) or
                getattr(instance, 'nic_name', None) or
                str(getattr(instance, 'id', 'no_id'))
            )
            
            # Очистка имени папки
            if named_folder:
                named_folder = re.sub(r'[\W]+', '_', str(named_folder).strip())
            else:
                named_folder = 'no_id'
            
            # Формирование пути
            path = f'{class_name}/{named_folder}/{directory}/'
            return os.path.join(path, file_name)
            
        except Exception as e:
            # В случае ошибки возвращаем простой путь
            return f'uploads/{filename}'
    
    @staticmethod
    def resize_and_crop_image(
        image_path: str, 
        max_size: Tuple[int, int] = (150, 150),
        quality: int = 85
    ) -> None:
        """
        Изменяет размер и обрезает изображение.
        
        Оригинальная логика: 
        1. Определяем меньшую сторону изображения
        2. Масштабируем по меньшей стороне до max_size
        3. Обрезаем до нужного размера
        
        Args:
            image_path: Путь к изображению
            max_size: Максимальный размер (ширина, высота)
            quality: Качество JPEG (1-100)
            
        Raises:
            FileNotFoundError: Если файл не найден
            ValueError: Если размер невалидный
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Файл не найден: {image_path}")
        
        if max_size[0] <= 0 or max_size[1] <= 0:
            raise ValueError("Размер должен быть положительным числом.")
        
        try:
            with Image.open(image_path) as img:
                width, height = img.size
                
                # Определяем, какая сторона изображения меньше
                if width < height:
                    # Устанавливаем ширину в max_size[0], сохраняя пропорции
                    new_width = max_size[0]
                    new_height = int((new_width / width) * height)
                else:
                    # Устанавливаем высоту в max_size[1], сохраняя пропорции
                    new_height = max_size[1]
                    new_width = int((new_height / height) * width)
                
                # Меняем размер с сохранением пропорций
                img = img.resize((new_width, new_height), Image.LANCZOS)
                
                # Обрезка изображения по центру
                left = (new_width - max_size[0]) / 2
                right = (new_width + max_size[0]) / 2
                top = (new_height - max_size[1]) / 2
                bottom = (new_height + max_size[1]) / 2
                
                # Преобразуем в целые числа для метода crop
                left = int(left)
                top = int(top)
                right = int(right)
                bottom = int(bottom)
                
                img = img.crop((left, top, right, bottom))
                
                # Определяем формат для сохранения
                if image_path.lower().endswith(('.png', '.gif', '.bmp')):
                    img.save(image_path, optimize=True)
                else:
                    img.save(image_path, 'JPEG', quality=quality, optimize=True)
                    
        except Exception as e:
            raise RuntimeError(f"Ошибка при обработке изображения: {e}")
    
    @staticmethod
    def resize_with_transparent_background(
        image_path: str,
        max_size: Tuple[int, int] = (150, 150),
        background_color: Tuple[int, int, int, int] = (255, 255, 255, 0)
    ) -> None:
        """
        Изменяет размер изображения с прозрачным фоном.
        
        Args:
            image_path: Путь к изображению
            max_size: Максимальный размер (ширина, высота)
            background_color: Цвет фона (R, G, B, A)
            
        Raises:
            FileNotFoundError: Если файл не найден
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Файл не найден: {image_path}")
        
        try:
            with Image.open(image_path) as img:
                width, height = img.size
                
                # Определяем коэффициент масштабирования для большей стороны
                if width > height:
                    scale_factor = max_size[0] / width
                else:
                    scale_factor = max_size[1] / height
                
                # Вычисляем новые размеры
                new_width = int(width * scale_factor)
                new_height = int(height * scale_factor)
                
                # Изменяем размер изображения
                img = img.resize((new_width, new_height), Image.LANCZOS)
                
                # Создаем новое изображение с прозрачным фоном
                new_img = Image.new("RGBA", max_size, background_color)
                
                # Вычисляем координаты для размещения по центру
                left = (max_size[0] - new_width) // 2
                top = (max_size[1] - new_height) // 2
                
                # Размещаем измененное изображение на новом фоне
                if img.mode == 'RGBA':
                    new_img.paste(img, (left, top), img)
                else:
                    new_img.paste(img, (left, top))
                
                # Сохраняем результат
                new_img.save(image_path, 'PNG', optimize=True)
                
        except Exception as e:
            raise RuntimeError(f"Ошибка при обработке изображения: {e}")
    
    @staticmethod
    def remove_empty_directories(root_path: str, dry_run: bool = False) -> int:
        """
        Удаляет пустые директории.
        
        Args:
            root_path: Корневой путь для поиска
            dry_run: Режим предпросмотра (не удалять)
            
        Returns:
            Количество удаленных директорий
        """
        if not os.path.exists(root_path):
            raise FileNotFoundError(f"Директория не найдена: {root_path}")
        
        removed_count = 0
        
        try:
            for root, dirs, files in os.walk(root_path, topdown=False):
                for dir_name in dirs:
                    dir_path = os.path.join(root, dir_name)
                    
                    try:
                        if not os.listdir(dir_path):  # Директория пуста
                            if not dry_run:
                                os.rmdir(dir_path)
                                print(f'Удалена пустая папка: {dir_path}')
                            else:
                                print(f'Найдена пустая папка: {dir_path}')
                            removed_count += 1
                    except (OSError, PermissionError) as e:
                        print(f'Не удалось удалить {dir_path}: {e}')
                        continue
                        
        except Exception as e:
            print(f'Ошибка при удалении пустых директорий: {e}')
        
        return removed_count
    
    @staticmethod
    def get_file_size(file_path: str, human_readable: bool = True) -> str:
        """
        Получает размер файла.
        
        Args:
            file_path: Путь к файлу
            human_readable: Форматировать в читаемый вид
            
        Returns:
            Размер файла
        """
        try:
            size = os.path.getsize(file_path)
            
            if human_readable:
                for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
                    if size < 1024.0:
                        return f"{size:.1f} {unit}"
                    size /= 1024.0
                return f"{size:.1f} PB"
            else:
                return str(size)
                
        except (OSError, FileNotFoundError):
            return "0 B"