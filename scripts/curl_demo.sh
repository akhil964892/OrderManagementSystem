#!/usr/bin/env bash
set -euo pipefail

# This script assumes port-forwards:
# kubectl port-forward deploy/inventory 8001:8000 &
# kubectl port-forward deploy/order 8002:8000 &
# kubectl port-forward deploy/shipping 8003:8000 &

INV=http://localhost:8001
ORD=http://localhost:8002
SHP=http://localhost:8003

echo "==> Health checks"
curl -s $INV/health; echo
curl -s $ORD/health; echo
curl -s $SHP/health; echo

echo "==> Add product"
curl -s -X POST $INV/products -H "Content-Type: application/json" -d '{"sku":"ABC","name":"Widget","price":100,"qty":50}'; echo

echo "==> Place order"
ORDER=$(curl -s -X POST $ORD/orders -H "Content-Type: application/json" -d '{"items":[{"sku":"ABC","qty":2}],"customer":{"name":"Alice","email":"alice@example.com"}}')
echo $ORDER
OID=$(echo $ORDER | python -c 'import sys,json; print(json.load(sys.stdin)["id"])')

echo "==> Invoice"
curl -s $ORD/orders/$OID/invoice; echo

echo "==> Wait for shipping to process event..."
sleep 2

echo "==> Shipping status"
curl -s $SHP/shipping/$OID; echo
