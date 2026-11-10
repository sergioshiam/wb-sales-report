"""Проверяем клиент WB без настоящего интернета: подменяем ответы сервера (MockTransport)."""

import httpx
import pytest

from app.wb_client import STOCKS_PAGE_LIMIT, WBApiError, WBClient


def make_client(handler):
    waits = []
    client = WBClient(
        token="test-token",
        http=httpx.Client(transport=httpx.MockTransport(handler)),
        sleep=waits.append,  # вместо ожидания просто запоминаем, сколько ждали бы
        demo=False,
    )
    return client, waits


def test_sales_pagination_and_auth_header():
    calls = []

    def handler(request: httpx.Request):
        calls.append(request)
        assert request.headers["Authorization"] == "test-token"
        date_from = request.url.params["dateFrom"]
        if date_from == "2026-10-01":
            return httpx.Response(200, json=[{"srid": "1", "lastChangeDate": "2026-10-05T10:00:00"}])
        return httpx.Response(200, json=[])  # пустой список = данные закончились

    client, waits = make_client(handler)
    rows = client.get_sales("2026-10-01")

    assert len(rows) == 1
    assert len(calls) == 2
    # второй запрос идёт с dateFrom = lastChangeDate последней строки
    assert calls[1].url.params["dateFrom"] == "2026-10-05T10:00:00"
    assert waits == [61]  # между запросами выдержан лимит WB


def test_sales_retries_after_429():
    attempts = {"n": 0}

    def handler(request):
        attempts["n"] += 1
        if attempts["n"] == 1:
            return httpx.Response(429, headers={"X-Ratelimit-Retry": "5"})
        return httpx.Response(200, json=[])

    client, waits = make_client(handler)
    assert client.get_sales("2026-10-01") == []
    assert waits == [5.0]


def test_stocks_204_means_no_data():
    client, _ = make_client(lambda request: httpx.Response(204))
    assert client.get_stocks() == []


def test_stocks_request_body_and_parse():
    def handler(request):
        assert request.method == "POST"
        assert request.url.path == "/api/analytics/v1/stocks-report/wb-warehouses"
        assert b'"limit":250000' in request.content.replace(b" ", b"")
        return httpx.Response(200, json={"data": {"items": [{"nmId": 1, "quantity": 5}]}})

    client, _ = make_client(handler)
    assert client.get_stocks() == [{"nmId": 1, "quantity": 5}]


def test_error_is_raised_on_401():
    client, _ = make_client(lambda request: httpx.Response(401, text="unauthorized"))
    with pytest.raises(WBApiError):
        client.get_sales("2026-10-01")


def test_page_limit_constant():
    assert STOCKS_PAGE_LIMIT == 250_000
