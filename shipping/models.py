from sqlalchemy.orm import declarative_base, Mapped, mapped_column
from sqlalchemy import String, Integer, create_engine
from typing import Optional

Base = declarative_base()

class Shipment(Base):
    __tablename__ = "shipments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(Integer, index=True)
    status: Mapped[str] = mapped_column(String(64), default="PROCESSING")  # PROCESSING, SHIPPED, DELIVERED
    tracking_number: Mapped[str] = mapped_column(String(64), default="TBD")
