import os
import glob

# Автоматически импортируем все views из файлов в папке
views_files = glob.glob(os.path.dirname(__file__) + "/*.py")
for module in views_files:
    if not module.endswith('__init__.py'):
        module_name = os.path.basename(module)[:-3]
        exec(f"from .{module_name} import *")