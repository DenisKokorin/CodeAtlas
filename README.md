# CodeAtlas

CodeAtlas — backend API для анализа GitHub-репозиториев и генерации документации по их структуре и содержимому.

Проект позволяет:

* добавлять GitHub-репозитории;
* получать информацию о репозитории;
* генерировать Markdown-документацию;
* хранить результат генерации;
* работать с API через Swagger UI;
* использовать JWT-авторизацию для защиты основных эндпоинтов.

## Локальный запуск backend

Перейдите в папку backend:

```bash
cd backend
```

Создайте виртуальное окружение:

```bash
python -m venv venv
```

Активируйте виртуальное окружение:

```bash
.\venv\Scripts\activate
```

Установите зависимости:

```bash
pip install -r requirements.txt
```

Создайте файл `.env` на основе `.env.example`:

```bash
copy .env.example .env
```

Запустите backend:

```bash
python uvicorn app.main:app --reload
```

После запуска API будет доступно по адресу:

```text
http://127.0.0.1:8000
```

## Swagger UI

Swagger UI доступен по адресу:

```text
http://127.0.0.1:8000/docs
```

Swagger защищён через Basic Auth, чтобы посторонние пользователи не могли просматривать и тестировать API.

Логин и пароль для локальной разработки указываются в файле `backend/.env`.

Пример значений из `.env.example`:

```env
DOCS_USERNAME=codeatlas
DOCS_PASSWORD=0000
```

Также защищён endpoint:

```text
/openapi.json
```

## Авторизация

Основные endpoints приложения используют JWT-авторизацию.

Сначала нужно зарегистрироваться или войти в систему:

```text
POST /auth/register
POST /auth/login
```

После успешной регистрации или входа backend возвращает:

```text
access_token
refresh_token
```

`access_token` нужно передавать в защищённые endpoints как Bearer token.

Пример заголовка:

```text
Authorization: Bearer <access_token>
```

## Auth endpoints

```text
POST /auth/register
POST /auth/login
POST /auth/refresh
POST /auth/logout
GET  /auth/me
```

Назначение endpoints:

* `/auth/register` — регистрация пользователя;
* `/auth/login` — вход пользователя;
* `/auth/refresh` — обновление access token через refresh token;
* `/auth/logout` — выход и отзыв refresh token;
* `/auth/me` — получение информации о текущем пользователе.

## Работа с репозиториями

Репозитории привязаны к пользователю через `owner_id`.

Пользователь может работать только со своими репозиториями.

Основные endpoints:

```text
POST   /repositories/
GET    /repositories/
GET    /repositories/{repository_id}
PUT    /repositories/{repository_id}
DELETE /repositories/{repository_id}
```

Для генерации и получения документации используются endpoints:

```text
POST /repositories/{repository_id}/generate-documentation
GET  /repositories/{repository_id}/documentation
```

## GitHub-интеграция

Backend умеет получать информацию о GitHub-репозитории через GitHub API.

Для этого используется endpoint:

```text
GET /external/github/repository-info
```

Если требуется GitHub API token, его можно указать в `.env`:

```env
GITHUB_API_TOKEN=
```

## Генерация документации

Генерация документации может работать через mock provider или Gemini provider.

Настройка provider выполняется через переменную окружения:

```env
DOCUMENTATION_PROVIDER=mock
```

Для Gemini нужно указать API-ключ:

```env
GEMINI_API_KEY=
GEMINI_MODEL=gemini-2.5-flash-lite
```

Mock provider используется для локальной разработки и тестирования без внешнего API.

## Переменные окружения

Основные переменные окружения находятся в файле:

```text
backend/.env.example
```

Перед запуском проекта нужно создать локальный `.env`:

```bash
copy .env.example .env
```