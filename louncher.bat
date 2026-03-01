@echo off

REM Активация виртуального окружения
call env\Scripts\activate

REM Запуск сервиса Django
cd src
start python manage.py runserver

REM Открытие сервиса в браузере
start "" http://localhost:8000

