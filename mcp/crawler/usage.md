# Использование Crawler Service

## Архитектура

Сервис предоставляет **два независимых HTTP-сервера** в одном контейнере:

| Интерфейс      | Порт                      | Технология      | Назначение                |
|----------------|---------------------------|-----------------|---------------------------|
| Flask REST API | `8000` (CRAWLER_PORT)     | gunicorn        | HTTP API (`/api/*`)       |
| FastMCP SSE    | `8100` (MCP_PORT)         | uvicorn         | MCP Streaming HTTP        |

FastMCP использует **SSE (Server-Sent Events)** — streaming HTTP транспорт,
который поддерживает долгоживущее соединение для MCP-клиентов.

---

## 1. Настройка MCP-клиента (mcp.json)

### Для LM Studio

LM Studio подключается к MCP-серверу через SSE-транспорт.
Укажите URL FastMCP SSE сервера:

```json
{
  "mcpServers": {
    "crawler": {
      "type": "url",
      "url": "http://localhost:8100"
    }
  }
}
```

> **Важно:** Указывайте именно MCP-порт (8100), а не порт Flask API (8000).

### Для Claude Desktop

Claude Desktop поддерживает SSE-подключения:

```json
{
  "mcpServers": {
    "crawler": {
      "type": "url",
      "url": "http://localhost:8100"
    }
  }
}
```

### Для VS Code (Cline / Continue)

```json
{
  "mcpServers": {
    "crawler": {
      "type": "url",
      "url": "http://localhost:8100"
    }
  }
}
```

### Для Python (прямой вызов через MCP SDK)

```python
from mcp import ClientSession
from mcp.client.sse import sse_client

async def main():
    async with sse_client("http://localhost:8100") as streams:
        async with ClientSession(*streams) as session:
            result = await session.call_tool("search", {
                "query": "python asyncio",
                "top_k": 5
            })
            print(result.content)
```

---

## 2. Доступные MCP инструменты

### 2.1. search — поиск без загрузки

```json
{
  "tool": "search",
  "input": {
    "query": "machine learning",
    "top_k": 5
  }
}
```

**Параметры:**

| Параметр | Тип  | По умолч. | Описание                |
|----------|------|-----------|-------------------------|
| `query`  | str  | —         | Поисковый запрос        |
| `top_k`  | int  | 10        | Количество результатов (1-50) |

**Ответ:**

```json
{
  "content": "**Результаты поиска по запросу «machine learning»:**\n\n1. [Title](url) — snippet...",
  "artifacts": [
    {
      "type": "search_result",
      "url": "https://...",
      "title": "...",
      "snippet": "...",
      "engine": "google",
      "score": 0.92
    }
  ],
  "meta": {
    "total_results": 5,
    "query": "machine learning",
    "top_k": 5,
    "elapsed_ms": 234
  }
}
```

### 2.2. fetch_page — загрузить одну страницу

```json
{
  "tool": "fetch_page",
  "input": {
    "url": "https://example.com"
  }
}
```

**Параметры:**

| Параметр | Тип  | По умолч. | Описание          |
|----------|------|-----------|-------------------|
| `url`    | str  | —         | URL для загрузки  |

**Ответ:**

```json
{
  "content": "**Страница:** Example Domain\n\nThis domain is for use...\n\n*Сохранено: html → /data/html/..., txt → /data/txt/...*",
  "artifacts": [
    {
      "type": "page",
      "url": "https://example.com",
      "title": "Example Domain",
      "text_length": 1245,
      "html_path": "/data/html/abc.html",
      "text_path": "/data/txt/abc.txt",
      "fetch_time_ms": 1200
    }
  ],
  "meta": {
    "fetch_time_ms": 1200,
    "text_bytes": 1245,
    "extracted": true,
    "elapsed_ms": 1250
  }
}
```

### 2.3. crawl — поиск → загрузка → извлечение → сохранение

```json
{
  "tool": "crawl",
  "input": {
    "query": "python asyncio",
    "top_k": 3
  }
}
```

**Параметры:**

| Параметр | Тип  | По умолч. | Описание                    |
|----------|------|-----------|-----------------------------|
| `query`  | str  | —         | Поисковый запрос            |
| `top_k`  | int  | 5         | Сколько страниц обойти (max 20) |

**Ответ:**

```json
{
  "content": "**Обход по запросу «python asyncio» завершён.**\n\n- Найдено результатов: 3\n- Успешно загружено: 3\n- Извлечено текста: 3\n- Всего текста: 45000 байт\n- Время: 3450 мс",
  "artifacts": [
    {
      "type": "page",
      "url": "https://docs.python.org/3/library/asyncio.html",
      "title": "asyncio — Asynchronous I/O",
      "status": "success",
      "text_length": 15000,
      "html_path": "/data/html/abc.html",
      "text_path": "/data/txt/abc.txt"
    }
  ],
  "meta": {
    "total_results": 3,
    "total_fetched": 3,
    "total_extracted": 3,
    "total_text_bytes": 45000,
    "total_time_ms": 3450,
    "query": "python asyncio",
    "top_k": 3
  }
}
```

---

## 3. HTTP REST API (порт 8000)

Базовый URL: `http://localhost:8000` (или `http://crawler:8000` внутри Docker)

### 3.1. Healthcheck

```bash
curl http://localhost:8000/api/health
```

**Ответ:**

```json
{
  "status": "ok"
}
```

### 3.2. Поиск (`GET /api/search`)

Прокси к SearXNG. Возвращает ссылки и сниппеты без загрузки страниц.

```bash
curl "http://localhost:8000/api/search?q=python+asyncio&top_k=5"
```

**Параметры:**

| Параметр | Тип  | По умолч. | Описание                |
|----------|------|-----------|-------------------------|
| `q`      | str  | —         | Поисковый запрос        |
| `top_k`  | int  | 10        | Количество результатов   |

### 3.3. Загрузка одной страницы (`GET /api/fetch`)

Загружает URL → извлекает контент (trafilatura + readability) → сохраняет HTML и TXT на диск.

```bash
curl "http://localhost:8000/api/fetch?url=https://example.com"
```

### 3.4. Полный обход (`POST /api/crawl`)

Поиск → загрузка всех результатов → извлечение → сохранение.

```bash
curl -X POST http://localhost:8000/api/crawl \
  -H "Content-Type: application/json" \
  -d '{"query": "fastapi tutorial", "top_k": 3}'
```

---

## 4. Пример использования из MCP-клиента (Claude Desktop / LM Studio)

При настройке `mcp.json` как указано выше, можно отправить сообщение агенту:

> "Найди информацию по fastapi и сохрани результаты"

Агент автоматически вызовет `crawl` с параметрами:

```json
{
  "query": "fastapi",
  "top_k": 5
}
```

---

## 5. Пример использования из Python (MCP SDK)

```python
import asyncio
from mcp import ClientSession
from mcp.client.sse import sse_client


async def search_example():
    async with sse_client("http://localhost:8100") as streams:
        async with ClientSession(*streams) as session:
            # Поиск
            result = await session.call_tool("search", {
                "query": "docker compose",
                "top_k": 3
            })
            print(result.content)

            # Загрузка страницы
            result = await session.call_tool("fetch_page", {
                "url": "https://docs.docker.com/compose/"
            })
            print(result.content)

            # Полный обход
            result = await session.call_tool("crawl", {
                "query": "docker compose",
                "top_k": 2
            })
            print(result.content)


asyncio.run(search_example())
```

---

## 6. Docker

### Запуск через Docker Compose

```bash
cd crawler
docker compose up -d --build
```

После запуска будут доступны:

- Flask API: `http://localhost:8000`
- MCP SSE: `http://localhost:8100`

### Переменные окружения

| Переменная          | По умолч.     | Описание                          |
|---------------------|---------------|-----------------------------------|
| `CRAWLER_PORT`      | `8000`        | Порт Flask API                    |
| `MCP_PORT`          | `8100`        | Порт FastMCP SSE                  |
| `SEARXNG_URL`       | `searxng:8080`| Адрес SearXNG внутри сети Docker  |
| `DATA_PATH`         | `/data`       | Путь к данным на хосте            |
| `LOG_LEVEL`         | `INFO`        | Уровень логирования               |
| `GUNICORN_WORKERS`  | `4`           | Количество gunicorn-воркеров      |
| `MAX_CONCURRENCY`   | `10`          | Макс. параллельных fetch          |
| `FETCH_TIMEOUT`     | `15`          | Таймаут HTTP запроса (сек)        |
| `FETCH_RETRIES`     | `2`           | Кол-во повторов при ошибке fetch  |
| `PLAYWRIGHT_ENABLED`| `false`       | Включить Playwright fallback      |
| `SOCKS5_PROXY`      | —             | SOCKS5 прокси (опционально)       |

---

## 7. Лимиты и ограничения

| Инструмент  | Параметр | Минимум | Максимум |
|-------------|----------|---------|----------|
| search      | `top_k`  | 1       | 50       |
| crawl       | `top_k`  | 1       | 20       |
| fetch_page  | —        | —       | —        |

- Сервис использует `SearXNG` в качестве поискового движка.
- Извлечение контента: `trafilatura` + `readability`.
- Сохранённые HTML и TXT хранятся в каталоге, указанном в `DATA_PATH` (по умолчанию `/data`).
- Логи пишутся в JSON-файл в `/data/access.log`.
- Все вызовы MCP инструментов логируются в stdout/stderr контейнера.