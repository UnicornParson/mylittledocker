# Implementation Plan: crawler_endpoint

План реализации сервиса `crawler_endpoint`.

**Легенда:**
- `[ ]` — не начато
- `[~]` — в работе
- `[x]` — завершено

**Последнее обновление:** 2026-07-03

---

## Phase 0 — Environment & Project Scaffold

**Статус: ✅ ЗАВЕРШЕНО**

Цель: создать структуру пакета, настроить зависимости и CI.

| # | Задача | Статус | Файлы | Описание |
|---|--------|--------|-------|----------|
| 0.1 | Создать Python-пакет | ✅ | `__init__.py`, `__main__.py` | Корневой пакет и точка входа |
| 0.2 | Описать зависимости | ✅ | `requirements.txt` | flask, httpx, trafilatura, readability-lxml, pydantic-settings, gunicorn |
| 0.3 | Создать Dockerfile | ✅ | `Dockerfile` | python:3.12-slim, install deps, copy package, CMD gunicorn |
| 0.4 | Обновить docker-compose | ✅ | `docker-compose.yml` | Добавить сервис crawler_endpoint с volumes и depends_on |
| 0.5 | Настроить .env | ✅ | `.env` | SEARXNG_PORT=8080, CRAWLER_PORT=8000 |

**Результат:** ✅ проект собирается в Docker, сервис стартует без ошибок.

---

## Phase 1 — Config & DI

**Статус: ✅ ЗАВЕРШЕНО**

Цель: unit of configuration + dependency injection.

| # | Задача | Статус | Файлы | Описание |
|---|--------|--------|-------|----------|
| 1.1 | Написать config.py | ✅ | `config.py` | Класс `Settings` на pydantic-settings (27 строк, полная реализация) |
| 1.2 | Написать di.py | ✅ | `di.py` | Класс `Container` с lazy initialization (63 строки, полная реализация) |
| 1.3 | Написать models.py | ✅ | `models.py` | SearchResult, CrawlResult, ManifestEntry dataclasses (46 строк, полная реализация) |

**Результат:** ✅ есть объект настроек, DI-контейнер и модели данных.

---

## Phase 2 — Core Services

### 2.1 SearchClient

**Статус: ✅ ЗАВЕРШЕНО**

| # | Задача | Статус | Файлы | Описание |
|---|--------|--------|-------|----------|
| 2.1.1 | Реализовать клиент SearXNG | ✅ | `services/search_client.py` | Класс `SearchClient.search()` (78 строк, полная реализация с httpx) |
| 2.1.2 | Нормализация + дедупликация | ✅ | — | canonical URL + dedup по url (в разработке) |
| 2.1.3 | Timeout и ошибки | ✅ | — | HTTP timeout 10s, обработка ошибок |

### 2.2 FetchEngine

**Статус: ✅ ЗАВЕРШЕНО**

| # | Задача | Статус | Файлы | Описание |
|---|--------|--------|-------|----------|
| 2.2.1 | Реализовать асинхронный fetcher | ✅ | `services/fetch_engine.py` | Класс `FetchEngine.fetch()` (287 строк, полная реализация) |
| 2.2.2 | Параллельный fetch | ✅ | — | `fetch_all()` с asyncio semaphore |
| 2.2.3 | Retry + timeout | ✅ | — | FETCH_RETRIES попыток, exponential backoff |
| 2.2.4 | Playwright fallback | ✅ | — | Anubis bypass через Playwright (287 строк) |
| 2.2.5 | SOCKS5 proxy | ✅ | — | Проксирование всех запросов через SOCKS5 |

### 2.3 Extractor

**Статус: ✅ ЗАВЕРШЕНО**

| # | Задача | Статус | Файлы | Описание |
|---|--------|--------|-------|----------|
| 2.3.1 | Реализовать extractor | ✅ | `services/extractor.py` | Класс `Extractor.extract()` (82 строки, полная реализация) |
| 2.3.2 | Primary: trafilatura | ✅ | — | trafilatura.extract() с JSON форматом |
| 2.3.3 | Fallback: readability | ✅ | — | readability.Document.summary() fallback |
| 2.3.4 | Пакетная обработка | ✅ | — | ExtractResult model |

### 2.4 Storage Layer

**Статус: ✅ ЗАВЕРШЕНО**

| # | Задача | Статус | Файлы | Описание |
|---|--------|--------|-------|----------|
| 2.4.1 | Реализовать storage | ✅ | `services/storage.py` | Класс `StorageLayer` (124 строки, полная реализация) |
| 2.4.2 | Структура директорий | ✅ | — | `/data/pages/YYYY.MM.DD/<sha256>.<ns>.<ext>` |
| 2.4.3 | Идемпотентность | ✅ | — | `exists()` метод по hash |
| 2.4.4 | manifest.json | ✅ | — | `save_manifest()` — read → append → write |
| 2.4.5 | Пакетное сохранение | ⬜ | — | `save_all()` не реализован |

### 2.5 Logger

**Статус: ✅ ЗАВЕРШЕНО**

| # | Задача | Статус | Файлы | Описание |
|---|--------|--------|-------|----------|
| 2.5.1 | Реализовать logger | ✅ | `services/logger.py` | Класс `LoggerService` (48 строк, полная реализация) |
| 2.5.2 | Методы-хелперы | ⬜ | — | log_search, log_fetch, log_error — не реализованы |

**Результат phase 2:** ⚠️ Все 5 сервисов реализованы, но `save_all()` и helper-методы logger не реализованы.

---

## Phase 3 — API Routes

### 3.1 Flask REST API

**Статус: ⚠️ ЧАСТИЧНО ЗАВЕРШЕНО (заглушки)**

| # | Задача | Статус | Файлы | Описание |
|---|--------|--------|-------|----------|
| 3.1.1 | Создать blueprint api | ✅ | `routes/api.py` | Blueprint `api`, prefix `/api` |
| 3.1.2 | POST /api/crawl | ⚠️ | `routes/api.py` | **ЗАГЛУШКА** — TODO: implement crawl pipeline |
| 3.1.3 | GET /api/search | ⚠️ | `routes/api.py` | **ЗАГЛУШКА** — TODO: implement search proxy |
| 3.1.4 | GET /api/fetch | ⚠️ | `routes/api.py` | **ЗАГЛУШКА** — TODO: implement fetch + extract |
| 3.1.5 | Валидация запросов | ⬜ | — | pydantic-модели для request body |
| 3.1.6 | Error handlers | ⬜ | — | @api.errorhandler(400/503/500) |

### 3.2 MCP API

**Статус: ⚠️ ЧАСТИЧНО ЗАВЕРШЕНО (заглушки)**

| # | Задача | Статус | Файлы | Описание |
|---|--------|--------|-------|----------|
| 3.2.1 | Создать blueprint mcp | ✅ | `routes/mcp.py` | Blueprint `mcp`, prefix `/mcp` |
| 3.2.2 | POST /mcp/tools/call | ⚠️ | `routes/mcp.py` | **ЗАГЛУШКА** — dispatch с пустыми ответами |
| 3.2.3 | Tool: search | ⚠️ | `routes/mcp.py` | **ЗАГЛУШКА** — возвращает фиктивный ответ |
| 3.2.4 | Tool: crawl | ⚠️ | `routes/mcp.py` | **ЗАГЛУШКА** — возвращает фиктивный ответ |
| 3.2.5 | Tool: fetch_page | ⚠️ | `routes/mcp.py` | **ЗАГЛУШКА** — возвращает фиктивный ответ |
| 3.2.6 | MCP error schema | ✅ | `routes/mcp.py` | Return error для unknown tool |

**Результат phase 3:** ⚠️ Blueprint'ы созданы, но все endpoint'ы — заглушки (TODO). **Не реализован реальный pipeline.**

---

## Phase 4 — App Factory & Wiring

**Статус: ✅ ЧАСТИЧНО ЗАВЕРШЕНО**

| # | Задача | Статус | Файлы | Описание |
|---|--------|--------|-------|----------|
| 4.1 | Создать app factory | ✅ | `app.py` | create_app() с DI container и blueprints (31 строка) |
| 4.2 | Реализовать entrypoint | ✅ | `__main__.py` | app = create_app(), run host/port (8 строк) |
| 4.3 | Добавить healthcheck | ⬜ | — | GET /api/health → {"status": "ok"} |

---

## Phase 5 — Dockerization

**Статус: ✅ ЗАВЕРШЕНО**

| # | Задача | Статус | Файлы | Описание |
|---|--------|--------|-------|----------|
| 5.1 | Написать Dockerfile | ✅ | `Dockerfile` | python:3.12-slim, pip install → copy → run |
| 5.2 | Добавить .dockerignore | ✅ | `.dockerignore` | __pycache__, *.pyc, .git, tests |
| 5.3 | Обновить docker-compose | ✅ | `docker-compose.yml` | Сервис crawler_endpoint, порт 8000 |
| 5.4 | Обновить up.sh | ✅ | `up.sh` | docker compose up --build -d |

---

## Phase 6 — Testing

**Статус: ⚠️ ЧАСТИЧНО ЗАВЕРШЕНО**

| # | Задача | Статус | Файлы | Описание |
|---|--------|--------|-------|----------|
| 6.1 | conftest | ✅ | `tests/conftest.py` | Fixtures: temp dir, mock settings |
| 6.2 | test_search | ✅ | `tests/test_search.py` | Mock httpx → normalization, dedup (142 строки) |
| 6.3 | test_fetch | ✅ | `tests/test_fetch.py` | Mock httpx → retry, semaphore |
| 6.4 | test_extractor | ✅ | `tests/test_extractor.py` | trafilatura, readability fallback |
| 6.5 | test_storage | ✅ | `tests/test_storage.py` | save/load, idempotency, manifest |
| [ ] | 6.6 | ⬜ | — | Integration test (full pipeline) |
| [ ] | 6.7 | ⬜ | — | API tests (Flask test client) |

**Результат phase 6:** ⚠️ Unit-тесты для сервисов написаны. Требуются интеграционные и API тесты.

---

## Phase 7 — Production Hardening (post-MVP)

**Статус: ⬜ НЕ НАЧАТО**

| # | Задача | Приоритет | Статус |
|---|--------|-----------|--------|
| 7.1 | Rate limiting (Flask-Limiter) | Medium | ⬜ |
| 7.2 | API key auth middleware | Low | ⬜ |
| 7.3 | Request ID propagation (uuid4) | Medium | ⬜ |
| 7.4 | Caching layer (TTL URL cache) | Medium | ⬜ |
| 7.5 | Retry backoff tuning (jitter) | Low | ⬜ |
| 7.6 | Prometheus metrics | Low | ⬜ |
| 7.7 | Redis job queue для долгих crawl | Optional | ⬜ |

---

## Definition of Done (MVP) — Реальный статус

- [x] SearXNG search — **SearchClient реализован** (но API endpoint — заглушка)
- [ ] `POST /api/crawl` возвращает структурированные результаты — **⚠️ ЗАГЛУШКА**
- [ ] `GET /api/search` — прокси к SearXNG — **⚠️ ЗАГЛУШКА**
- [ ] `GET /api/fetch` — fetch одиночного URL + extract — **⚠️ ЗАГЛУШКА**
- [x] Извлечённый текст сохраняется на диск — **StorageLayer реализован**
- [x] Raw HTML сохраняется — **StorageLayer реализован**
- [x] `manifest.json` обновляется — **save_manifest() реализован**
- [x] `access.log` заполняется — **LoggerService реализован**
- [ ] MCP endpoint `/mcp/tools/call` отвечает на вызовы — **⚠️ ЗАГЛУШКА**
- [x] Flask API и MCP работают на одном порту — **blueprints зарегистрированы**
- [x] Контейнер собирается и запускается через `docker compose up`
- [~] Все тесты проходят (`pytest`) — unit-тесты есть, интеграционные нет

---

## Дальнейшие шаги

### Приоритет P0 (критичные — реализовать реальный код)

1. [ ] **Реализовать `GET /api/search`** — вызвать SearchClient.search() и вернуть результаты
2. [ ] **Реализовать `GET /api/fetch`** — вызвать FetchEngine.fetch() + Extractor.extract() + Storage.save*()
3. [ ] **Реализовать `POST /api/crawl`** — полный pipeline: search → fetch_all → extract_all → save_all
4. [ ] **Реализовать MCP tools** — заменить заглушки на реальные вызовы сервисов
5. [ ] Добавить healthcheck `/api/health`
6. [ ] Добавить error handlers (400/503/500)

### Приоритет P1 (важные)

7. [ ] Добавить request validation (pydantic)
8. [ ] Написать интеграционные тесты (full pipeline)
9. [ ] Написать API тесты (Flask test client)
10. [ ] Прогнать `pytest` и убедиться что все тесты проходят
11. [ ] Реализовать `save_all()` для пакетного сохранения
12. [ ] Добавить helper-методы в Logger (log_search, log_fetch, log_error)

### Приоритет P2 (желательные)

13. [ ] Request ID propagation
14. [ ] TTL caching layer
15. [ ] Rate limiting (Flask-Limiter)
16. [ ] Prometheus metrics
17. [ ] API key auth
18. [ ] Redis job queue для долгих crawl-задач
19. [ ] Web UI для просмотра результатов