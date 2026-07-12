# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added

- Логирование попыток подключения к SD WebUI: при каждом HTTP-запросе теперь логируются метод, URL и статус ответа (httpx event hooks в `get_http_client()`).
- Логирование инициализации HTTP-клиента: URL, статус аутентификации, таймаут.