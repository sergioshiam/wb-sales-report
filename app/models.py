"""Таблицы базы данных.

sales  — продажи и возвраты из метода WB GET /api/v1/supplier/sales.
         Одна строка = одна единица товара (продажа S... или возврат R...).
stocks — текущие остатки из метода WB POST /api/analytics/v1/stocks-report/wb-warehouses.
         Одна строка = один размер товара на одном складе.
"""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Sale(Base):
    __tablename__ = "sales"

    # Ключ из двух полей: srid — ID заказа, sale_id — ID продажи или возврата.
    # У продажи и возврата одного заказа srid одинаковый, а sale_id разный (S... / R...).
    srid: Mapped[str] = mapped_column(String(64), primary_key=True)
    sale_id: Mapped[str] = mapped_column(String(32), primary_key=True)

    date: Mapped[datetime] = mapped_column(DateTime)
    last_change_date: Mapped[datetime] = mapped_column(DateTime)
    nm_id: Mapped[int] = mapped_column(BigInteger, index=True)  # артикул WB
    supplier_article: Mapped[str] = mapped_column(String(128), default="")  # артикул продавца
    subject: Mapped[str] = mapped_column(String(128), default="")  # предмет (категория)
    brand: Mapped[str] = mapped_column(String(128), default="")
    tech_size: Mapped[str] = mapped_column(String(32), default="")
    warehouse_name: Mapped[str] = mapped_column(String(128), default="")
    region_name: Mapped[str] = mapped_column(String(128), default="")
    finished_price: Mapped[float] = mapped_column(Float, default=0)  # заплатил покупатель
    for_pay: Mapped[float] = mapped_column(Float, default=0)  # к перечислению продавцу

    @property
    def is_return(self) -> bool:
        return self.sale_id.upper().startswith("R")


class Stock(Base):
    __tablename__ = "stocks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nm_id: Mapped[int] = mapped_column(BigInteger, index=True)
    chrt_id: Mapped[int] = mapped_column(BigInteger)  # ID размера
    warehouse_id: Mapped[int] = mapped_column(BigInteger)
    warehouse_name: Mapped[str] = mapped_column(String(128), default="")
    region_name: Mapped[str] = mapped_column(String(128), default="")
    quantity: Mapped[int] = mapped_column(Integer, default=0)  # доступно к заказу
    in_way_to_client: Mapped[int] = mapped_column(Integer, default=0)
    in_way_from_client: Mapped[int] = mapped_column(Integer, default=0)
