"""Веб-сервис на FastAPI.

Адреса (эндпоинты):
  GET  /health                 — проверка, что сервис жив, и в каком он режиме (демо или WB API)
  POST /sync?date_from=...     — забрать продажи и остатки из WB и сохранить в базу
  GET  /report?days=30         — отчёт по всем артикулам за последние N дней
  GET  /report/{nm_id}         — отчёт по одному артикулу
  GET  /docs                   — автоматическая документация, где можно нажимать кнопки и пробовать запросы
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import date, timedelta

from fastapi import Depends, FastAPI, HTTPException, Query
from sqlalchemy.orm import Session

from app import config
from app.db import SessionLocal, init_db
from app.reports import article_report
from app.sync import sync_all
from app.wb_client import WBApiError, WBClient


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()  # при старте создаём таблицы, если их нет
    yield


app = FastAPI(
    title="WB Sales Report",
    description="Продажи, возвраты и остатки Wildberries по артикулам",
    lifespan=lifespan,
)


def get_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def get_client() -> WBClient:
    return WBClient()


@app.get("/health")
def health():
    return {"status": "ok", "mode": "demo" if config.DEMO_MODE else "wb_api"}


@app.post("/sync")
def sync(
    date_from: str = Query(
        default_factory=lambda: (date.today() - timedelta(days=30)).isoformat(),
        description="С какой даты забирать продажи (ГГГГ-ММ-ДД)",
    ),
    session: Session = Depends(get_session),
    client: WBClient = Depends(get_client),
):
    try:
        return sync_all(session, client, date_from)
    except WBApiError as e:
        raise HTTPException(status_code=502, detail=str(e))


@app.get("/report")
def report(days: int = Query(30, ge=1, le=90), session: Session = Depends(get_session)):
    return article_report(session, days=days)


@app.get("/report/{nm_id}")
def report_one(nm_id: int, days: int = Query(30, ge=1, le=90), session: Session = Depends(get_session)):
    data = article_report(session, days=days)
    for item in data["items"]:
        if item["nm_id"] == nm_id:
            return item
    raise HTTPException(status_code=404, detail="Артикул не найден")
