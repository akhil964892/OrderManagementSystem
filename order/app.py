import os, json, time
import requests
import pika
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from models import Base, Order

DB_URL = os.getenv("DB_URL", "sqlite:///./orders.sqlite")
INVENTORY_URL = os.getenv("INVENTORY_URL", "http://localhost:8000")
RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
RABBITMQ_QUEUE = os.getenv("RABBITMQ_QUEUE", "orders")

engine = create_engine(DB_URL, connect_args={"check_same_thread": False} if DB_URL.startswith("sqlite") else {})
Base.metadata.create_all(engine)

app = FastAPI(title="Order Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # demo-friendly
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class OrderItem(BaseModel):
    sku: str = Field(..., example="SKU123")
    qty: int = Field(..., ge=1, example=2)

class Customer(BaseModel):
    name: str = Field(..., example="Alice")
    email: str = Field(None, example="alice@example.com")

class OrderIn(BaseModel):
    items: List[OrderItem]
    customer: Customer

class OrderOut(BaseModel):
    id: int
    total_amount: float
    items: List[OrderItem]
    customer_name: str

def publish_event(event: dict):
    try:
        params = pika.URLParameters(RABBITMQ_URL)
        connection = pika.BlockingConnection(params)
        ch = connection.channel()
        ch.queue_declare(queue=RABBITMQ_QUEUE, durable=False)
        ch.basic_publish(exchange="", routing_key=RABBITMQ_QUEUE, body=json.dumps(event).encode("utf-8"))
        connection.close()
    except Exception as e:
        # In a rush demo, we don't fail the order if broker is down; we just log.
        print(f"[WARN] Failed to publish event: {e}")

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/orders", response_model=OrderOut, status_code=201)
def create_order(payload: OrderIn):
    # 1) Check all items exist and have stock; compute total
    total = 0.0
    fetched = []
    for it in payload.items:
        r = requests.get(f"{INVENTORY_URL}/products/{it.sku}", timeout=5)
        if r.status_code != 200:
            raise HTTPException(status_code=400, detail=f"SKU {it.sku} not found")
        prod = r.json()
        if prod["qty"] < it.qty:
            raise HTTPException(status_code=400, detail=f"Insufficient qty for {it.sku}")
        total += prod["price"] * it.qty
        fetched.append(prod)

    # 2) Reserve stock (simplified): update product qty to (current - ordered)
    for it, prod in zip(payload.items, fetched):
        new_qty = prod["qty"] - it.qty
        r2 = requests.put(f"{INVENTORY_URL}/products/{it.sku}", json={"qty": new_qty}, timeout=5)
        if r2.status_code != 200:
            raise HTTPException(status_code=409, detail=f"Failed to reserve stock for {it.sku}")

    # 3) Persist order
    with Session(engine) as s:
        order = Order(customer_name=payload.customer.name, total_amount=total, items_json={"items": [i.model_dump() for i in payload.items]})
        s.add(order)
        s.commit()
        s.refresh(order)

        event = {
            "type": "order.created",
            "ts": int(time.time()),
            "order": {
                "id": order.id,
                "customer_name": order.customer_name,
                "total_amount": order.total_amount,
                "items": [i.model_dump() for i in payload.items],
            }
        }
        publish_event(event)

        return {"id": order.id, "total_amount": order.total_amount, "items": payload.items, "customer_name": order.customer_name}

@app.get("/orders/{order_id}", response_model=OrderOut)
def get_order(order_id: int):
    with Session(engine) as s:
        o = s.get(Order, order_id)
        if not o:
            raise HTTPException(status_code=404, detail="Not found")
        return {"id": o.id, "total_amount": o.total_amount, "items": o.items_json.get("items", []), "customer_name": o.customer_name}

@app.get("/orders/{order_id}/invoice")
def get_invoice(order_id: int):
    with Session(engine) as s:
        o = s.get(Order, order_id)
        if not o:
            raise HTTPException(status_code=404, detail="Not found")
        # Simple JSON invoice; could be extended to PDF
        return {
            "invoice_id": f"INV-{order_id:06d}",
            "order_id": o.id,
            "billed_to": o.customer_name,
            "line_items": o.items_json.get("items", []),
            "subtotal": o.total_amount,
            "tax": round(o.total_amount * 0.1, 2),
            "total": round(o.total_amount * 1.1, 2),
        }
from fastapi.responses import StreamingResponse
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

@app.get("/orders/{order_id}/invoice.pdf")
def get_invoice_pdf(order_id: int):
    with Session(engine) as s:
        o = s.get(Order, order_id)
        if not o:
            raise HTTPException(status_code=404, detail="Not found")
        data = {
            "invoice_id": f"INV-{order_id:06d}",
            "order_id": o.id,
            "billed_to": o.customer_name,
            "line_items": o.items_json.get("items", []),
            "subtotal": o.total_amount,
            "tax": round(o.total_amount * 0.1, 2),
            "total": round(o.total_amount * 1.1, 2),
        }
    # Generate PDF in-memory
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    width, height = A4

    y = height - 50
    c.setFont("Helvetica-Bold", 16)
    c.drawString(40, y, "Invoice")
    y -= 25
    c.setFont("Helvetica", 12)
    c.drawString(40, y, f"Invoice ID: {data['invoice_id']}")
    y -= 18
    c.drawString(40, y, f"Order ID: {data['order_id']}")
    y -= 18
    c.drawString(40, y, f"Billed To: {data['billed_to']}")
    y -= 28
    c.setFont("Helvetica-Bold", 12)
    c.drawString(40, y, "Items")
    y -= 18
    c.setFont("Helvetica", 12)
    for it in data["line_items"]:
        c.drawString(50, y, f"- {it['sku']} x {it['qty']}")
        y -= 16
        if y < 80:
            c.showPage()
            y = height - 50
            c.setFont("Helvetica", 12)
    y -= 10
    c.setFont("Helvetica-Bold", 12)
    c.drawString(40, y, f"Subtotal: {data['subtotal']:.2f}")
    y -= 18
    c.drawString(40, y, f"Tax (10%): {data['tax']:.2f}")
    y -= 18
    c.drawString(40, y, f"Total: {data['total']:.2f}")
    c.showPage()
    c.save()
    buf.seek(0)
    headers = {"Content-Disposition": f'inline; filename="{data["invoice_id"]}.pdf"'}
    return StreamingResponse(buf, headers=headers, media_type="application/pdf")
