"""Загрузка данных из WB в базу (синхронизация)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.models import Sale, Stock
from app.wb_client import WBClient


def _parse_dt(value: str | None) -> datetime:
    """WB отдаёт даты строками вида 2026-10-01T12:30:00 (иногда с долями секунды или поясом)."""
    if not value:
        return datetime.min
    return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)


def save_sales(session: Session, rows: list[dict]) -> int:
    """Сохраняет продажи и возвраты. Повторная загрузка тех же строк не создаёт дублей:
    merge обновляет строку с тем же ключом (srid + saleID) или добавляет новую."""
    for r in rows:
        session.merge(
            Sale(
                srid=r["srid"],
                sale_id=r["saleID"],
                date=_parse_dt(r.get("date")),
                last_change_date=_parse_dt(r.get("lastChangeDate")),
                nm_id=r["nmId"],
                supplier_article=r.get("supplierArticle", ""),
                subject=r.get("subject", ""),
                brand=r.get("brand", ""),
                tech_size=r.get("techSize", ""),
                warehouse_name=r.get("warehouseName", ""),
                region_name=r.get("regionName", ""),
                finished_price=float(r.get("finishedPrice") or 0),
                for_pay=float(r.get("forPay") or 0),
            )
        )
    session.commit()
    return len(rows)


def save_stocks(session: Session, rows: list[dict]) -> int:
    """Остатки — это «снимок» на текущий момент, поэтому старый снимок заменяем новым."""
    session.execute(delete(Stock))
    session.add_all(
        Stock(
            nm_id=r["nmId"],
            chrt_id=r.get("chrtId", 0),
            warehouse_id=r.get("warehouseId", 0),
            warehouse_name=r.get("warehouseName", ""),
            region_name=r.get("regionName", ""),
            quantity=int(r.get("quantity") or 0),
            in_way_to_client=int(r.get("inWayToClient") or 0),
            in_way_from_client=int(r.get("inWayFromClient") or 0),
        )
        for r in rows
    )
    session.commit()
    return len(rows)


def sync_all(session: Session, client: WBClient, date_from: str) -> dict:
    sales = client.get_sales(date_from)
    stocks = client.get_stocks()
    return {
        "mode": "demo" if client.demo else "wb_api",
        "sales_rows": save_sales(session, sales),
        "stock_rows": save_stocks(session, stocks),
    }
