"""Pruebas de dominio y Specifications (Partes 1 y 2)."""
from dataclasses import FrozenInstanceError
from decimal import Decimal

import pytest

from app.domain import (
    Customer, DomainEvent, InvalidOrderData, InvalidOrderTransition, Money,
    Order, OrderItem, OrderItemLimitExceeded, OrderStatus,
)
from app.specifications import (
    ActivePromotionSpec, FIVE_PERCENT_SPEC, MinimumAmountSpec,
    MinimumUnitsSpec, TEN_PERCENT_SPEC, VIPCustomerSpec, discount_rate,
)
from cargar_csv import load_fixture


# ---------------------------------------------------------------- helpers
def mxn(valor: str) -> Money:
    return Money(Decimal(valor))


def make_order(units=1, price="100.00", vip=False, active=True, promo=False,
               oid="T1") -> Order:
    order = Order(Customer("C", vip, active), oid, promo)
    if units:
        order.add_item(OrderItem("SKU", units, mxn(price)))
    return order


@pytest.fixture
def orders():
    return load_fixture()


# ------------------------------------------------------------------ Money
def test_money_negativo():
    with pytest.raises(InvalidOrderData):
        Money(Decimal("-1"))


@pytest.mark.parametrize("valor", ["NaN", "Infinity", "-Infinity"])
def test_money_no_finito(valor):
    with pytest.raises(InvalidOrderData):
        Money(Decimal(valor))


def test_money_rechaza_float():
    with pytest.raises(InvalidOrderData):
        Money(600.0)


def test_money_cero_es_valido():
    assert Money(Decimal("0")).amount == 0


def test_money_add_suma_y_devuelve_objeto_nuevo():
    a, b = mxn("10.50"), mxn("4.50")
    resultado = a.add(b)
    assert resultado.amount == Decimal("15.00")
    assert resultado is not a and a.amount == Decimal("10.50")


def test_money_monedas_distintas():
    with pytest.raises(InvalidOrderData):
        mxn("1").add(Money(Decimal("1"), "USD"))


def test_money_es_inmutable():
    with pytest.raises(FrozenInstanceError):
        mxn("1").amount = Decimal("2")


# ---------------------------------------------------------------- OrderItem
def test_item_subtotal():
    assert OrderItem("SKU001", 2, mxn("600.00")).subtotal.amount == Decimal("1200.00")


@pytest.mark.parametrize("cantidad", [0, -1])
def test_item_cantidad_invalida(cantidad):
    with pytest.raises(InvalidOrderData):
        OrderItem("SKU001", cantidad, mxn("1"))


@pytest.mark.parametrize("sku", ["", "   "])
def test_item_sku_vacio(sku):
    with pytest.raises(InvalidOrderData):
        OrderItem(sku, 1, mxn("1"))


# ------------------------------------------------------- límites del pedido
def test_pedido_o001_inicia_draft(orders):
    o = orders["O001"]
    assert o.status == OrderStatus.DRAFT
    assert o.units == 4
    assert o.total.amount == Decimal("2100.00")


def test_cargador_trae_16_pedidos_en_draft(orders):
    assert len(orders) == 16
    assert all(o.status == OrderStatus.DRAFT for o in orders.values())


def test_veinte_unidades_exactas_permitidas(orders):
    assert orders["O008"].units == 20


def test_unidades_se_suman_no_se_cuentan_renglones():
    order = make_order(units=0)
    order.add_item(OrderItem("A", 10, mxn("1")))
    order.add_item(OrderItem("B", 10, mxn("1")))
    assert len(order.items) == 2 and order.units == 20


def test_21_unidades_rechazadas_sin_modificar_pedido(orders):
    o = orders["O009"]  # 19 unidades
    with pytest.raises(OrderItemLimitExceeded):
        o.add_item(OrderItem("SKU003", 2, mxn("120.00")))
    assert o.units == 19 and len(o.items) == 1


def test_agregar_21_unidades_de_golpe():
    with pytest.raises(OrderItemLimitExceeded):
        make_order(units=0).add_item(OrderItem("A", 21, mxn("1")))


def test_solo_moneda_mxn():
    with pytest.raises(InvalidOrderData):
        make_order(units=0).add_item(OrderItem("A", 1, Money(Decimal("1"), "USD")))


def test_no_se_agregan_items_fuera_de_draft():
    order = make_order()
    order.confirm()
    with pytest.raises(InvalidOrderTransition):
        order.add_item(OrderItem("B", 1, mxn("1")))
    assert order.units == 1


# ---------------------------------------------------- transiciones válidas
def test_ciclo_confirmar_enviar_entregar():
    order = make_order()
    order.confirm(); order.ship("GUIA-1"); order.deliver()
    assert order.status == OrderStatus.DELIVERED
    assert [e.name for e in order.events] == [
        "OrderConfirmed", "OrderShipped", "OrderDelivered"]


def test_ciclo_confirmar_enviar_devolver():
    order = make_order()
    order.confirm(); order.ship("GUIA-1"); order.return_order()
    assert order.status == OrderStatus.RETURNED
    assert order.events[-1].name == "OrderReturned"


def test_cancelar_desde_confirmed():
    order = make_order()
    order.confirm(); order.cancel("Cliente se arrepintió")
    assert order.status == OrderStatus.CANCELLED
    assert order.events[-1].name == "OrderCancelled"


def test_eventos_son_inmutables_y_referencian_pedido():
    order = make_order(oid="X9")
    order.confirm()
    evento = order.events[0]
    assert isinstance(evento, DomainEvent) and evento.order_id == "X9"
    assert evento.occurred_at.tzinfo is not None
    with pytest.raises(FrozenInstanceError):
        evento.name = "otro"


# -------------------------------------------------- transiciones inválidas
def test_confirmar_pedido_vacio(orders):
    o = orders["O007"]
    with pytest.raises(InvalidOrderData):
        o.confirm()
    assert o.status == OrderStatus.DRAFT and o.events == []


def test_confirmar_cliente_inactivo(orders):
    o = orders["O003"]
    with pytest.raises(InvalidOrderData):
        o.confirm()
    assert o.status == OrderStatus.DRAFT and o.events == []


def test_confirmacion_doble_no_agrega_evento(orders):
    o = orders["O013"]
    o.confirm()
    with pytest.raises(InvalidOrderTransition):
        o.confirm()
    assert o.status == OrderStatus.CONFIRMED
    assert [e.name for e in o.events] == ["OrderConfirmed"]


@pytest.mark.parametrize("guia", ["", "   ", None])
def test_envio_sin_guia(guia):
    order = make_order()
    order.confirm()
    with pytest.raises(InvalidOrderData):
        order.ship(guia)
    assert order.status == OrderStatus.CONFIRMED
    assert [e.name for e in order.events] == ["OrderConfirmed"]


def test_enviar_desde_draft():
    with pytest.raises(InvalidOrderTransition):
        make_order().ship("G1")


@pytest.mark.parametrize("motivo", ["", "  ", None])
def test_cancelar_sin_motivo(motivo):
    order = make_order()
    order.confirm()
    with pytest.raises(InvalidOrderData):
        order.cancel(motivo)
    assert order.status == OrderStatus.CONFIRMED


def test_cancelar_desde_shipped_rechazado(orders):
    o = orders["O014"]
    o.confirm(); o.ship("G1")
    with pytest.raises(InvalidOrderTransition):
        o.cancel("tarde")
    assert o.status == OrderStatus.SHIPPED
    assert [e.name for e in o.events] == ["OrderConfirmed", "OrderShipped"]


def test_cancelar_desde_draft_rechazado():
    with pytest.raises(InvalidOrderTransition):
        make_order().cancel("motivo")


@pytest.mark.parametrize("accion", ["deliver", "return_order"])
def test_entregar_o_devolver_requiere_shipped(accion):
    order = make_order()
    order.confirm()
    with pytest.raises(InvalidOrderTransition):
        getattr(order, accion)()
    assert order.status == OrderStatus.CONFIRMED


@pytest.mark.parametrize("final", ["deliver", "return_order"])
def test_estados_finales_no_admiten_mas_transiciones(final):
    order = make_order()
    order.confirm(); order.ship("G1"); getattr(order, final)()
    for accion in (order.confirm, order.deliver, order.return_order):
        with pytest.raises(InvalidOrderTransition):
            accion()
    with pytest.raises(InvalidOrderTransition):
        order.ship("G2")
    with pytest.raises(InvalidOrderTransition):
        order.cancel("x")
    assert len(order.events) == 3


# ----------------------------------------------------------- Specifications
def test_minimum_amount_es_estricto():
    spec = MinimumAmountSpec(Decimal("500"))
    assert not spec.is_satisfied_by(make_order(units=1, price="500.00"))
    assert spec.is_satisfied_by(make_order(units=1, price="500.01"))


def test_minimum_units_es_inclusivo():
    spec = MinimumUnitsSpec(4)
    assert not spec.is_satisfied_by(make_order(units=3))
    assert spec.is_satisfied_by(make_order(units=4))


def test_vip_y_promocion_specs():
    assert VIPCustomerSpec().is_satisfied_by(make_order(vip=True))
    assert not VIPCustomerSpec().is_satisfied_by(make_order(vip=False))
    assert ActivePromotionSpec().is_satisfied_by(make_order(promo=True))
    assert not ActivePromotionSpec().is_satisfied_by(make_order(promo=False))


def test_composicion_and_or_not():
    vip, promo = VIPCustomerSpec(), ActivePromotionSpec()
    o = make_order(vip=True, promo=False)
    assert (vip & ~promo).is_satisfied_by(o)
    assert not (vip & promo).is_satisfied_by(o)
    assert (vip | promo).is_satisfied_by(o)
    assert not (~vip | promo).is_satisfied_by(o)
    assert (~~vip).is_satisfied_by(o)


def test_specification_no_modifica_el_pedido(orders):
    o = orders["O001"]
    antes = (o.status, o.units, o.total, len(o.events))
    TEN_PERCENT_SPEC.is_satisfied_by(o)
    assert (o.status, o.units, o.total, len(o.events)) == antes


# ------------------------------------------------- reglas de descuento 10/5
@pytest.mark.parametrize("pedido, esperado", [
    ("O001", "0.10"),  # E01: VIP, 2100, 4 u., sin promo
    ("O002", "0"),     # E02: no VIP, total < 5000
    ("O004", "0"),
    ("O005", "0"),     # E04: promoción activa bloquea
    ("O006", "0.05"),  # E05: 18000 sin promo, no VIP
    ("O010", "0"),     # E09: total exactamente 500
    ("O011", "0"),     # E10: VIP con 3 unidades
])
def test_descuento_en_escenarios_del_paquete(orders, pedido, esperado):
    assert discount_rate(orders[pedido]) == Decimal(esperado)


def test_diez_por_ciento_cumple_todas_las_condiciones():
    assert TEN_PERCENT_SPEC.is_satisfied_by(make_order(units=4, price="125.01", vip=True))


@pytest.mark.parametrize("kwargs", [
    dict(units=4, price="125.00", vip=True),               # total = 500 exacto
    dict(units=3, price="200.00", vip=True),               # 3 unidades
    dict(units=4, price="200.00", vip=False),              # no VIP
    dict(units=4, price="200.00", vip=True, promo=True),   # con promoción
])
def test_diez_por_ciento_falla_si_falta_una_condicion(kwargs):
    assert not TEN_PERCENT_SPEC.is_satisfied_by(make_order(**kwargs))


def test_cinco_por_ciento_frontera_5000():
    assert not FIVE_PERCENT_SPEC.is_satisfied_by(make_order(units=1, price="5000.00"))
    assert FIVE_PERCENT_SPEC.is_satisfied_by(make_order(units=1, price="5000.01"))


def test_cinco_por_ciento_bloqueado_por_promocion():
    assert not FIVE_PERCENT_SPEC.is_satisfied_by(make_order(price="9000.00", promo=True))


def test_prioridad_diez_sobre_cinco():
    order = make_order(units=4, price="2000.00", vip=True)  # cumple ambas
    assert TEN_PERCENT_SPEC.is_satisfied_by(order)
    assert FIVE_PERCENT_SPEC.is_satisfied_by(order)
    assert discount_rate(order) == Decimal("0.10")


def test_vip_con_total_alto_pero_pocas_unidades_recibe_cinco():
    order = make_order(units=1, price="6000.00", vip=True)
    assert discount_rate(order) == Decimal("0.05")
