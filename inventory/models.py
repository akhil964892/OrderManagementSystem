from sqlalchemy.orm import declarative_base, Mapped, mapped_column, Session
from sqlalchemy import String, Integer, Float, create_engine, select
from typing import Optional

Base = declarative_base()

class Product(Base):
    __tablename__ = "products"
    sku: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    price: Mapped[float] = mapped_column(Float)
    qty: Mapped[int] = mapped_column(Integer)
