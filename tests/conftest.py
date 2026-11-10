import pytest
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy import create_engine

from app.db import init_db


@pytest.fixture()
def session():
    """Отдельная база в памяти для каждого теста — тесты не мешают друг другу."""
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    init_db(bind=engine)
    s = sessionmaker(bind=engine, expire_on_commit=False)()
    yield s
    s.close()
