"""Ejecuta los 15 escenarios de datos/escenarios.csv y genera BITACORA.md.

Cada caso usa objetos recién cargados con load_fixture(), por lo que los
casos son independientes. Los resultados se OBSERVAN al ejecutar el dominio;
no están escritos a mano.

Uso:  python generar_bitacora.py
"""
from decimal import Decimal

from app.domain import (
    DomainException, Money, OrderItem, InvalidOrderData,
    InvalidOrderTransition, OrderItemLimitExceeded,
)
from app.specifications import (
    FIVE_PERCENT_SPEC, TEN_PERCENT_SPEC, discount_rate,
)
from cargar_csv import load_fixture, rows

HTTP = {InvalidOrderTransition: 409, InvalidOrderData: 422,
        OrderItemLimitExceeded: 422}


def evaluar_descuento(o):
    tasa = discount_rate(o)
    detalle = (f"VIP={o.customer.is_vip}, total={o.total.amount}, "
               f"unidades={o.units}, promo={o.has_promotion}; "
               f"regla10={TEN_PERCENT_SPEC.is_satisfied_by(o)}, "
               f"regla5={FIVE_PERCENT_SPEC.is_satisfied_by(o)}")
    return f"Descuento {int(tasa * 100)}%", detalle


def paso(o, nombre, fn):
    """Ejecuta un paso; devuelve (ok, texto)."""
    try:
        fn()
        return True, f"{nombre} OK → {o.status.value}"
    except DomainException as exc:
        return False, (f"{nombre} RECHAZADO ({type(exc).__name__}, "
                       f"HTTP {HTTP[type(exc)]}): {exc}")


def ejecutar(caso, o):
    """Devuelve (operación, resultado, explicación)."""
    cid = caso["caso_id"]
    if caso["accion"] == "evaluar_descuento":
        res, det = evaluar_descuento(o)
        return "evaluar_descuento", res, det

    if cid == "E08":
        item = OrderItem("SKU003", 2, Money(Decimal("120.00")))
        antes = o.units
        ok, txt = paso(o, "add_item(SKU003 x2)", lambda: o.add_item(item))
        return (f"add_item(SKU003 x2) con {antes} unidades",
                txt, f"Unidades tras el intento: {o.units} (sin cambios)")

    secuencias = {
        "E03": [("confirm()", o.confirm)],
        "E06": [("confirm()", o.confirm)],
        "E07": [("confirm()", o.confirm)],
        "E11": [("confirm()", o.confirm), ("ship('')", lambda: o.ship(""))],
        "E12": [("confirm() #1", o.confirm), ("confirm() #2", o.confirm)],
        "E13": [("confirm()", o.confirm), ("ship('GUIA-014')", lambda: o.ship("GUIA-014")),
                ("cancel('Ya no lo quiero')", lambda: o.cancel("Ya no lo quiero"))],
        "E14": [("confirm()", o.confirm), ("ship('GUIA-015')", lambda: o.ship("GUIA-015")),
                ("return_order()", o.return_order)],
        "E15": [("confirm()", o.confirm), ("ship('GUIA-016')", lambda: o.ship("GUIA-016")),
                ("deliver()", o.deliver)],
    }
    pasos, textos = secuencias[cid], []
    for nombre, fn in pasos:
        ok, txt = paso(o, nombre, fn)
        textos.append(txt)
        if not ok:
            break
    return (" → ".join(n for n, _ in pasos), " ; ".join(textos),
            f"Estado final {o.status.value}; eventos: "
            f"{[e.name for e in o.events] or 'ninguno'}")


def main():
    casos = rows("escenarios.csv")
    filas = []
    for caso in casos:
        o = load_fixture()[caso["pedido_id"]]  # datos limpios por caso
        inicial = o.status.value
        operacion, resultado, explicacion = ejecutar(caso, o)
        eventos = ", ".join(e.name for e in o.events) or "— (ninguno)"
        filas.append((caso, inicial, operacion, resultado, eventos,
                      explicacion, o.status.value))

    md = ["# Bitácora de ejecución E01–E15", "",
          "Generada con `python generar_bitacora.py`. Cada caso parte de "
          "datos recién cargados con `load_fixture()`.", "",
          "| Caso | Pedido | Estado inicial | Operación | Resultado real | "
          "Eventos emitidos | Estado final | Objetivo CSV | Explicación |",
          "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for caso, ini, op, res, ev, exp, fin in filas:
        esc = lambda s: str(s).replace("|", "\\|")
        md.append(f"| {caso['caso_id']} | {caso['pedido_id']} | {ini} | "
                  f"{esc(op)} | {esc(res)} | {esc(ev)} | {fin} | "
                  f"{caso['objetivo']} ({esc(caso['pista'])}) | {esc(exp)} |")
    with open("BITACORA.md", "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")
    for caso, ini, op, res, ev, exp, fin in filas:
        print(f"{caso['caso_id']} {caso['pedido_id']} | {res} | final={fin} | eventos={ev}")


if __name__ == "__main__":
    main()
