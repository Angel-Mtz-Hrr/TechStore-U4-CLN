# Reflexión: tres errores encontrados y aprendizajes

## Error 1: tipos incorrectos que producían errores genéricos

**Qué ocurrió.** La base sugerida para `Money` llama a `self.amount.is_finite()` directamente. Si alguien crea `Money(600.0)` con un `float`, el programa falla con un `AttributeError` y no con una excepción de dominio; algo parecido pasa con `OrderItem` si el SKU no es texto.

**Solución.** Se agregaron validaciones de tipo (`isinstance`) en `Money` y `OrderItem` para que cualquier dato incorrecto lance `InvalidOrderData`, con pruebas específicas (`test_money_rechaza_float`, entre otras).

## Error 2: orden de las validaciones y códigos HTTP

**Qué ocurrió.** Al confirmar un pedido había que decidir qué se valida primero. Si se revisaban los datos antes que el estado, una segunda confirmación podía dar un error de datos (422) en lugar de un conflicto de estado (409), y el mismo caso respondería distinto según el pedido.

**Solución.** Todos los métodos validan **primero el estado** (`InvalidOrderTransition`, 409) y **después los datos** (`InvalidOrderData`, 422). Así cada situación produce siempre el mismo código y los escenarios E11 a E13 se comportan de forma predecible.

## Error 3: estado en memoria que contamina pruebas y capturas

**Qué ocurrió.** Como los pedidos viven en memoria, un pedido confirmado en una prueba o en Swagger seguía confirmado en la siguiente, lo que daba resultados distintos a los esperados al repetir un caso. Además, Swagger reutiliza el valor de `order_id` entre operaciones y propone `"string"` como cuerpo de ejemplo en `ship` y `cancel`, lo que puede producir un envío «exitoso» con la guía `string` si no se cambia.

**Solución.** Las pruebas de la API usan una fixture que recarga los datos antes de cada prueba, la bitácora carga objetos nuevos por escenario y, en Swagger, se reinicia el servidor para repetir casos desde cero y se escriben valores explícitos en el cuerpo de las peticiones.

## Qué aprendimos

- Poner las reglas de negocio en el dominio y no en los endpoints permitió probarlas sin levantar un servidor y reutilizarlas desde cualquier interfaz.
- Los Value Objects inmutables y las validaciones tempranas evitan que existan objetos inválidos en cualquier momento.
- El patrón Specification vuelve legibles y modificables las reglas de descuento, y los valores frontera (500 contra 500.01, 3 contra 4 unidades) son donde suelen esconderse los errores.
- Validar primero y registrar el evento al final mantiene consistentes el estado y la historia del pedido.
- Una bitácora ejecutable y pruebas automáticas ofrecen evidencia verificable en lugar de afirmaciones.
