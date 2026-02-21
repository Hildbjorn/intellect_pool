import os
from pathlib import Path

def create_project_dump(project_root, output_dir, exclude_dirs=None):
    # Добавляем исключаемые папки
    if exclude_dirs is None:
        exclude_dirs = ['.idea', '.vscode', '', 'env', 'venv', '.git',
                      '__pycache__', 'node_modules', 'media', 'static',
                      'staticfiles', 'migrations']
    
    # Создаем директорию для выходных файлов, если ее нет
    os.makedirs(output_dir, exist_ok=True)

    # Получаем список всех папок в корне проекта (кроме исключенных)
    target_dirs = [d for d in os.listdir(project_root) 
                  if os.path.isdir(os.path.join(project_root, d)) and d not in exclude_dirs]

    for target_dir in target_dirs:
        target_path = os.path.join(project_root, target_dir)
        output_filename = f"{target_dir}.md"
        output_path = os.path.join(output_dir, output_filename)
        
        file_contents = []
        
        for root, dirs, files in os.walk(target_path):
            # Исключаем ненужные директории
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            
            for file in files:
                # Пропускаем manage.py и SQLite файлы
                if file == 'manage.py' or file.endswith('.sqlite3'):
                    continue

                file_path = os.path.join(root, file)
                relative_path = os.path.relpath(file_path, target_path)

                try:
                    with open(file_path, 'r', encoding='utf-8') as infile:
                        content = infile.read()
                except UnicodeDecodeError:
                    content = f"!!! Файл содержит бинарные данные и не может быть прочитан !!!"
                except Exception as e:
                    content = f"!!! Ошибка при чтении файла: {str(e)} !!!"

                file_entry = f"# Файл: {relative_path}\n\n```\n{content}\n```\n"
                file_contents.append(file_entry)
        
        if file_contents:
            with open(output_path, 'w', encoding='utf-8') as outfile:
                outfile.write("\n\n-----\n\n".join(file_contents))
            print(f"Создан файл: {output_filename}")
        else:
            print(f"Нет файлов для папки: {target_dir}")
    
    print(f"\nДамп проекта создан в директории: {output_dir}")

if __name__ == "__main__":
    # Определяем путь к корневой папке проекта (../../src относительно расположения скрипта)
    script_dir = Path(__file__).parent.resolve()
    project_root = script_dir.parent.parent / "src"
    
    if not project_root.exists():
        raise FileNotFoundError(f"Не найдена корневая папка проекта по пути: {project_root}")
    
    output_directory = "project_dumps"
    
    print(f"Обрабатываю папку проекта: {project_root}")
    create_project_dump(project_root, output_directory)
    print(f"Готово! Файлы дампа находятся в папке: {output_directory}")