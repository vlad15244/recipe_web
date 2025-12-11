@echo off
title Django and Uvicorn Launcher

:: Путь к папке вашего Django‑проекта (измените на свой!)
set DJANGO_PROJECT_DIR=C:\Users\vlad\opc


:: Порт для Django (по умолчанию 8000)
set DJANGO_PORT=8000


:: Порт для Uvicorn (по умолчанию 8001)
set UVICORN_PORT=8001

:: Имя ASGI‑приложения в вашем проекте (обычно: <имя_проекта>.asgi:application)
set ASGI_APP=opc.asgi:application


echo Запускаю Django на порту %DJANGO_PORT%...
start "Django Development Server" cmd /k "cd /d %DJANGO_PROJECT_DIR% && python manage.py runserver %DJANGO_PORT%"


echo Запускаю Uvicorn на порту %UVICORN_PORT%...
start "Uvicorn ASGI Server" cmd /k "cd /d %DJANGO_PROJECT_DIR% && python -m uvicorn %ASGI_APP% --port %UVICORN_PORT% --reload"


echo Оба сервера запущены!
pause
