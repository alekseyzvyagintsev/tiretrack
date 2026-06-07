# Система управления QR-кодами грузовых шин (Django версия)

## Описание

Полнофункциональная система управления QR-кодами грузовых шин на базе Django с интеграцией системы "Честный Знак". Приложение включает в себя REST API, асинхронную обработку задач с Celery, PostgreSQL в качестве базы данных и Redis для кэширования.

## Основные функции

1. Управление пользователями с кастомной моделью (email как основной идентификатор)
2. Импорт QR-кодов из текстовых файлов и PDF
3. Интеграция с системой "Честный Знак" (В процессе разработки)
4. Управление владельцами шин (Эксклюзив, поставщики, ответственное хранение)
5. Отслеживание поступлений и выбытий
6. Управление статусами шин (внутренний, промежуточный, внешний)
7. Экспорт QR-кодов для сканеров ТСД
8. Асинхронная обработка задач с Celery
9. REST API для интеграции

## Технологии

- Django 4.2
- Django REST Framework
- PostgreSQL
- Redis
- Celery
- Docker и Docker Compose
- Gunicorn

## Структура проекта

```
tiretrack/
├── tiretrack/              # Основной проект Django
│   ├── settings.py          # Конфигурация
│   ├── urls.py             # URL маршруты
│   └── wsgi.py             # WSGI конфигурация
├── users/                  # Приложение пользователей
├── tires/                  # Приложение управления шинами
├── qr_processing/          # Приложение обработки QR-кодов
├── manage.py              # Утилита управления Django
├── requirements.txt         # Зависимости
├── Dockerfile             # Docker конфигурация
├── docker-compose.yml     # Оркестрация контейнеров
└── README.md              # Документация
```

## Установка и запуск

### С использованием Docker (рекомендуется)

1. Клонируйте репозиторий:
   ```bash
   git clone https://github.com/alekseyzvyagintsev/tiretrack.git
   cd tire-management-django
   ```

2. Создайте .env файл на основе примера:
   ```bash
   cp .env.example .env
   ```

3. Запустите приложение с помощью Docker Compose:
   ```bash
   docker-compose up -d
   ```

4. Выполните миграции базы данных:
   ```bash
   docker-compose exec web python manage.py migrate
   ```

5. Создайте суперпользователя:
   ```bash
   docker-compose exec web python manage.py createsuperuser
   ```

6. Инициализируйте базовых владельцев:
   ```bash
   docker-compose exec web python manage.py init_owners
   ```

### Без Docker

1. Создайте виртуальное окружение:
   ```bash
   python -m venv venv
   source venv/bin/activate  # На Windows: venv\Scripts\activate
   ```

2. Установите зависимости:
   ```bash
   pip install -r requirements.txt
   ```

3. Создайте .env файл и настройте параметры подключения к базе данных

4. Выполните миграции:
   ```bash
   python manage.py migrate
   ```

5. Создайте суперпользователя:
   ```bash
   python manage.py createsuperuser
   ```

6. Инициализируйте базовых владельцев:
   ```bash
   python manage.py init_owners
   ```

7. Запустите сервер разработки:
   ```bash
   python manage.py runserver
   ```

8. В отдельном терминале запустите Celery worker:
   ```bash
   celery -A tiretrack worker --loglevel=info
   ```

## API endpoints

### Пользователи
- `POST /api/users/register/` - Регистрация пользователя
- `POST /api/users/login/` - Аутентификация
- `POST /api/users/logout/` - Выход

### Шины
- `GET /api/tires/owners/` - Список владельцев
- `POST /api/tires/owners/` - Создание владельца
- `GET /api/tires/tires/` - Список шин
- `POST /api/tires/tires/` - Создание шины
- `POST /api/tires/transfers/` - Передача шины
- `GET /api/tires/transfers/history/` - История передач

### Обработка QR-кодов
- `POST /api/qr/imports/` - Импорт файла с QR-кодами
- `GET /api/qr/imports/list/` - Список импортов
- `GET /api/qr/qr-data/` - Данные QR-кодов
- `GET /api/qr/exports/` - Список экспортов
- `POST /api/qr/exports/` - Создание экспорта

## Разработка

### Запуск тестов
```bash
python manage.py test
```

### Создание миграций
```bash
python manage.py makemigrations
python manage.py migrate
```

## Лицензия

MIT

## Автор и поддержка

**Разработчик**: Alexey Zvyagintsev
**Email**: alex0236889@gmail.com
**GitHub**: https://github.com/alekseyzvyagintsev/tiretrack

Для вопросов, предложений или сообщений об ошибках, пожалуйста, свяжитесь с разработчиком по-указанному email, все предложения по улучшению приветствуются.
