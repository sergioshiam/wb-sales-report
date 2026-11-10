"""Настройки приложения.

Все настройки берутся из переменных окружения (так принято для сервисов в Docker):
  WB_TOKEN      — токен продавца Wildberries (личный кабинет → Интеграции по API).
                  Нужны категории «Статистика» и «Аналитика». Если токена нет —
                  сервис работает на демо-данных из папки data/.
  DATABASE_URL  — адрес базы данных. В Docker это PostgreSQL,
                  для локального запуска без Docker можно оставить SQLite.
"""

import os

WB_TOKEN: str = os.getenv("WB_TOKEN", "").strip()

DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./wb_report.db")

# Демо-режим включается сам, если токен не задан.
DEMO_MODE: bool = not WB_TOKEN

# Адреса API Wildberries (по официальной OpenAPI-спецификации WB).
WB_STATISTICS_URL = "https://statistics-api.wildberries.ru"
WB_ANALYTICS_URL = "https://seller-analytics-api.wildberries.ru"
