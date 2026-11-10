"""Отчёт по артикулам: продажи, возвраты, выручка, остатки и на сколько дней их хватит.

Логика расчёта (её стоит уметь объяснить):
  * Продажа — строка с saleID на «S», возврат — на «R».
  * Чистые продажи = продажи − возвраты (в штуках и в рублях).
  * Суммы по возвратам берём по модулю и вычитаем, чтобы расчёт не зависел
    от того, с каким знаком WB отдаёт сумму возврата.
  * Процент возвратов = возвраты / продажи.
  * Средние продажи в день = чистые продажи за период / число дней периода.
  * Запас в днях = остаток на складах / средние продажи в день.
    Если запаса меньше 14 дней — пометка «дефицит»,
    если товар лежит на складе, но за период не продавался — «нет продаж».
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Sale, Stock

DEFICIT_DAYS = 14


def article_report(session: Session, days: int = 30, period_end: datetime | None = None) -> dict:
    if period_end is None:
        # Конец периода — дата последней продажи в базе (для демо-данных) или сейчас.
        period_end = session.scalar(select(func.max(Sale.date))) or datetime.now()
    period_start = period_end - timedelta(days=days)

    sales = session.scalars(
        select(Sale).where(Sale.date > period_start, Sale.date <= period_end)
    ).all()

    agg: dict[int, dict] = defaultdict(
        lambda: {
            "supplier_article": "",
            "subject": "",
            "sold_qty": 0,
            "returned_qty": 0,
            "revenue": 0.0,
            "for_pay": 0.0,
        }
    )
    for s in sales:
        a = agg[s.nm_id]
        a["supplier_article"] = s.supplier_article
        a["subject"] = s.subject
        if s.is_return:
            a["returned_qty"] += 1
            a["revenue"] -= abs(s.finished_price)
            a["for_pay"] -= abs(s.for_pay)
        else:
            a["sold_qty"] += 1
            a["revenue"] += abs(s.finished_price)
            a["for_pay"] += abs(s.for_pay)

    # Остатки по артикулу — сумма по всем складам и размерам.
    stock_rows = session.execute(
        select(
            Stock.nm_id,
            func.sum(Stock.quantity),
            func.sum(Stock.in_way_to_client),
            func.sum(Stock.in_way_from_client),
        ).group_by(Stock.nm_id)
    ).all()
    stocks = {nm: (int(q or 0), int(to or 0), int(fr or 0)) for nm, q, to, fr in stock_rows}

    items = []
    for nm_id in sorted(set(agg) | set(stocks)):
        a = agg[nm_id]
        stock_qty, to_client, from_client = stocks.get(nm_id, (0, 0, 0))
        net_qty = a["sold_qty"] - a["returned_qty"]
        per_day = net_qty / days if days else 0
        days_of_stock = round(stock_qty / per_day, 1) if per_day > 0 else None

        if stock_qty > 0 and net_qty <= 0:
            status = "нет продаж"
        elif days_of_stock is not None and days_of_stock < DEFICIT_DAYS:
            status = "дефицит"
        else:
            status = "норма"

        items.append(
            {
                "nm_id": nm_id,
                "supplier_article": a["supplier_article"],
                "subject": a["subject"],
                "sold_qty": a["sold_qty"],
                "returned_qty": a["returned_qty"],
                "net_qty": net_qty,
                "return_rate_pct": round(100 * a["returned_qty"] / a["sold_qty"], 1)
                if a["sold_qty"]
                else 0.0,
                "revenue": round(a["revenue"], 2),
                "for_pay": round(a["for_pay"], 2),
                "avg_daily_sales": round(per_day, 2),
                "stock_qty": stock_qty,
                "in_way_to_client": to_client,
                "in_way_from_client": from_client,
                "days_of_stock": days_of_stock,
                "status": status,
            }
        )

    return {
        "period_start": period_start.isoformat(timespec="seconds"),
        "period_end": period_end.isoformat(timespec="seconds"),
        "days": days,
        "totals": {
            "sold_qty": sum(i["sold_qty"] for i in items),
            "returned_qty": sum(i["returned_qty"] for i in items),
            "revenue": round(sum(i["revenue"] for i in items), 2),
            "for_pay": round(sum(i["for_pay"] for i in items), 2),
            "stock_qty": sum(i["stock_qty"] for i in items),
        },
        "items": items,
    }
