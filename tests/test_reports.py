"""Проверяем расчёты отчёта на маленьком наборе данных, где ответ известен заранее."""

from datetime import datetime

from app.reports import article_report
from app.sync import save_sales, save_stocks


def sale(srid, sale_id, nm_id, day, price, for_pay):
    return {
        "srid": srid, "saleID": sale_id, "nmId": nm_id,
        "date": f"2026-10-{day:02d}T12:00:00", "lastChangeDate": f"2026-10-{day:02d}T13:00:00",
        "supplierArticle": f"ART-{nm_id}", "subject": "Леггинсы",
        "finishedPrice": price, "forPay": for_pay,
    }


def stock(nm_id, qty, wh=1):
    return {"nmId": nm_id, "chrtId": 1, "warehouseId": wh, "warehouseName": "Склад",
            "regionName": "Россия", "quantity": qty, "inWayToClient": 0, "inWayFromClient": 0}


END = datetime(2026, 10, 30, 23, 0)


def test_sales_minus_returns(session):
    # 3 продажи по 1000 ₽ и 1 возврат (сумма возврата пришла со знаком минус)
    save_sales(session, [
        sale("o1", "S1", 111, 10, 1000, 700),
        sale("o2", "S2", 111, 11, 1000, 700),
        sale("o3", "S3", 111, 12, 1000, 700),
        sale("o1", "R1", 111, 14, -1000, -700),
    ])
    save_stocks(session, [stock(111, 50)])
    item = article_report(session, days=30, period_end=END)["items"][0]

    assert item["sold_qty"] == 3
    assert item["returned_qty"] == 1
    assert item["net_qty"] == 2
    assert item["revenue"] == 2000.0
    assert item["for_pay"] == 1400.0
    assert item["return_rate_pct"] == 33.3


def test_return_sign_does_not_matter(session):
    # Если WB отдаст сумму возврата положительной — результат должен быть тем же.
    save_sales(session, [
        sale("o1", "S1", 111, 10, 1000, 700),
        sale("o1", "R1", 111, 12, 1000, 700),
    ])
    item = article_report(session, days=30, period_end=END)["items"][0]
    assert item["revenue"] == 0.0


def test_days_of_stock_and_statuses(session):
    # Артикул 1: 30 продаж за 30 дней (1 в день), остаток 10 → хватит на 10 дней → дефицит
    # Артикул 2: продаж нет, остаток 100 → «нет продаж»
    # Артикул 3: 30 продаж, остаток 60 → 60 дней → норма
    rows = [sale(f"a{i}", f"S{i}", 1, (i % 29) + 1, 500, 350) for i in range(30)]
    rows += [sale(f"c{i}", f"SC{i}", 3, (i % 29) + 1, 500, 350) for i in range(30)]
    save_sales(session, rows)
    save_stocks(session, [stock(1, 10), stock(2, 100), stock(3, 30, wh=1), stock(3, 30, wh=2)])

    items = {i["nm_id"]: i for i in article_report(session, days=30, period_end=END)["items"]}
    assert items[1]["days_of_stock"] == 10.0
    assert items[1]["status"] == "дефицит"
    assert items[2]["status"] == "нет продаж"
    assert items[3]["stock_qty"] == 60  # остатки по двум складам сложились
    assert items[3]["status"] == "норма"


def test_reload_does_not_duplicate(session):
    rows = [sale("o1", "S1", 111, 10, 1000, 700)]
    save_sales(session, rows)
    save_sales(session, rows)  # повторная синхронизация тех же данных
    item = article_report(session, days=30, period_end=END)["items"][0]
    assert item["sold_qty"] == 1
