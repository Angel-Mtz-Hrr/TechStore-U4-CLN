"""Patrón Specification y reglas de descuento de TechStore (Parte 2).

Una Specification responde True/False sobre un pedido sin modificarlo.
Se combinan con & (AND), | (OR) y ~ (NOT).
"""
from decimal import Decimal

from app.domain import Order


class Specification:
    def is_satisfied_by(self, order: Order) -> bool:
        raise NotImplementedError

    def __and__(self, other: "Specification") -> "Specification":
        return AndSpec(self, other)

    def __or__(self, other: "Specification") -> "Specification":
        return OrSpec(self, other)

    def __invert__(self) -> "Specification":
        return NotSpec(self)


class AndSpec(Specification):
    def __init__(self, left: Specification, right: Specification):
        self.left, self.right = left, right

    def is_satisfied_by(self, order: Order) -> bool:
        return (self.left.is_satisfied_by(order)
                and self.right.is_satisfied_by(order))


class OrSpec(Specification):
    def __init__(self, left: Specification, right: Specification):
        self.left, self.right = left, right

    def is_satisfied_by(self, order: Order) -> bool:
        return (self.left.is_satisfied_by(order)
                or self.right.is_satisfied_by(order))


class NotSpec(Specification):
    def __init__(self, spec: Specification):
        self.spec = spec

    def is_satisfied_by(self, order: Order) -> bool:
        return not self.spec.is_satisfied_by(order)


# --------------------------------------------------------------------------
# Especificaciones concretas
# --------------------------------------------------------------------------
class MinimumAmountSpec(Specification):
    """Total ESTRICTAMENTE mayor al umbral (> y no >=)."""

    def __init__(self, amount: Decimal):
        self.amount = amount

    def is_satisfied_by(self, order: Order) -> bool:
        return order.total.amount > self.amount


class VIPCustomerSpec(Specification):
    def is_satisfied_by(self, order: Order) -> bool:
        return order.customer.is_vip is True


class MinimumUnitsSpec(Specification):
    """Al menos min_units unidades (>=)."""

    def __init__(self, min_units: int):
        self.min_units = min_units

    def is_satisfied_by(self, order: Order) -> bool:
        return order.units >= self.min_units


class ActivePromotionSpec(Specification):
    def is_satisfied_by(self, order: Order) -> bool:
        return order.has_promotion is True


# --------------------------------------------------------------------------
# Reglas de descuento compuestas
# --------------------------------------------------------------------------
TEN_PERCENT_SPEC = (
    MinimumAmountSpec(Decimal("500"))
    & VIPCustomerSpec()
    & MinimumUnitsSpec(4)
    & ~ActivePromotionSpec()
)

FIVE_PERCENT_SPEC = MinimumAmountSpec(Decimal("5000")) & ~ActivePromotionSpec()

# Cualquiera de las dos reglas otorga algún descuento.
ANY_DISCOUNT_SPEC = TEN_PERCENT_SPEC | FIVE_PERCENT_SPEC


def discount_rate(order: Order) -> Decimal:
    """Tasa de descuento aplicable. Si ambas reglas aplican, gana la de 10 %."""
    if TEN_PERCENT_SPEC.is_satisfied_by(order):
        return Decimal("0.10")
    if FIVE_PERCENT_SPEC.is_satisfied_by(order):
        return Decimal("0.05")
    return Decimal("0")
