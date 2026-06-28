# CodeAtlas

CodeAtlas — backend API для анализа GitHub-репозиториев и генерации документации по их структуре и содержимому.

Проект позволяет:

* добавлять GitHub-репозитории;
* получать информацию о репозитории;
* генерировать Markdown-документацию;
* хранить документацию по версиям приложения и ревизиям;
* получать Business Summary для руководителя;
* получать описание наиболее критичных частей проекта (Critical Parts);
* получать общую оценку проекта по инфраструктурным признакам (Quality Assessment);
* экспортировать документацию в разных форматах;
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
python -m uvicorn app.main:app --reload
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

Для генерации и получения актуальной документации используются endpoints:

```text
POST /repositories/{repository_id}/generate-documentation
GET  /repositories/{repository_id}/documentation
```

При генерации документации нужно вручную указать версию приложения:

```json
{
  "app_version": "1.0.0"
}
```

## Управление версиями документации

CodeAtlas хранит документацию по версиям приложения.

Пользователь вручную указывает `app_version` при генерации документации. Например:

```text
App version 1.0.0
```

Если для этой версии приложения документация генерируется впервые, создаётся первая ревизия:

```text
Documentation 1.0.0 revision 1
```

Если документация повторно генерируется для той же версии приложения, создаётся новая ревизия:

```text
Documentation 1.0.0 revision 2
```

Если пользователь указывает новую версию приложения, ревизии для неё начинаются заново:

```text
Documentation 1.1.0 revision 1
```

Последняя созданная документация считается актуальной и отдаётся через:

```text
GET /repositories/{repository_id}/documentation
```

Для просмотра истории версий используются endpoints:

```text
GET /repositories/{repository_id}/documentation/versions
GET /repositories/{repository_id}/documentation/versions/{version_id}
```

## Business Summary, Critical Parts и оценка проекта

При генерации документации backend получает от LLM не один общий Markdown-текст, а структурированный результат:

```text
documentation_markdown
business_summary
quality_assessment
critical_parts
```

`documentation_markdown` хранится и используется как основная техническая документация. `business_summary`, `quality_assessment` и `critical_parts` сохраняются отдельно для конкретной версии документации.

Business Summary можно получить через endpoint:

```text
GET /repositories/{repository_id}/business-summary
```

Этот endpoint возвращает краткое описание проекта для руководителя или заказчика: что делает система, кому она полезна и какую ценность даёт.

Critical Parts можно получить через endpoint:

```text
GET /repositories/{repository_id}/critical-parts
```

Этот endpoint возвращает описание наиболее критичных частей проекта — какие модули наиболее важны, почему, и какие файлы к ним относятся. В mock-режиме анализ выполняется автоматически по структуре репозитория. При использовании Gemini анализ выполняет LLM на основе предоставленного контекста.

Общую оценку проекта можно получить через endpoint:

```text
GET /repositories/{repository_id}/quality-assessment
```

Оценка проекта возвращается в JSON-формате и может использоваться frontend-ом для dashboard. В ответ входят:

```text
score
max_score
score_label
summary
criteria
strengths
risks
recommendations
```

Часть критериев backend определяет сам по структуре репозитория:

```text
has_readme
has_tests
has_ci_cd
has_docker
has_env_example
has_dependency_manifest
has_clear_structure
```

Для конкретной версии документации доступны endpoints:

```text
GET /repositories/{repository_id}/documentation/versions/{version_id}/business-summary
GET /repositories/{repository_id}/documentation/versions/{version_id}/quality-assessment
GET /repositories/{repository_id}/documentation/versions/{version_id}/critical-parts
```

По умолчанию endpoints без `version_id` возвращают Business Summary, Critical Parts и оценку для актуальной версии документации.

Мультиформатный экспорт применяется только к основной Markdown-документации. Business Summary, Critical Parts и Quality Assessment не добавляются в экспортируемые файлы автоматически и отдаются отдельными JSON endpoints.

## Мультиформатный экспорт

Документация хранится в базе в Markdown-формате. Остальные форматы не сохраняются отдельно, а генерируются на лету при экспорте.

Поддерживаемые форматы:

```text
markdown
txt
html
docx
json
```

Экспорт актуальной документации:

```text
GET /repositories/{repository_id}/export?format=docx
```

Экспорт конкретной версии документации:

```text
GET /repositories/{repository_id}/documentation/versions/{version_id}/export?format=docx
```

Примеры:

```text
GET /repositories/1/export?format=markdown
GET /repositories/1/export?format=html
GET /repositories/1/documentation/versions/2/export?format=docx
GET /repositories/1/documentation/versions/2/export?format=json
```

## GitHub-интеграция

Backend умеет получать информацию о GitHub-репозитории через GitHub API.

Для этого используется endpoint:

```text
GET /external/github/repository-info
```

GitHub API token можно указать в `.env`:

```env
GITHUB_API_TOKEN=
```

Для публичных репозиториев token не обязателен функционально, но рекомендуется для стабильной работы. Без token GitHub применяет небольшой лимит для неавторизованных API-запросов по IP. При активном тестировании генерации этот лимит можно быстро исчерпать, и backend не сможет получить структуру репозитория.

Если GitHub API недоступен, генерация через Gemini останавливается до вызова LLM. Это сделано специально, чтобы не генерировать документацию и оценку проекта по пустому или неполному контексту. В таком случае нужно добавить `GITHUB_API_TOKEN` в `backend/.env` или повторить запрос позже.

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

При использовании Gemini backend ожидает структурированный JSON-ответ. Если LLM вернула некорректный JSON, генерация завершается ошибкой, после чего запрос можно повторить.

Перед вызовом Gemini backend должен получить данные GitHub API: метаданные репозитория и дерево файлов. Если GitHub вернул rate limit, access denied или дерево файлов недоступно, генерация не запускается и возвращается понятная ошибка.

## Переменные окружения

Основные переменные окружения находятся в файле:

```text
backend/.env.example
```

Перед запуском проекта нужно создать локальный `.env`:

```bash
copy .env.example .env
```

Файл `.env` не должен попадать в Git.


## Примечание по генерации через Gemini JSON

Для генерации документации, Business Summary, Critical Parts и Quality Assessment backend ожидает от Gemini структурированный JSON.
Если ответ Gemini был обрезан, увеличьте значение переменной окружения:

```env
DOCUMENTATION_MAX_OUTPUT_TOKENS=12000
```

Если локальный `.env` уже был создан раньше, обновите значение вручную, потому что `.env.example` не применяется автоматически.
## Временный debug endpoint для Gemini

Для отладки структурированного ответа Gemini временно добавлен endpoint:

```text
POST /repositories/{repository_id}/debug/gemini-raw-response
```

Он использует тот же GitHub-контекст, prompt и настройки Gemini, что и обычная генерация документации, но **не сохраняет результат в базу данных**. Endpoint возвращает сырой ответ Gemini в поле `raw_response`, а также диагностические признаки:

```text
strict_json_valid
repaired_json_valid
structured_response_valid
parse_error
github_tree_items_count
github_files_used
quality_facts
```

Этот endpoint нужен только для отладки ошибок парсинга JSON.
