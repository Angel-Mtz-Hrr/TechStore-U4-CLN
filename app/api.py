"""API REST de TechStore U4 (Parte 3).

Los endpoints solo buscan el pedido, delegan en el dominio y traducen las
excepciones de negocio a códigos HTTP. Las reglas viven en app/domain.py.
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.domain import (
    InvalidOrderData,
    InvalidOrderTransition,
    Order,
    OrderItemLimitExceeded,
)
from app.specifications import discount_rate
from cargar_csv import load_fixture

app = FastAPI(
    title="TechStore U4",
    description="Núcleo de negocio de pedidos (en memoria). "
    "Los cambios se pierden al reiniciar el servidor.",
)

# Repositorio en memoria: se llena al iniciar la aplicación.
orders: dict[str, Order] = load_fixture()


# ------------------------------------------------------------ esquemas
class ShipRequest(BaseModel):
    tracking_number: str


class CancelRequest(BaseModel):
    reason: str


# ------------------------------------------------- errores de dominio → HTTP
@app.exception_handler(InvalidOrderTransition)
async def _transition_error(_: Request, exc: InvalidOrderTransition):
    return JSONResponse(status_code=409, content={"detail": str(exc)})


@app.exception_handler(InvalidOrderData)
@app.exception_handler(OrderItemLimitExceeded)
async def _data_error(_: Request, exc: Exception):
    return JSONResponse(status_code=422, content={"detail": str(exc)})


# ------------------------------------------------------------- utilidades
def get_order_or_404(order_id: str) -> Order:
    order = orders.get(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail=f"No existe el pedido {order_id}")
    return order


def serialize(order: Order) -> dict:
    return {
        "id": order.id,
        "customer": {
            "id": order.customer.id,
            "is_vip": order.customer.is_vip,
            "active": order.customer.active,
        },
        "status": order.status.value,
        "has_promotion": order.has_promotion,
        "items": [
            {
                "sku": i.sku,
                "quantity": i.quantity,
                "unit_price": str(i.unit_price.amount),
                "subtotal": str(i.subtotal.amount),
            }
            for i in order.items
        ],
        "units": order.units,
        "total": {"amount": str(order.total.amount), "currency": order.total.currency},
        "discount_rate": str(discount_rate(order)),
        "events": [
            {"name": e.name, "occurred_at": e.occurred_at.isoformat()}
            for e in order.events
        ],
    }


def summary(order: Order) -> dict:
    return {
        "id": order.id,
        "status": order.status.value,
        "events": [e.name for e in order.events],
    }


# -------------------------------------------------------------- endpoints
@app.get("/orders/{order_id}")
def get_order(order_id: str):
    return serialize(get_order_or_404(order_id))


@app.post("/orders/{order_id}/confirm")
def confirm_order(order_id: str):
    order = get_order_or_404(order_id)
    order.confirm()
    return summary(order)


@app.post("/orders/{order_id}/ship")
def ship_order(order_id: str, body: ShipRequest):
    order = get_order_or_404(order_id)
    order.ship(body.tracking_number)
    return summary(order)


@app.post("/orders/{order_id}/cancel")
def cancel_order(order_id: str, body: CancelRequest):
    order = get_order_or_404(order_id)
    order.cancel(body.reason)
    return summary(order)


@app.post("/orders/{order_id}/deliver")
def deliver_order(order_id: str):
    order = get_order_or_404(order_id)
    order.deliver()
    return summary(order)


@app.post("/orders/{order_id}/return")
def return_order(order_id: str):
    order = get_order_or_404(order_id)
    order.return_order()
    return summary(order)
