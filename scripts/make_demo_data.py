"""Генерирует демо-данные в формате ответов API Wildberries.

Бренд и товары вымышленные. Данные нужны, чтобы сервис можно было запустить
и показать без настоящего токена продавца.

Запуск: python scripts/make_demo_data.py
"""

import json
import random
from datetime import datetime, timedelta
from pathlib import Path

random.seed(42)  # одинаковые данные при каждом запуске

DATA = Path(__file__).resolve().parent.parent / "data"

# nmId, артикул продавца, предмет, цена со скидкой, продаж в день, размеры, остаток на размер
PRODUCTS = [
    (210000101, "DEMO-LEG-01", "Леггинсы", 1490, 6.0, ["S", "M", "L"], 60),
    (210000102, "DEMO-LEG-02", "Леггинсы", 1690, 3.0, ["S", "M", "L"], 8),     # скоро закончится
    (210000203, "DEMO-TOP-01", "Топы", 990, 4.0, ["S", "M"], 90),
    (210000304, "DEMO-SET-01", "Комплекты термобелья", 2890, 1.5, ["M", "L", "XL"], 25),
    (210000405, "DEMO-SOCK-01", "Носки", 390, 0.0, ["0"], 300),                  # лежит без продаж
]
WAREHOUSES = [(507, "Коледино", "Россия"), (117986, "Казань", "Россия"), (1733, "Екатеринбург - Испытателей 14г", "Россия")]
REGIONS = ["Московская", "Татарстан", "Свердловская", "Краснодарский", "Новосибирская"]

END = datetime(2026, 10, 31, 23, 0, 0)
DAYS = 30


def make_sales():
    rows = []
    counter = 1
    for nm_id, article, subject, price, per_day, sizes, _ in PRODUCTS:
        for d in range(DAYS):
            day = END - timedelta(days=DAYS - 1 - d)
            n = max(0, round(random.gauss(per_day, per_day * 0.4))) if per_day else 0
            for _ in range(n):
                ts = day.replace(hour=random.randint(8, 22), minute=random.randint(0, 59))
                wh = random.choice(WAREHOUSES)
                finished = round(price * random.uniform(0.85, 0.95))  # минус скидка WB / СПП
                for_pay = round(price * 0.72, 2)  # после комиссии WB
                srid = f"demo{counter:07d}.0.0"
                base = {
                    "date": ts.isoformat(),
                    "lastChangeDate": (ts + timedelta(hours=2)).isoformat(),
                    "warehouseName": wh[1],
                    "warehouseType": "Склад WB",
                    "countryName": "Россия",
                    "oblastOkrugName": "",
                    "regionName": random.choice(REGIONS),
                    "supplierArticle": article,
                    "nmId": nm_id,
                    "barcode": f"20000{nm_id}",
                    "category": "Одежда",
                    "subject": subject,
                    "brand": "ДемоБренд",
                    "techSize": random.choice(sizes),
                    "incomeID": 1000 + d,
                    "isSupply": False,
                    "isRealization": True,
                    "totalPrice": price * 2,
                    "discountPercent": 50,
                    "spp": 8,
                    "paymentSaleAmount": 0,
                    "forPay": for_pay,
                    "finishedPrice": finished,
                    "priceWithDisc": price,
                    "saleID": f"S{counter:010d}",
                    "sticker": "",
                    "gNumber": f"g{counter}",
                    "srid": srid,
                }
                rows.append(base)
                # ~8% возвратов: возврат приходит через 3–6 дней с тем же srid и saleID на R
                if random.random() < 0.08:
                    ret_ts = ts + timedelta(days=random.randint(3, 6))
                    if ret_ts <= END:
                        ret = dict(base)
                        ret.update(
                            date=ret_ts.isoformat(),
                            lastChangeDate=(ret_ts + timedelta(hours=1)).isoformat(),
                            saleID=f"R{counter:010d}",
                            forPay=-for_pay,
                            finishedPrice=-finished,
                            priceWithDisc=-price,
                        )
                        rows.append(ret)
                counter += 1
    rows.sort(key=lambda r: r["lastChangeDate"])
    return rows


def make_stocks():
    rows = []
    chrt = 900000000
    for nm_id, _a, _s, _p, _pd, sizes, stock_per_size in PRODUCTS:
        for size in sizes:
            chrt += 1
            for wh_id, wh_name, region in WAREHOUSES:
                rows.append(
                    {
                        "nmId": nm_id,
                        "chrtId": chrt,
                        "warehouseId": wh_id,
                        "warehouseName": wh_name,
                        "regionName": region,
                        "quantity": max(0, round(stock_per_size / len(WAREHOUSES))),
                        "inWayToClient": random.randint(0, 3),
                        "inWayFromClient": random.randint(0, 1),
                    }
                )
    return rows


if __name__ == "__main__":
    DATA.mkdir(exist_ok=True)
    sales, stocks = make_sales(), make_stocks()
    (DATA / "demo_sales.json").write_text(json.dumps(sales, ensure_ascii=False, indent=1), encoding="utf-8")
    (DATA / "demo_stocks.json").write_text(json.dumps(stocks, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"sales: {len(sales)} строк, stocks: {len(stocks)} строк")
