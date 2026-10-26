"""Pruebas de integración de la API (Parte 3)."""
import pytest
from fastapi.testclient import TestClient

from app import api
from cargar_csv import load_fixture


@pytest.fixture
def client():
    """Cliente con fixtures recargados: cada prueba parte de datos limpios."""
    api.orders.clear()
    api.orders.update(load_fixture())
    return TestClient(api.app)


def post_ship(client, oid, guia="GUIA-123"):
    return client.post(f"/orders/{oid}/ship", json={"tracking_number": guia})


# ------------------------------------------------------------------ GET
def test_get_pedido_formateado(client):
    r = client.get("/orders/O001")
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == "O001" and body["status"] == "DRAFT"
    assert body["units"] == 4
    assert body["total"] == {"amount": "2100.00", "currency": "MXN"}
    assert body["customer"] == {"id": "C001", "is_vip": True, "active": True}
    assert len(body["items"]) == 2
    assert body["discount_rate"] == "0.10"
    assert body["events"] == []


def test_get_pedido_inexistente_404(client):
    assert client.get("/orders/NOPE").status_code == 404


# -------------------------------------------------------------- confirm
def test_confirm_exitoso(client):
    r = client.post("/orders/O013/confirm")
    assert r.status_code == 200
    assert r.json() == {"id": "O013", "status": "CONFIRMED",
                        "events": ["OrderConfirmed"]}


def test_confirm_inexistente_404(client):
    assert client.post("/orders/NOPE/confirm").status_code == 404


def test_confirm_doble_409_sin_evento_extra(client):
    assert client.post("/orders/O013/confirm").status_code == 200
    r = client.post("/orders/O013/confirm")
    assert r.status_code == 409
    estado = client.get("/orders/O013").json()
    assert [e["name"] for e in estado["events"]] == ["OrderConfirmed"]


def test_confirm_pedido_vacio_422(client):
    r = client.post("/orders/O007/confirm")
    assert r.status_code == 422
    assert client.get("/orders/O007").json()["status"] == "DRAFT"


def test_confirm_cliente_inactivo_422(client):
    assert client.post("/orders/O003/confirm").status_code == 422


def test_confirm_20_unidades_ok(client):
    assert client.post("/orders/O008/confirm").status_code == 200


# ----------------------------------------------------------------- ship
def test_ship_exitoso(client):
    client.post("/orders/O012/confirm")
    r = post_ship(client, "O012")
    assert r.status_code == 200
    assert r.json()["status"] == "SHIPPED"
    assert r.json()["events"] == ["OrderConfirmed", "OrderShipped"]


def test_ship_sin_guia_422(client):
    client.post("/orders/O012/confirm")
    r = post_ship(client, "O012", guia="   ")
    assert r.status_code == 422
    assert client.get("/orders/O012").json()["status"] == "CONFIRMED"


def test_ship_sin_cuerpo_422(client):
    client.post("/orders/O012/confirm")
    assert client.post("/orders/O012/ship").status_code == 422


def test_ship_desde_draft_409(client):
    assert post_ship(client, "O012").status_code == 409


def test_ship_inexistente_404(client):
    assert post_ship(client, "NOPE").status_code == 404


# --------------------------------------------------------------- cancel
def test_cancel_desde_confirmed(client):
    client.post("/orders/O014/confirm")
    r = client.post("/orders/O014/cancel", json={"reason": "Pedido duplicado"})
    assert r.status_code == 200
    assert r.json()["status"] == "CANCELLED"
    assert r.json()["events"][-1] == "OrderCancelled"


def test_cancel_desde_shipped_409(client):
    client.post("/orders/O014/confirm")
    post_ship(client, "O014")
    r = client.post("/orders/O014/cancel", json={"reason": "Tarde"})
    assert r.status_code == 409
    assert client.get("/orders/O014").json()["status"] == "SHIPPED"


def test_cancel_sin_motivo_422(client):
    client.post("/orders/O014/confirm")
    r = client.post("/orders/O014/cancel", json={"reason": ""})
    assert r.status_code == 422
    assert client.get("/orders/O014").json()["status"] == "CONFIRMED"


def test_cancel_inexistente_404(client):
    r = client.post("/orders/NOPE/cancel", json={"reason": "x"})
    assert r.status_code == 404


# ------------------------------------------------------------ documentación
def test_openapi_y_docs_disponibles(client):
    assert client.get("/docs").status_code == 200
    paths = client.get("/openapi.json").json()["paths"]
    assert "/orders/{order_id}" in paths
    for ruta in ("confirm", "ship", "cancel"):
        assert f"/orders/{{order_id}}/{ruta}" in paths
