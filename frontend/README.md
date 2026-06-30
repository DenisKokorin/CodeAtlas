# CodeAtlas Frontend

Frontend-приложение для CodeAtlas на React + TypeScript + Vite. Для редактирования документации используется MDXEditor.

## Локальный запуск

```bash
cd frontend
npm install
npm install @mdxeditor/editor
npm run dev
```

По умолчанию frontend обращается к backend по адресу:

```text
http://127.0.0.1:8000
```

Если backend запущен на другом адресе, создайте файл `.env` в папке `frontend`:

```env
VITE_API_URL=http://127.0.0.1:8000
```

## Сборка

```bash
npm run build
```


## Редактирование документации

Во frontend подключён `@mdxeditor/editor`. Он используется на странице репозитория для ручного редактирования Markdown-документации.

Если зависимости уже были установлены до добавления редактора, выполните в папке `frontend`:

```bash
npm install @mdxeditor/editor
```

После сохранения frontend отправляет изменённый Markdown на backend endpoint:

```text
PUT /repositories/{repository_id}/documentation/versions/{version_id}/content
```

Редактируется только основная Markdown-документация. Business Summary, Critical Parts и Quality Assessment остаются неизменными.
