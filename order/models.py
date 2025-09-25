from sqlalchemy.orm import declarative_base, Mapped, mapped_column
from sqlalchemy import String, Integer, Float, JSON, create_engine
from typing import Optional

Base = declarative_base()

class Order(Base):
    __tablename__ = "orders"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    customer_name: Mapped[str] = mapped_column(String(255))
    total_amount: Mapped[float] = mapped_column(Float)
    items_json: Mapped[dict] = mapped_column(JSON)
