"""Núcleo de dominio de TechStore (Actividad 4, Parte 1).

Contiene excepciones de dominio, Value Objects (Money, OrderItem),
entidades (Customer), eventos (DomainEvent) y el Aggregate Root Order.
No depende de FastAPI ni de ningún detalle de infraestructura.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum

MAX_UNITS_PER_ORDER = 20
DEFAULT_CURRENCY = "MXN"


# --------------------------------------------------------------------------
# Excepciones de dominio
# --------------------------------------------------------------------------
class DomainException(Exception):
    """Base de todas las violaciones de reglas de negocio."""


class InvalidOrderData(DomainException):
    """Datos inválidos (montos, cantidades, SKU, guía, motivo, etc.)."""


class InvalidOrderTransition(DomainException):
    """Operación no permitida desde el estado actual del pedido."""


class OrderItemLimitExceeded(DomainException):
    """Se excede el máximo de unidades permitido por pedido."""


# --------------------------------------------------------------------------
# Value Objects
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class Money:
    amount: Decimal
    currency: str = DEFAULT_CURRENCY

    def __post_init__(self):
        # bool e int/float no son Decimal: evita errores de precisión con float.
        if not isinstance(self.amount, Decimal):
            raise InvalidOrderData("El monto debe ser Decimal")
        if not self.amount.is_finite() or self.amount < 0:
            raise InvalidOrderData("Monto inválido")
        if not isinstance(self.currency, str) or not self.currency.strip():
            raise InvalidOrderData("Moneda inválida")

    def add(self, other: "Money") -> "Money":
        if not isinstance(other, Money):
            raise InvalidOrderData("Solo se puede sumar otro Money")
        if self.currency != other.currency:
            raise InvalidOrderData("Monedas distintas")
        return Money(self.amount + other.amount, self.currency)


@dataclass(frozen=True)
class OrderItem:
    sku: str
    quantity: int
    unit_price: Money

    def __post_init__(self):
        if not isinstance(self.sku, str) or not self.sku.strip():
            raise InvalidOrderData("SKU vacío o inválido")
        if (not isinstance(self.quantity, int) or isinstance(self.quantity, bool)
                or self.quantity <= 0):
            raise InvalidOrderData("La cantidad debe ser un entero mayor a 0")
        if not isinstance(self.unit_price, Money):
            raise InvalidOrderData("El precio unitario debe ser Money")

    @property
    def subtotal(self) -> Money:
        return Money(self.unit_price.amount * self.quantity,
                     self.unit_price.currency)


# --------------------------------------------------------------------------
# Entidades, enumeraciones y eventos
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class Customer:
    id: str
    is_vip: bool = False
    active: bool = True


class OrderStatus(str, Enum):
    DRAFT = "DRAFT"
    CONFIRMED = "CONFIRMED"
    SHIPPED = "SHIPPED"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"
    RETURNED = "RETURNED"


@dataclass(frozen=True)
class DomainEvent:
    name: str
    order_id: str
    occurred_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


# --------------------------------------------------------------------------
# Aggregate Root
# --------------------------------------------------------------------------
@dataclass
class Order:
    customer: Customer
    id: str
    has_promotion: bool = False
    status: OrderStatus = OrderStatus.DRAFT
    items: list[OrderItem] = field(default_factory=list)
    events: list[DomainEvent] = field(default_factory=list)

    # ---- propiedades calculadas -------------------------------------------
    @property
    def units(self) -> int:
        """Suma de unidades (no cuenta renglones)."""
        return sum(item.quantity for item in self.items)

    @property
    def total(self) -> Money:
        amount = sum((item.subtotal.amount for item in self.items),
                     Decimal("0"))
        return Money(amount)

    # ---- helpers privados -------------------------------------------------
    def _require_status(self, expected: OrderStatus, action: str) -> None:
        if self.status != expected:
            raise InvalidOrderTransition(
                f"No se puede {action} un pedido en estado "
                f"{self.status.value}; se requiere {expected.value}"
            )

    def _record(self, event_name: str) -> None:
        self.events.append(DomainEvent(event_name, self.id))

    @staticmethod
    def _require_text(value, message: str) -> None:
        if not isinstance(value, str) or not value.strip():
            raise InvalidOrderData(message)

    # ---- comandos ---------------------------------------------------------
    def add_item(self, item: OrderItem) -> None:
        if self.status != OrderStatus.DRAFT:
            raise InvalidOrderTransition("Solo DRAFT admite artículos")
        if self.units + item.quantity > MAX_UNITS_PER_ORDER:
            raise OrderItemLimitExceeded(
                f"Máximo {MAX_UNITS_PER_ORDER} unidades por pedido"
            )
        if item.unit_price.currency != DEFAULT_CURRENCY:
            raise InvalidOrderData("Solo MXN")
        self.items.append(item)

    def confirm(self) -> None:
        self._require_status(OrderStatus.DRAFT, "confirmar")
        if not self.items:
            raise InvalidOrderData("El pedido no tiene artículos")
        if not self.customer.active:
            raise InvalidOrderData("El cliente está inactivo")
        self.status = OrderStatus.CONFIRMED
        self._record("OrderConfirmed")

    def ship(self, tracking_number: str) -> None:
        self._require_status(OrderStatus.CONFIRMED, "enviar")
        self._require_text(tracking_number, "La guía de envío es obligatoria")
        self.status = OrderStatus.SHIPPED
        self._record("OrderShipped")

    def cancel(self, reason: str) -> None:
        self._require_status(OrderStatus.CONFIRMED, "cancelar")
        self._require_text(reason, "El motivo de cancelación es obligatorio")
        self.status = OrderStatus.CANCELLED
        self._record("OrderCancelled")

    def deliver(self) -> None:
        self._require_status(OrderStatus.SHIPPED, "entregar")
        self.status = OrderStatus.DELIVERED
        self._record("OrderDelivered")

    def return_order(self) -> None:
        self._require_status(OrderStatus.SHIPPED, "devolver")
        self.status = OrderStatus.RETURNED
        self._record("OrderReturned")
