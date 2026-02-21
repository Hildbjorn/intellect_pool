import os
import glob

# Автоматически импортируем все формы из файлов в папке
model_files = glob.glob(os.path.dirname(__file__) + "/*.py")
for module in model_files:
    if not module.endswith('__init__.py'):
        module_name = os.path.basename(module)[:-3]
        exec(f"from .{module_name} import *")