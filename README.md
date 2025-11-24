# Django Catalog Project

## Описание проекта

Простой веб-каталог товаров, разработанный на Django. Проект включает систему категорий и товаров с возможностью управления через административную панель.

## Функциональность

- Модели Category и Product для организации каталога товаров
- Административная панель для управления данными
- Кастомные команды для заполнения тестовыми данными
- Поддержка PostgreSQL в качестве базы данных
- Система миграций для управления схемой базы данных

## Модели данных

### Category
- Наименование (name)
- Описание (description)

### Product
- Наименование (name)
- Описание (description)
- Изображение (image)
- Категория (category) - внешний ключ к Category
- Цена за покупку (price)
- Дата создания (created_at)
- Дата последнего изменения (updated_at)

## Установка и настройка

### Предварительные требования
- Python 3.8+
- PostgreSQL
- Virtualenv (рекомендуется)

### Установка

1. Клонирование репозитория
```
git clone <repository-url> \
cd DJ_catalog
```


2. Создание виртуального окружения
```
python -m venv venv \
source venv/bin/activate # Linux/Mac \
venv\Scripts\activate # Windows
```


3. Установка зависимостей
```
3. pip install -r requirements.txt
```



4. Настройка базы данных PostgreSQL
```
CREATE DATABASE djcatalog;
CREATE USER djcatalog_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE djcatalog TO djcatalog_user;
```


5. Настройка переменных окружения
```
Создайте файл `.env` в корне проекта:
DB_NAME=djcatalog
DB_USER=djcatalog_user
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=5432
SECRET_KEY=your-secret-key
DEBUG=True
```

6. Применение миграций
python manage.py migrate

7. Создание суперпользователя
python manage.py createsuperuser

8. Запуск сервера разработки
python manage.py runserver


## Использование

### Административная панель
Доступна по адресу: http://127.0.0.1:8000/admin/

Возможности:
- Просмотр списка категорий и товаров
- Фильтрация товаров по категориям
- Поиск по наименованию и описанию
- Управление ценами и описаниями

### Кастомные команды

#### Заполнение тестовыми данными
python manage.py fill_products --count 5


Параметры:
- `--count` - количество товаров в каждой категории (по умолчанию 5)

#### Создание фикстур
```
python manage.py dumpdata catalog.Category catalog.Product --indent 2 > catalog/fixtures/catalog_data.json
```


#### Загрузка фикстур
```
python manage.py loaddata catalog_data.json
```

## Структура проекта
DJ_catalog/ \
├── catalog/ # Приложение каталога \
│ ├── management/ \
│ │ └── commands/ # Кастомные команды \
│ ├── migrations/ # Файлы миграций \
│ ├── fixtures/ # Тестовые данные \
│ ├── models.py # Модели Category и Product \
│ ├── admin.py # Настройки админ-панели \
│ └── ... \
├── myproject/ # Настройки проекта \
│ ├── settings.py # Конфигурация \
│ ├── urls.py # URL-маршруты \
│ └── ... \
├── manage.py \
└── requirements.txt

## Команды управления

### Работа с миграциями
Создание миграций

python manage.py makemigrations catalog

Применение миграций

python manage.py migrate

Просмотр статуса миграций

python manage.py showmigrations


### Работа с данными
Django shell

python manage.py shell

Создание суперпользователя

python manage.py createsuperuser

Сбор статических файлов

python manage.py collectstatic


## Настройки базы данных

Проект поддерживает как SQLite (для разработки), так и PostgreSQL (для продакшена). 
Настройки находятся в `myproject/settings.py`:
```
DATABASES = {
'default': {
'ENGINE': 'django.db.backends.postgresql',
'NAME': os.getenv('DB_NAME', 'djcatalog'),
'USER': os.getenv('DB_USER', 'djcatalog_user'),
'PASSWORD': os.getenv('DB_PASSWORD', ''),
'HOST': os.getenv('DB_HOST', 'localhost'),
'PORT': os.getenv('DB_PORT', '5432'),
}
}
```

## Разработка

### Добавление новых полей в модели
1. Внесите изменения в `catalog/models.py`
2. Создайте миграцию: `python manage.py makemigrations catalog`
3. Примените миграцию: `python manage.py migrate`

### Создание новых кастомных команд
1. Создайте файл в `catalog/management/commands/`
2. Унаследуйте класс от `BaseCommand`
3. Реализуйте метод `handle()`

## Тестирование

Для запуска тестов выполните:
python manage.py test catalog



## Развертывание

Для развертывания в production:
1. Установите `DEBUG=False` в настройках
2. Настройте веб-сервер (Nginx + Gunicorn)
3. Настройте статические файлы
4. Используйте PostgreSQL в production
5. Настройте брандмауэр и SSL

## Лицензия

Этот проект распространяется под лицензией MIT.