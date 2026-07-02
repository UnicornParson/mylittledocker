# Implementation Plan: crawler_endpoint

План реализации сервиса `crawler_endpoint`.

**Легенда:**
- `[ ]` — не начато
- `[~]` — в работе
- `[x]` — завершено

---

## Phase 0 — Environment & Project Scaffold

Цель: создать структуру пакета, настроить зависимости и CI.

| # | Задача | Файлы | Описание |
|---|--------|-------|----------|
| 0.1 | Создать Python-пакет | `crawler_endpoint/__init__.py`, `crawler_endpoint/__main__.py` | Корневой пакет и точка входа |
| 0.2 | Описать зависимости | `crawler_endpoint/requirements.txt` | `flask`, `httpx`, `trafilatura`, `readability-lxml`, `pydantic-settings`, `gunicorn` |
| 0.3 | Создать Dockerfile | `crawler/Dockerfile` | `python:3.12-slim`, install deps, copy package, CMD gunicorn |
| 0.4 | Обновить docker-compose | `crawler/docker-compose.yml` | Добавить сервис `crawler_endpoint` с volumes и depends_on |
| 0.5 | Настроить .env | `crawler/.env` | `SEARXNG_PORT=8080`, `CRAWLER_PORT=8000` |

**Результат:** проект собирается в Docker, сервис стартует без ошибок.

---

## Phase 1 — Config & DI

Цель: unit of configuration + dependency injection.

| # | Задача | Файлы | Описание |
|---|--------|-------|----------|
| 1.1 | Написать config.py | `crawler_endpoint/config.py` | Класс `Settings` на `pydantic-settings` (см. HLD раздел 5) |
| 1.2 | Написать di.py | `crawler_endpoint/di.py` | Функция `wire_services(settings) -> dict` — фабрика сервисов |
| 1.3 | Написать models.py | `crawler_endpoint/models.py` | Dataclasses: `SearchResult`, `CrawlResult`, `ManifestEntry` (см. HLD раздел 6) |

**Результат:** есть объект настроек, DI-контейнер и модели данных.

---

## Phase 2 — Core Services

### 2.1 SearchClient

| # | Задача | Файлы | Описание |
|---|--------|-------|----------|
| 2.1.1 | Реализовать клиент SearXNG | `crawler_endpoint/services/search_client.py` | Класс `SearchClient`: `search(query, top_k) -> list[SearchResult]` |
| 2.1.2 | Нормализация + дедупликация | — | canonical URL (strip utm_*, fbclid, etc.) + dedup по url |
| 2.1.3 | Timeout и ошибки | — | HTTP timeout 10s, raise `SearchClientError` при недоступности |

### 2.2 FetchEngine

| # | Задача | Файлы | Описание |
|---|--------|-------|----------|
| 2.2.1 | Реализовать асинхронный fetcher | `crawler_endpoint/services/fetch_engine.py` | Класс `FetchEngine`: `fetch(url) -> str` (raw html) |
| 2.2.2 | Параллельный fetch | — | `fetch_all(urls) -> list[tuple[url, html]]` с asyncio semaphore |
| 2.2.3 | Retry + timeout | — | `FETCH_RETRIES` попыток, exponential backoff, `FETCH_TIMEOUT` |
| 2.2.4 | Playwright fallback (опция) | — | Если `PLAYWRIGHT_ENABLED=true` — пробуем Playwright при пустом html |

### 2.3 Extractor

| # | Задача | Файлы | Описание |
|---|--------|-------|----------|
| 2.3.1 | Реализовать extractor | `crawler_endpoint/services/extractor.py` | Класс `Extractor`: `extract(html, url) -> CrawlResult` |
| 2.3.2 | Primary: trafilatura | — | `trafilatura.extract(html, output_format='txt', include_links=False)` |
| 2.3.3 | Fallback: readability | — | Если trafilatura вернул None — `readability.Document(html).summary()` + `html2text` |
| 2.3.4 | Пакетная обработка | — | `extract_all(htmls) -> list[CrawlResult]` |

### 2.4 Storage Layer

| # | Задача | Файлы | Описание |
|---|--------|-------|----------|
| 2.4.1 | Реализовать storage | `crawler_endpoint/services/storage.py` | Класс `Storage`: `save(result: CrawlResult) -> None` |
| 2.4.2 | Структура директорий | — | `DATA_PATH/pages/<sha256(url)>.html/.txt` |
| 2.4.3 | Идемпотентность | — | Если `.txt` существует — skip |
| 2.4.4 | manifest.json | — | `save_manifest(entry)` — read → append → write (или NDJSON) |
| 2.4.5 | Пакетное сохранение | — | `save_all(results: list[CrawlResult]) -> None` |

### 2.5 Logger

| # | Задача | Файлы | Описание |
|---|--------|-------|----------|
| 2.5.1 | Реализовать logger | `crawler_endpoint/services/logger.py` | Класс `AccessLogger`: `log(event, **fields)` — JSON lines |
| 2.5.2 | Методы-хелперы | — | `log_search(query, count, latency_ms)`, `log_fetch(url, ok, latency_ms)`, `log_error(msg)` |

**Результат phase 2:** все 5 сервисов реализованы unit-независимо.

---

## Phase 3 — API Routes

### 3.1 Flask REST API

| # | Задача | Файлы | Описание |
|---|--------|-------|----------|
| 3.1.1 | Создать blueprint api | `crawler_endpoint/routes/api.py` | Blueprint `api`, prefix `/api` |
| 3.1.2 | `POST /api/crawl` | `crawler_endpoint/routes/api.py` | Body: `{query, top_k}` → search → fetch_all → extract_all → save_all → response |
| 3.1.3 | `GET /api/search` | — | `?q=&top_k=` → proxy to SearXNG → return results |
| 3.1.4 | `GET /api/fetch` | — | `?url=` → fetch → extract → save → return |
| 3.1.5 | Валидация запросов | — | pydantic-модели для request body / query params |
| 3.1.6 | Error handlers | — | `@api.errorhandler(400/503/500)` → JSON error response |

### 3.2 MCP API

| # | Задача | Файлы | Описание |
|---|--------|-------|----------|
| 3.2.1 | Создать blueprint mcp | `crawler_endpoint/routes/mcp.py` | Blueprint `mcp`, prefix `/mcp` |
| 3.2.2 | `POST /mcp/tools/call` | — | Dispatch по `tool`: `search`/`crawl`/`fetch_page` |
| 3.2.3 | Tool: search | — | MCP wrapper над `SearchClient.search()` |
| 3.2.4 | Tool: crawl | — | MCP wrapper над полным pipeline |
| 3.2.5 | Tool: fetch_page | — | MCP wrapper над `FetchEngine.fetch()` + `Extractor.extract()` |
| 3.2.6 | MCP error schema | — | Return `{error: {code, message}}` для unknown tool |

**Результат phase 3:** Flask приложение отвечает на запросы, MCP вызывается.

---

## Phase 4 — App Factory & Wiring

| # | Задача | Файлы | Описание |
|---|--------|-------|----------|
| 4.1 | Создать app factory | `crawler_endpoint/app.py` | `create_app() -> Flask`: load config, wire DI, register blueprints |
| 4.2 | Реализовать entrypoint | `crawler_endpoint/__main__.py` | `gunicorn -w 1 -b 0.0.0.0:8000 crawler_endpoint.app:create_app()` |
| 4.3 | Добавить healthcheck | `api.py` | `GET /api/health` → `{"status": "ok"}` |

---

## Phase 5 — Dockerization

| # | Задача | Файлы | Описание |
|---|--------|-------|----------|
| 5.1 | Написать Dockerfile | `crawler/Dockerfile` | Multi-stage или single-stage: pip install → copy package → run |
| 5.2 | Добавить .dockerignore | `crawler/.dockerignore` | `__pycache__`, `*.pyc`, `.git`, `tests`, `.venv` |
| 5.3 | Обновить docker-compose | `crawler/docker-compose.yml` | Сервис `crawler_endpoint`, порт 8000, volume `/data`, depends_on searxng |
| 5.4 | Обновить up.sh | `crawler/up.sh` | `docker compose up --build -d` |

---

## Phase 6 — Testing

| # | Задача | Файлы | Описание |
|---|--------|-------|----------|
| 6.1 | conftest | `crawler_endpoint/tests/conftest.py` | Fixtures: temp dir, mock settings, mock services |
| 6.2 | test_search | `crawler_endpoint/tests/test_search.py` | Mock httpx → test normalization, dedup, timeout |
| 6.3 | test_fetch | `crawler_endpoint/tests/test_fetch.py` | Mock httpx → test retry, semaphore, timeout, Playwright fallback |
| 6.4 | test_extractor | `crawler_endpoint/tests/test_extractor.py` | Test trafilatura extraction, readability fallback, empty html |
| 6.5 | test_storage | `crawler_endpoint/tests/test_storage.py` | Test save/load, idempotency, manifest append |
| 6.6 | Integration test | — | Test full pipeline: search → fetch → extract → save |
| 6.7 | API tests | — | Test Flask endpoints (test client) |

**Результат phase 6:** `pytest` проходит все тесты.

---

## Phase 7 — Production Hardening (post-MVP)

| # | Задача | Приоритет |
|---|--------|-----------|
| 7.1 | Rate limiting (Flask-Limiter) | Medium |
| 7.2 | API key auth middleware | Low |
| 7.3 | Request ID propagation (`uuid4` per request) | Medium |
| 7.4 | Caching layer (TTL cache для часто запрашиваемых URL) | Medium |
| 7.5 | Retry backoff tuning (jitter) | Low |
| 7.6 | Prometheus metrics (request count, latency, errors) | Low |
| 7.7 | Redis job queue для долгих crawl | Optional |

---

## Definition of Done (MVP)

- [ ] SearXNG search работает через API (`GET /api/search`)
- [ ] `POST /api/crawl` возвращает структурированные результаты с извлечённым текстом
- [ ] `GET /api/fetch` fetch одиночного URL + extract + save
- [ ] Извлечённый текст сохраняется на диск (`/data/pages/<hash>.txt`)
- [ ] Raw HTML сохраняется (`/data/pages/<hash>.html`)
- [ ] `manifest.json` обновляется после каждого crawl
- [ ] `access.log` заполняется структурированными записями
- [ ] MCP endpoint `/mcp/tools/call` отвечает на вызовы `search`, `crawl`, `fetch_page`
- [ ] Flask API и MCP работают на одном порту
- [ ] Контейнер собирается и запускается через `docker compose up`
- [ ] Все тесты проходят (`pytest`)