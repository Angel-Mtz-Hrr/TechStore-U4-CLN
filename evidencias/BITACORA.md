# Bitácora de ejecución E01–E15

Generada con `python generar_bitacora.py`. Cada caso parte de datos recién cargados con `load_fixture()`.

| Caso | Pedido | Estado inicial | Operación | Resultado real | Eventos emitidos | Estado final | Objetivo CSV | Explicación |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| E01 | O001 | DRAFT | evaluar_descuento | Descuento 10% | — (ninguno) | DRAFT | 10% (AND VIP + monto >500 + unidades >=4 + NOT promo) | VIP=True, total=2100.00, unidades=4, promo=False; regla10=True, regla5=False |
| E02 | O002 | DRAFT | evaluar_descuento | Descuento 0% | — (ninguno) | DRAFT | 0% (No VIP, total menor a 5000) | VIP=False, total=1050.00, unidades=2, promo=False; regla10=False, regla5=False |
| E03 | O003 | DRAFT | confirm() | confirm() RECHAZADO (InvalidOrderData, HTTP 422): El cliente está inactivo | — (ninguno) | DRAFT | rechazo (Cliente inactivo) | Estado final DRAFT; eventos: ninguno |
| E04 | O005 | DRAFT | evaluar_descuento | Descuento 0% | — (ninguno) | DRAFT | 0% (Promocion activa bloquea descuento) | VIP=True, total=2100.00, unidades=4, promo=True; regla10=False, regla5=False |
| E05 | O006 | DRAFT | evaluar_descuento | Descuento 5% | — (ninguno) | DRAFT | 5% (OR total >5000 y sin promocion) | VIP=False, total=18000.00, unidades=1, promo=False; regla10=False, regla5=True |
| E06 | O007 | DRAFT | confirm() | confirm() RECHAZADO (InvalidOrderData, HTTP 422): El pedido no tiene artículos | — (ninguno) | DRAFT | rechazo (Pedido sin articulos) | Estado final DRAFT; eventos: ninguno |
| E07 | O008 | DRAFT | confirm() | confirm() OK → CONFIRMED | OrderConfirmed | CONFIRMED | exito (20 unidades permitidas) | Estado final CONFIRMED; eventos: ['OrderConfirmed'] |
| E08 | O009 | DRAFT | add_item(SKU003 x2) con 19 unidades | add_item(SKU003 x2) RECHAZADO (OrderItemLimitExceeded, HTTP 422): Máximo 20 unidades por pedido | — (ninguno) | DRAFT | rechazo (21 unidades excede limite) | Unidades tras el intento: 19 (sin cambios) |
| E09 | O010 | DRAFT | evaluar_descuento | Descuento 0% | — (ninguno) | DRAFT | 0% (Umbral estricto >500) | VIP=False, total=500.00, unidades=2, promo=False; regla10=False, regla5=False |
| E10 | O011 | DRAFT | evaluar_descuento | Descuento 0% | — (ninguno) | DRAFT | 0% (Solo 3 unidades, requiere 4) | VIP=True, total=1500.00, unidades=3, promo=False; regla10=False, regla5=False |
| E11 | O012 | DRAFT | confirm() → ship('') | confirm() OK → CONFIRMED ; ship('') RECHAZADO (InvalidOrderData, HTTP 422): La guía de envío es obligatoria | OrderConfirmed | CONFIRMED | rechazo envio (La confirmacion es valida pero falta guia) | Estado final CONFIRMED; eventos: ['OrderConfirmed'] |
| E12 | O013 | DRAFT | confirm() #1 → confirm() #2 | confirm() #1 OK → CONFIRMED ; confirm() #2 RECHAZADO (InvalidOrderTransition, HTTP 409): No se puede confirmar un pedido en estado CONFIRMED; se requiere DRAFT | OrderConfirmed | CONFIRMED | rechazo segunda (No permite confirmar desde CONFIRMED) | Estado final CONFIRMED; eventos: ['OrderConfirmed'] |
| E13 | O014 | DRAFT | confirm() → ship('GUIA-014') → cancel('Ya no lo quiero') | confirm() OK → CONFIRMED ; ship('GUIA-014') OK → SHIPPED ; cancel('Ya no lo quiero') RECHAZADO (InvalidOrderTransition, HTTP 409): No se puede cancelar un pedido en estado SHIPPED; se requiere CONFIRMED | OrderConfirmed, OrderShipped | SHIPPED | rechazo cancelacion (No permite cancelar desde SHIPPED) | Estado final SHIPPED; eventos: ['OrderConfirmed', 'OrderShipped'] |
| E14 | O015 | DRAFT | confirm() → ship('GUIA-015') → return_order() | confirm() OK → CONFIRMED ; ship('GUIA-015') OK → SHIPPED ; return_order() OK → RETURNED | OrderConfirmed, OrderShipped, OrderReturned | RETURNED | exito (Termina en RETURNED) | Estado final RETURNED; eventos: ['OrderConfirmed', 'OrderShipped', 'OrderReturned'] |
| E15 | O016 | DRAFT | confirm() → ship('GUIA-016') → deliver() | confirm() OK → CONFIRMED ; ship('GUIA-016') OK → SHIPPED ; deliver() OK → DELIVERED | OrderConfirmed, OrderShipped, OrderDelivered | DELIVERED | exito (Termina en DELIVERED) | Estado final DELIVERED; eventos: ['OrderConfirmed', 'OrderShipped', 'OrderDelivered'] |
