"""Подключение к базе данных через SQLAlchemy.

SQLAlchemy — библиотека, которая позволяет работать с базой данных из Python,
описывая таблицы как классы. Один и тот же код работает и с PostgreSQL, и с SQLite.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app import config


class Base(DeclarativeBase):
    """Базовый класс для всех таблиц."""


def make_engine(url: str):
    # Для SQLite нужен особый флаг, чтобы базу можно было использовать из разных потоков.
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, connect_args=connect_args)


engine = make_engine(config.DATABASE_URL)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def init_db(bind=None) -> None:
    """Создаёт таблицы, если их ещё нет."""
    from app import models  # noqa: F401 — импорт регистрирует таблицы

    Base.metadata.create_all(bind=bind or engine)
