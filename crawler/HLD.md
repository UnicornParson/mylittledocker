# High-Level Design: crawler_endpoint

## 1. Overview

crawler_endpoint — локальный orchestration-сервис, промежуточный слой между:

- **SearXNG** — поиск и discovery URL
- **Web** — fetch страниц (HTTP / Playwright)
- **Storage** — локальное сохранение контента на диск
- **LLM Agents** — потребители данных через MCP

Сервис предоставляет два интерфейса на одном порту (единый Flask-сервер):

- HTTP REST API (`/api/*`)
- MCP API (`/mcp/*`)

Оба интерфейса используют общие внутренние сервисы через **Service Layer** (явный DI).

---

## 2. Goals

- Единая точка доступа к поиску + crawling
- Детерминированное сохранение всех результатов (sha256(content) — идемпотентность)
- Полная наблюдаемость (structured logs + persisted data)
- Поддержка LLM-агентов через MCP protocol
- Простота расширения pipeline (rerank, embeddings, caching — pluggable steps)

---

## 3. System Architecture

```
┌────────────────────────────┐
│        LLM Agent           │
└────────────┬───────────────┘
             │
   ┌─────────┴──────────────────┐
   │     crawler_endpoint       │
   │     (Flask + gunicorn)     │
   │                            │
   │  ┌──────────────┐         │
   │  │ Flask API     │         │
   │  │ /api/*        │         │
   │  └──────┬───────┘         │
   │  ┌──────▼───────┐         │
   │  │ MCP Router    │         │
   │  │ /mcp/*        │         │
   │  └──────┬───────┘         │
   │         │                  │
   │  ┌──────▼──────────────┐  │
   │  │   Service Layer     │  │
   │  │   (DI container)    │  │
   │  └──────┬──────────────┘  │
   │         │                  │
   │  ┌──────▼───────┐        │
   │  │ SearchClient  │ ←── SearXNG
   │  └──────┬───────┘        │
   │         │                  │
   │  ┌──────▼───────┐        │
   │  │ FetchEngine   │ ──→ HTTP / Playwright
   │  └──────┬───────┘        │
   │         │                  │
   │  ┌──────▼───────┐        │
   │  │ Extractor     │        │
   │  │ (trafilatura) │        │
   │  └──────┬───────┘        │
   │         │                  │
   │  ┌──────▼───────┐        │
   │  │ StorageLayer  │ ──→ /data
   │  └──────────────┘        │
   └──────────────────────────┘
```

---

## 4. Module Structure (Python package)

```
crawler_endpoint/
├── __init__.py
├── __main__.py            # entrypoint: gunicorn --bind 0.0.0.0:8000 ...
├── app.py                 # Flask app factory (create_app)
├── config.py              # pydantic-settings (load env → settings object)
├── di.py                  # simple DI container / service wiring
├── models.py              # dataclasses / pydantic models (SearchResult, CrawlResult, etc.)
├── routes/
│   ├── __init__.py
│   ├── api.py             # Flask blueprint /api/*
│   └── mcp.py             # Flask blueprint /mcp/*
├── services/
│   ├── __init__.py
│   ├── search_client.py   # SearXNG HTTP client
│   ├── fetch_engine.py    # async fetch (httpx) + optional Playwright
│   ├── extractor.py       # trafilatura + readability fallback
│   ├── storage.py         # filesystem storage /data
│   └── logger.py          # structured logging
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_search.py
│   ├── test_fetch.py
│   ├── test_extractor.py
│   └── test_storage.py
└── requirements.txt
```

---

## 5. Configuration (pydantic-settings)

| Variable         | Default               | Description                |
|------------------|-----------------------|----------------------------|
| `SEARXNG_URL`    | `http://searxng:8080` | SearXNG internal endpoint  |
| `DATA_PATH`      | `/data`               | Storage root               |
| `LOG_PATH`       | `/data/access.log`    | Path to access log         |
| `MAX_CONCURRENCY` | `10`                  | Max parallel fetch workers |
| `FETCH_TIMEOUT`  | `15`                  | HTTP timeout (seconds)     |
| `FETCH_RETRIES`  | `2`                   | Retry count                |
| `PLAYWRIGHT_ENABLED` | `false`           | Enable Playwright fallback |
| `LOG_LEVEL`      | `INFO`                | Logging level              |

---

## 6. Data Models

### SearchResult
```python
@dataclass
class SearchResult:
    url: str
    title: str
    snippet: str
    engine: str
    score: float
```

### CrawlResult
```python
@dataclass
class CrawlResult:
    url: str
    title: str | None
    text: str
    html_path: str       # /data/pages/<sha256>.html
    text_path: str       # /data/pages/<sha256>.txt
    fetch_time_ms: int
    extracted_with: str  # "trafilatura" | "readability"
```

### ManifestEntry (manifest.json)
```json
{
  "url": "https://...",
  "hash": "sha256hex",
  "title": "...",
  "fetched_at": "2026-07-02T17:00:00Z",
  "fetch_time_ms": 1234,
  "extracted_with": "trafilatura",
  "text_bytes": 54321
}
```

---

## 7. API Design

### 7.1 Flask REST API

Base path: `/api`

#### `POST /api/crawl`
Поиск → fetch → extract → save → вернуть результаты.

```json
{
  "query": "linux kernel tuning",
  "top_k": 5
}
```

Response:
```json
{
  "query": "linux kernel tuning",
  "results": [
    {
      "url": "https://kernel.org/doc/...",
      "title": "Linux Kernel Documentation",
      "text": "...",
      "text_path": "/data/pages/abc123.txt"
    }
  ],
  "total_fetched": 5,
  "total_time_ms": 3450
}
```

#### `GET /api/search`
Прокси к SearXNG (format=json). Возвращает сырые URL без fetch.

```json
// Query: ?q=linux&top_k=10
// Response:
{
  "query": "linux",
  "results": [
    {"url": "...", "title": "...", "snippet": "..."}
  ]
}
```

#### `GET /api/fetch`
Fetch одного URL + extract.

```json
// Query: ?url=https://kernel.org/
// Response:
{
  "url": "https://kernel.org/",
  "title": "The Linux Kernel Archives",
  "text": "...",
  "text_path": "/data/pages/def456.txt"
}
```

---

### 7.2 MCP API

Base path: `/mcp`

#### `POST /mcp/tools/call`

Tool schema:

| Tool        | Description                                      |
|-------------|--------------------------------------------------|
| `search`    | Поиск по SearXNG, без fetch                     |
| `crawl`     | Поиск → fetch всех результатов → extract → save |
| `fetch_page`| Fetch одного URL → extract → save               |

Пример вызова `crawl`:

```json
{
  "tool": "crawl",
  "input": {
    "query": "linux kernel tuning",
    "top_k": 5
  }
}
```

Response:
```json
{
  "content": "Crawled 5 pages from query 'linux kernel tuning'",
  "artifacts": [
    {"type": "text", "path": "/data/pages/abc123.txt"},
    {"type": "text", "path": "/data/pages/def456.txt"}
  ],
  "meta": {
    "total_fetched": 5,
    "total_time_ms": 3450
  }
}
```

---

## 8. Core Modules

### 8.1 SearchClient
- HTTP client к SearXNG (`httpx.AsyncClient`)
- Нормализация ответа: `SearchResult` list
- Дедупликация URL (canonicalization: strip tracking params)
- Timeout: 10s

### 8.2 FetchEngine
- `asyncio` + `httpx.AsyncClient` для параллельного fetch
- Semaphore: `MAX_CONCURRENCY` (default 10)
- Retry: `FETCH_RETRIES` attempts с exponential backoff
- Timeout: `FETCH_TIMEOUT` seconds
- Playwright fallback: если `PLAYWRIGHT_ENABLED=true` и HTTP fetch вернул JS-heavy страницу

### 8.3 Extractor
- Primary: `trafilatura.extract()`
- Fallback: `readability.Document.summary()` (html2text)
- Output: `{title, text, metadata}`

### 8.4 Storage Layer
- Filesystem-based:
  ```
  /data/
    pages/
      <sha256(url)>.html    # raw HTML
      <sha256(url)>.txt     # extracted text
    manifest.json           # append-only log (list of ManifestEntry)
  ```
- Идемпотентность: если `<hash>.txt` существует — skip fetch
- `save_manifest()`: read → append → write (или использовать line-delimited JSON)

### 8.5 Logger
- File-based structured logging (JSON lines)
- Log path: `LOG_PATH` (default `/data/access.log`)
- Fields per entry:
  ```json
  {
    "timestamp": "...",
    "request_id": "...",
    "event": "search|fetch|extract|error",
    "query": "...",
    "url": "...",
    "latency_ms": 123,
    "error": null
  }
  ```

---

## 9. Concurrency Model

- `asyncio` event loop (Flask with async route handlers or gunicorn with `uvicorn workers`)
- Search → async fetch (parallel, semaphore-limited) → extract → save
- Non-blocking pipeline: search results потоком поступают в FetchEngine

```
search(query)
    │
    ▼
list[SearchResult] ──→ FetchEngine.fetch_all(urls) ──→ list[html]
                            │
                            ▼
                    Extractor.extract_all(htmls) ──→ list[CrawlResult]
                            │
                            ▼
                    Storage.save_all(results)
                            │
                            ▼
                    response
```

---

## 10. Failure Handling

| Scenario                    | Strategy                              |
|-----------------------------|---------------------------------------|
| SearXNG unavailable         | Return 503, log error                 |
| URL fetch timeout           | Retry 2×, skip if exhausted           |
| Extract empty text          | Log warning, include partial result   |
| Disk full / write error     | Log critical, return 507              |
| Invalid request body        | Return 400 with validation error      |
| MCP unknown tool            | Return structured MCP error response  |

---

## 11. Deployment

- **Container**: единый Docker-образ на базе `python:3.12-slim`
- **Process manager**: `gunicorn` (wsgi) или `uvicorn` (asgi)
- **Docker compose**: отдельный сервис `crawler_endpoint` в том же compose-файле, что и SearXNG

```yaml
services:
  searxng: ...
  crawler_endpoint:
    build: ./crawler_endpoint
    ports:
      - "8000:8000"
    environment:
      - SEARXNG_URL=http://searxng:8080
      - DATA_PATH=/data
      - MAX_CONCURRENCY=10
    volumes:
      - crawler_data:/data
    depends_on:
      searxng:
        condition: service_healthy
```

---

## 12. Security Model

- **local-only trusted environment**
- **No auth** initially (служебный сервис внутри Docker network)
- Optional future: API key middleware (Flask before_request)
- MCP endpoint — только изнутри Docker-сети, не публикуется наружу

---

## 13. Future Extensions (Roadmap)

- Redis job queue для долгих crawl-задач
- Vector DB integration (Qdrant / Chroma) для RAG
- Embeddings pipeline (sentence-transformers)
- Reranking (cross-encoder)
- Caching layer для URL (TTL-based dedup)
- Web UI для просмотра результатов
- Rate limiter (per-agent)

---

## 14. Definition of Done (MVP)

- [x] SearXNG search работает через API
- [x] `POST /api/crawl` возвращает структурированные результаты
- [x] `GET /api/search` — прокси к SearXNG
- [x] `GET /api/fetch` — fetch одиночного URL + extract
- [x] Извлечённый текст сохраняется на диск (`/data/pages/<hash>.txt`)
- [x] Raw HTML сохраняется (`/data/pages/<hash>.html`)
- [x] `manifest.json` обновляется после каждого crawl
- [x] `access.log` заполняется структурированными записями
- [x] MCP endpoint `/mcp/tools/call` отвечает на вызовы `search`, `crawl`, `fetch_page`
- [x] Flask API и MCP работают на одном порту
- [x] Контейнер собирается и запускается через `docker-compose up`
- [x] Все тесты проходят (`pytest`)
