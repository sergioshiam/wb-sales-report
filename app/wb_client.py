"""Клиент API Wildberries.

Два метода:
  1. Продажи и возвраты: GET https://statistics-api.wildberries.ru/api/v1/supplier/sales
     Лимит WB: 1 запрос в минуту. Ответ — список строк, не больше ~80 000 за раз.
     Чтобы забрать всё, следующий запрос делаем с dateFrom = lastChangeDate последней строки,
     пока WB не вернёт пустой список.
  2. Текущие остатки: POST https://seller-analytics-api.wildberries.ru/api/analytics/v1/stocks-report/wb-warehouses
     Лимит WB: 3 запроса в минуту (интервал 20 секунд). До 250 000 строк за запрос,
     дальше — постранично через offset. Ответ 204 означает «данных нет».
     (Старый метод GET /api/v1/supplier/stocks WB отключил в 2026 году.)

Если токена нет (демо-режим), данные читаются из файлов data/demo_*.json.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Callable

import httpx

from app import config

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

SALES_PATH = "/api/v1/supplier/sales"
STOCKS_PATH = "/api/analytics/v1/stocks-report/wb-warehouses"
STOCKS_PAGE_LIMIT = 250_000


class WBApiError(Exception):
    """Ошибка при обращении к API Wildberries."""


class WBClient:
    def __init__(
        self,
        token: str | None = None,
        http: httpx.Client | None = None,
        sleep: Callable[[float], None] = time.sleep,
        demo: bool | None = None,
    ):
        self.token = config.WB_TOKEN if token is None else token
        self.demo = (not self.token) if demo is None else demo
        self.http = http or httpx.Client(timeout=60)
        self.sleep = sleep  # подменяется в тестах, чтобы не ждать минуту

    # ---------- общий запрос с обработкой лимитов ----------
    def _request(self, method: str, url: str, **kwargs) -> httpx.Response:
        headers = {"Authorization": self.token}
        for _attempt in range(3):
            resp = self.http.request(method, url, headers=headers, **kwargs)
            if resp.status_code == 429:
                # WB сообщает, сколько секунд подождать, в заголовке X-Ratelimit-Retry.
                wait = float(resp.headers.get("X-Ratelimit-Retry", 60))
                self.sleep(wait)
                continue
            if resp.status_code in (200, 204):
                return resp
            raise WBApiError(f"WB ответил {resp.status_code}: {resp.text[:300]}")
        raise WBApiError("WB продолжает отвечать 429 (превышен лимит запросов)")

    # ---------- продажи ----------
    def get_sales(self, date_from: str) -> list[dict]:
        """Все продажи и возвраты, изменённые начиная с date_from (формат 2026-10-01)."""
        if self.demo:
            return _load_demo("demo_sales.json")

        rows: list[dict] = []
        cursor = date_from
        while True:
            resp = self._request(
                "GET",
                config.WB_STATISTICS_URL + SALES_PATH,
                params={"dateFrom": cursor, "flag": 0},
            )
            page = resp.json() if resp.status_code == 200 else []
            if not page:
                break
            rows.extend(page)
            new_cursor = page[-1]["lastChangeDate"]
            if new_cursor == cursor:  # защита от бесконечного цикла
                break
            cursor = new_cursor
            self.sleep(61)  # лимит WB: 1 запрос в минуту
        return rows

    # ---------- остатки ----------
    def get_stocks(self, nm_ids: list[int] | None = None) -> list[dict]:
        """Текущие остатки на складах WB (по всем товарам или по списку артикулов)."""
        if self.demo:
            return _load_demo("demo_stocks.json")

        rows: list[dict] = []
        offset = 0
        while True:
            body: dict = {"limit": STOCKS_PAGE_LIMIT, "offset": offset}
            if nm_ids:
                body["nmIds"] = nm_ids
            resp = self._request("POST", config.WB_ANALYTICS_URL + STOCKS_PATH, json=body)
            if resp.status_code == 204:
                break
            items = resp.json().get("data", {}).get("items", [])
            rows.extend(items)
            if len(items) < STOCKS_PAGE_LIMIT:
                break
            offset += STOCKS_PAGE_LIMIT
            self.sleep(20)  # лимит WB: 1 запрос в 20 секунд
        return rows


def _load_demo(name: str) -> list[dict]:
    with open(DATA_DIR / name, encoding="utf-8") as f:
        return json.load(f)
