Вот обновлённое резюме без уже решённых и неактуальных проблем — оставил только текущее состояние и активный дизайн.

---

# 📌 Текущее состояние проекта

Ты строишь локальную систему на базе **SearXNG + crawler_endpoint**, которая используется как backend для LLM-агентов.

Основная цель:

> Search → URL selection → crawling → extraction → storage → LLM/RAG consumption

---

# 🧩 SearXNG слой (уже работает)

## Статус

* SearXNG развернут в Docker
* API доступен (`/search?format=json`)
* JSON выдача стабильна
* несколько движков работают (DuckDuckGo, Brave, Startpage)
* агрегация результатов функционирует (≈16 результатов на запрос)

## Роль в системе

SearXNG используется только как:

> discovery layer (поиск и выдача URL)

Он:

* не фетчит страницы
* не делает IP/geo lookup
* не участвует в извлечении контента

---

# 🧱 Основной компонент: crawler_endpoint (в разработке)

Ты проектируешь отдельный сервис:

> orchestration + crawling + storage + MCP interface

---

## 📡 Интерфейсы (один порт)

### 1. HTTP API (Flask)

* `/api/crawl`
* `/api/search`
* `/api/fetch`

### 2. MCP API (для LLM-агентов)

* `/mcp/tools/call`

Инструменты:

* search
* crawl
* fetch_page

---

# 🔁 Основной pipeline

```text id="g0p1lm"
LLM Agent
   ↓
crawler_endpoint
   ↓
SearXNG (discovery)
   ↓
URL ranking / filtering
   ↓
page fetching (HTTP / Playwright)
   ↓
text extraction (trafilatura)
   ↓
local storage (/data)
   ↓
logs (access.log)
```

---

# 🧠 Core responsibilities crawler_endpoint

## 1. SearchClient

* запросы в SearXNG
* нормализация результатов
* дедупликация URL

---

## 2. FetchEngine

* async HTTP fetching
* retry + timeout control
* fallback на Playwright (если нужно)

---

## 3. Extractor

* primary: trafilatura
* fallback: readability-lxml
* output: чистый текст + metadata

---

## 4. Storage layer

Filesystem-based:

```text id="x7d9qp"
/data
  /pages
    <sha256>.html
    <sha256>.txt
  manifest.json
```

---

## 5. Logging system

File-based:

```text id="l2k8mn"
access.log
```

Логирует:

* входящие запросы
* SearXNG response stats
* выбранные URL
* результаты fetch
* ошибки
* latency

---

# 🔌 MCP слой

Добавляется для LLM-native интеграции:

## Tools:

* `search`
* `crawl`
* `fetch_page`

## Формат:

* JSON tool calls
* возвращает structured artifacts + text output

---

# ⚙️ Архитектурные свойства

## 1. Stateless compute

* состояние хранится в `/data`
* контейнер можно пересоздавать

## 2. Async pipeline

* параллельный fetch
* ограничение concurrency (semaphore)

## 3. Deduplication

* hash(URL)
* canonicalization (clean tracking params)

## 4. Resilience

* retry policy
* graceful skip failed pages

---

# 🧭 Общая роль системы

Ты фактически строишь:

> локальный retrieval + crawling + ingestion слой для LLM

Это промежуточный слой между:

* поиском (SearXNG)
* вебом
* LLM

---

# 🚀 Текущее состояние проекта (сводка)

### Уже работает:

* SearXNG search backend ✔
* JSON API ✔
* мульти-движковая выдача ✔

### В разработке:

* crawler_endpoint orchestration layer
* MCP API
* page fetching + extraction pipeline
* storage + logging system

---

# 📌 Ключевая идея системы

SearXNG = discovery
crawler_endpoint = intelligence + retrieval + persistence
LLM = reasoning layer

---

# ➜ Следующий логичный шаг (если продолжать)

* MVP FastAPI/Flask skeleton crawler_endpoint
* async fetch engine (production-ready)
* MCP tool server implementation
* docker-compose integration finalization

---

