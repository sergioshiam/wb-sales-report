"""Проверяем веб-сервис целиком на демо-данных: синхронизация → отчёт."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.main import app, get_client, get_session
from app.wb_client import WBClient


def test_sync_and_report_in_demo_mode(session):
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[get_client] = lambda: WBClient(token="", demo=True)
    try:
        client = TestClient(app)
        r = client.post("/sync")
        assert r.status_code == 200
        assert r.json()["mode"] == "demo"
        assert r.json()["sales_rows"] > 0

        report = client.get("/report?days=30").json()
        statuses = {i["supplier_article"] or i["nm_id"]: i["status"] for i in report["items"]}
        assert statuses["DEMO-LEG-02"] == "дефицит"
        assert report["totals"]["sold_qty"] > 0

        one = client.get("/report/210000101").json()
        assert one["supplier_article"] == "DEMO-LEG-01"

        assert client.get("/report/1").status_code == 404
    finally:
        app.dependency_overrides.clear()
