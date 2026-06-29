# CodeAtlas Frontend

Frontend-приложение для CodeAtlas на React + TypeScript + Vite.

## Локальный запуск

```bash
cd frontend
npm install
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
