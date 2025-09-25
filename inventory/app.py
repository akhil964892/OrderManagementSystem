import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from models import Base, Product

DB_URL = os.getenv("DB_URL", "sqlite:///./inventory.sqlite")
engine = create_engine(DB_URL, connect_args={"check_same_thread": False} if DB_URL.startswith("sqlite") else {})
Base.metadata.create_all(engine)

app = FastAPI(title="Inventory Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # allow React dev server calls
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ProductIn(BaseModel):
    sku: str = Field(..., example="SKU123")
    name: str = Field(..., example="Widget")
    price: float = Field(..., example=99.99)
    qty: int = Field(..., ge=0, example=100)

class ProductUpdate(BaseModel):
    name: Optional[str] = Field(None, example="Widget")
    price: Optional[float] = Field(None, example=99.99)
    qty: Optional[int] = Field(None, ge=0, example=100)

class ProductOut(BaseModel):
    sku: str
    name: str
    price: float
    qty: int

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/products", response_model=ProductOut, status_code=201)
def create_product(p: ProductIn):
    with Session(engine) as s:
        existing = s.get(Product, p.sku)
        if existing:
            raise HTTPException(status_code=409, detail="SKU already exists")
        product = Product(sku=p.sku, name=p.name, price=p.price, qty=p.qty)
        s.add(product)
        s.commit()
        s.refresh(product)
        return product

@app.put("/products/{sku}", response_model=ProductOut)
def update_product(sku: str, p: ProductUpdate):
    with Session(engine) as s:
        product = s.get(Product, sku)
        if not product:
            raise HTTPException(status_code=404, detail="Not found")
        if p.name is not None:
            product.name = p.name
        if p.price is not None:
            product.price = p.price
        if p.qty is not None:
            if p.qty < 0:
                raise HTTPException(status_code=400, detail="qty cannot be negative")
            product.qty = p.qty
        s.commit()
        s.refresh(product)
        return product

@app.get("/products/{sku}", response_model=ProductOut)
def get_product(sku: str):
    with Session(engine) as s:
        product = s.get(Product, sku)
        if not product:
            raise HTTPException(status_code=404, detail="Not found")
        return product
