FROM python:3.11-slim

# Установка зависимостей системы
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Установка переменных окружения
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Создание рабочей директории
WORKDIR /app

# Копирование зависимостей
COPY ../tiretrack/requirements.txt /app/

# Установка зависимостей Python
RUN pip install --no-cache-dir -r requirements.txt

# Копирование кода приложения
COPY . /app/

# Создание директории для статических файлов
RUN mkdir -p /app/staticfiles

# Создание директории для медиа файлов
RUN mkdir -p /app/media

# Открытие порта
EXPOSE 8000

# Команда для запуска приложения
CMD ["gunicorn", "tiretrack.wsgi:application", "--bind", "0.0.0.0:8000"]