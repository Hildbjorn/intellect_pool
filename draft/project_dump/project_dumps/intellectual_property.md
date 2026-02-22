# Файл: apps.py

```
from django.apps import AppConfig


class IntellectualPropertyConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'intellectual_property'
    verbose_name = 'Результаты интеллектуальной деятельности'

```


-----

# Файл: tests.py

```
from django.test import TestCase

# Create your tests here.

```


-----

# Файл: urls.py

```
from django.urls import path


# Маршруты результатов интеллектуальной собственности
urlpatterns = [
]
```


-----

# Файл: __init__.py

```

```


-----

# Файл: admin\__init__.py

```
import os
import glob

# Автоматически импортируем все файлы админки из папки
admin_files = glob.glob(os.path.dirname(__file__) + "/*.py")
for module in admin_files:
    if not module.endswith('__init__.py'):
        module_name = os.path.basename(module)[:-3]
        exec(f"from .{module_name} import *")
```


-----

# Файл: forms\__init__.py

```
import os
import glob

# Автоматически импортируем все формы из файлов в папке
model_files = glob.glob(os.path.dirname(__file__) + "/*.py")
for module in model_files:
    if not module.endswith('__init__.py'):
        module_name = os.path.basename(module)[:-3]
        exec(f"from .{module_name} import *")
```


-----

# Файл: models\__init__.py

```
import os
import glob

# Автоматически импортируем все модели из файлов в папке
model_files = glob.glob(os.path.dirname(__file__) + "/*.py")
for module in model_files:
    if not module.endswith('__init__.py'):
        module_name = os.path.basename(module)[:-3]
        exec(f"from .{module_name} import *")
```


-----

# Файл: views\__init__.py

```

```
