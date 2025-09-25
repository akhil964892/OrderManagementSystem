# Order Management System (FastAPI + RabbitMQ + Kubernetes)
*Assignment for 4th Orbit Internship Cum PPO Recruitment Drive-2026 Batch*
**Video Representation:** https://drive.google.com/file/d/1pfEsS1DVAOtgLJjc9yiTou7aU5syUoJ9/view?usp=sharing

Minimal microservices demo you can run quickly on **Minikube** or **Docker Desktop (Kubernetes)**.

**Services**:
- **Inventory**: product CRUD (SQLite)
- **Order**: place orders, generate invoice JSON, publish `order.created` to RabbitMQ (SQLite)
- **Shipping**: consumes events, creates shipment, exposes status (SQLite)

Each service exposes OpenAPI/Swagger at `/docs`.

## Quick Run (Local without K8s)

Open three terminals:

```bash
# Terminal 1 - Inventory
cd inventory
pip install -r requirements.txt
uvicorn app:app --reload --port 8000

# Terminal 2 - RabbitMQ (Docker required)
docker run -it --rm -p 5672:5672 -p 15672:15672 rabbitmq:3-management

# Terminal 3 - Order
cd order
pip install -r requirements.txt
export INVENTORY_URL=http://localhost:8000
export RABBITMQ_URL=amqp://guest:guest@localhost:5672/
uvicorn app:app --reload --port 8002

# Terminal 4 - Shipping
cd shipping
pip install -r requirements.txt
export RABBITMQ_URL=amqp://guest:guest@localhost:5672/
uvicorn app:app --reload --port 8003
```

Test end-to-end (adjust ports if needed):
```bash
curl -X POST http://localhost:8000/products -H "Content-Type: application/json" -d '{"sku":"ABC","name":"Widget","price":100,"qty":50}'
curl -X POST http://localhost:8002/orders -H "Content-Type: application/json" -d '{"items":[{"sku":"ABC","qty":2}],"customer":{"name":"Alice"}}'
curl http://localhost:8002/orders/1/invoice
curl http://localhost:8003/shipping/1
```

## Kubernetes (Minikube)

1) Start Minikube and use its Docker daemon so local images are visible:
```bash
minikube start
eval $(minikube -p minikube docker-env)
```

2) Build images:
```bash
# From repo root
docker build -t inventory:latest ./inventory
docker build -t order:latest ./order
docker build -t shipping:latest ./shipping
```

3) Deploy RabbitMQ and services:
```bash
kubectl apply -f k8s/rabbitmq.yaml
kubectl apply -f k8s/inventory.yaml
kubectl apply -f k8s/order.yaml
kubectl apply -f k8s/shipping.yaml
```

4) Port-forward for quick access (in separate terminals):
```bash
kubectl port-forward deploy/inventory 8001:8000
kubectl port-forward deploy/order 8002:8000
kubectl port-forward deploy/shipping 8003:8000
```

5) Run the demo script:
```bash
./scripts/curl_demo.sh
```

(Optional) Access Swagger UIs:
- Inventory: http://localhost:8001/docs
- Order: http://localhost:8002/docs
- Shipping: http://localhost:8003/docs

### Notes / Assumptions
- Databases use **SQLite** per service (mounted as `emptyDir`). Good enough for demo and meets "separate DB" requirement.
- Event broker is **RabbitMQ** with default `guest/guest` credentials (inside cluster only).
- Inventory stock reservation is simplified (read then update). Good for demo flow.
- Invoice is JSON; you can extend to PDF easily.

## API Summary

### Inventory
- `POST /products` → add product `{sku,name,price,qty}`
- `PUT /products/{sku}` → update any field (commonly `qty`)
- `GET /products/{sku}` → fetch product

### Order
- `POST /orders` → create order, checks stock via Inventory, reserves qty, publishes `order.created`
- `GET /orders/{id}` → fetch order
- `GET /orders/{id}/invoice` → invoice JSON

### Shipping
- `GET /shipping/{orderId}` → shipment status

## Testing with Postman
Import `scripts/curl_demo.sh` commands or call the endpoints directly. Swagger UIs provide request/response schemas.

## License
MIT




* Full Setup & Run Guide (Windows 10/11)
1. Install prerequisites
    Make sure these are installed:
        Docker Desktop
            → for RabbitMQ
        Python 3.10
            → recommended (since we have uvicorn )
        Node.js 18+
            → for the React UI

2. Start RabbitMQ
    Open PowerShell and run:
    docker run -it --rm -p 5672:5672 -p 15672:15672 rabbitmq:3-management
    RabbitMQ management console → http://localhost:15672
    (user: guest, password: guest)
    Keep this terminal running.

3. Run each microservice
    You have 3 services: Inventory (8000), Order (8002), Shipping (8003).
    Each needs a venv, dependencies, and uvicorn.

    A) Inventory Service
        cd C:\Users\KIIT\Desktop\oms\inventory
        py -3.10 -m venv .venv
        .\.venv\Scripts\activate.bat
        pip install -r requirements.txt
        python -m uvicorn app:app --reload --port 8000

        Test: open http://localhost:8000/docs

    B) Order Service
        Open new PowerShell window:
        cd C:\Users\KIIT\Desktop\oms\order
        py -3.10 -m venv .venv
        .\.venv\Scripts\activate.bat
        pip install -r requirements.txt
        python -m uvicorn app:app --reload --port 8002

        Test: open http://localhost:8002/docs

    C) Shipping Service
        Open new PowerShell window:
        cd C:\Users\KIIT\Desktop\oms\shipping
        py -3.10 -m venv .venv
        .\.venv\Scripts\activate.bat
        pip install -r requirements.txt
        python -m uvicorn app:app --reload --port 8003

        Test: open http://localhost:8003/docs

4. Run the React UI

    Open new PowerShell window:
    cd C:\Users\KIIT\Desktop\oms\ui
    npm install
    Copy-Item .env.example .env
    notepad .env

    Inside .env, set:
    VITE_INV=http://localhost:8000
    VITE_ORD=http://localhost:8002
    VITE_SHP=http://localhost:8003


    Then run:
    npm run dev

    UI → http://localhost:5173
