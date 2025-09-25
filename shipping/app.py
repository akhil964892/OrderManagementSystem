import os, json, threading, time
import pika
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from models import Base, Shipment

DB_URL = os.getenv("DB_URL", "sqlite:///./shipping.sqlite")
RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
RABBITMQ_QUEUE = os.getenv("RABBITMQ_QUEUE", "orders")

engine = create_engine(DB_URL, connect_args={"check_same_thread": False} if DB_URL.startswith("sqlite") else {})
Base.metadata.create_all(engine)

app = FastAPI(title="Shipping Service", version="1.0.0")

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/shipping/{order_id}")
def get_shipping(order_id: int):
    with Session(engine) as s:
        sh = s.execute(select(Shipment).where(Shipment.order_id == order_id)).scalar_one_or_none()
        if not sh:
            raise HTTPException(status_code=404, detail="Not found")
        return {"order_id": sh.order_id, "status": sh.status, "tracking_number": sh.tracking_number}

def process_event(event: dict):
    if event.get("type") != "order.created":
        return
    order = event.get("order", {})
    order_id = order.get("id")
    with Session(engine) as s:
        existing = s.execute(select(Shipment).where(Shipment.order_id == order_id)).scalar_one_or_none()
        if existing:
            return
        sh = Shipment(order_id=order_id, status="PROCESSING", tracking_number=f"TRK-{order_id:06d}")
        s.add(sh)
        s.commit()
        print(f"[Shipping] Created shipment for order {order_id}")

def _consume_loop():
    # Retry loop to avoid crashing if RabbitMQ isn't up yet
    while True:
        try:
            params = pika.URLParameters(RABBITMQ_URL)
            connection = pika.BlockingConnection(params)
            ch = connection.channel()
            ch.queue_declare(queue=RABBITMQ_QUEUE, durable=False)
            def callback(chx, method, properties, body):
                try:
                    event = json.loads(body.decode("utf-8"))
                    process_event(event)
                except Exception as e:
                    print(f"[ERROR] Failed to process event: {e}")
            ch.basic_consume(queue=RABBITMQ_QUEUE, on_message_callback=callback, auto_ack=True)
            print("[Shipping] Consumer started")
            ch.start_consuming()
        except Exception as e:
            print(f"[WARN] Rabbit consumer error: {e}. Retrying in 3s...")
            time.sleep(3)

@app.on_event("startup")
def startup_event():
    t = threading.Thread(target=_consume_loop, daemon=True)
    t.start()
