# HTTP-клиент и сервер с графическим интерфейсом на Python

Десктопное приложение на Python (`tkinter`), реализующее HTTP/1.1 клиент и многопоточный HTTP-сервер поверх чистых TCP/SSL-сокетов (`socket`, `ssl`, `threading`).

## Установка и запуск

```bash
# Установка зависимостей (тесты и линтер)
pip install -r requirements.txt

# Запуск графического приложения
python -m src.main

# Запуск всех тестов (unit + интеграционные)
pytest tests/ -v

# Проверка кода линтером
flake8 src/ tests/