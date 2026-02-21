import os
import glob

# Автоматически импортируем все файлы админки из папки
admin_files = glob.glob(os.path.dirname(__file__) + "/*.py")
for module in admin_files:
    if not module.endswith('__init__.py'):
        module_name = os.path.basename(module)[:-3]
        exec(f"from .{module_name} import *")