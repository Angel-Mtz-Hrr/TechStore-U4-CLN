# TechStore U4 — Núcleo de negocio (DDD + FastAPI)

Actividad 4 · Componentes de Lógica de Negocio · FIME-UANL.

Sistema de gestión de pedidos **en memoria** (sin base de datos): los datos se cargan
desde CSV al iniciar y los cambios se pierden al cerrar el programa. El proyecto aplica
Domain-Driven Design (Value Objects y Aggregate Root), el patrón Specification para las
reglas de descuento, una máquina de estados con Domain Events y una API REST con FastAPI,
todo verificado con pruebas automáticas.

**Equipo:** M6 · Grupo 003 · Equipo 11

## Estructura

```text
TechStore-U4-CLN/
├── .gitignore              # Excluye .venv, __pycache__, .pytest_cache, etc.
├── README.md               # Este documento
├── README.txt              # README original del paquete del alumno
├── requirements.txt        # Dependencias: fastapi, uvicorn, pytest, httpx
├── cargar_csv.py           # Carga los CSV en objetos Order
├── generar_bitacora.py     # Ejecuta E01–E15 y genera BITACORA.md
├── app/
│   ├── __init__.py
│   ├── domain.py           # Money, OrderItem, Customer, Order (Aggregate Root), eventos, excepciones
│   ├── specifications.py   # Patrón Specification + reglas de descuento 10 % / 5 %
│   └── api.py              # API REST con FastAPI
├── datos/                  # CSV: clientes, productos, pedidos, detalle_pedidos, escenarios
├── tests/
│   ├── __init__.py
│   ├── test_domain.py      # Dominio y Specifications (63 pruebas)
│   └── test_api.py         # Endpoints (29 pruebas: 200, 404, 409, 422)
└── evidencias/
    ├── BITACORA.md                                                   # Resultado de los 15 escenarios
    ├── REFLEXION.md                                                  # Tres errores encontrados y aprendizajes
    ├── Diagrama de estados y Explicacion de los Domain Events.md     # Diagrama Mermaid y eventos
    └── Captura *.png                                                 # Cinco capturas de evidencia
```

## Instalación

Requiere Python 3.11 o superior.

```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# Windows CMD:        .venv\Scripts\activate.bat
# macOS / Linux:      source .venv/bin/activate
python -m pip install -r requirements.txt
```

El entorno virtual `.venv` es local y no se sube al repositorio.

## Ejecución

Todos los comandos se ejecutan desde la raíz del proyecto.

| Acción                | Comando                        |
| --------------------- | ------------------------------ |
| Cargar los 16 pedidos | `python cargar_csv.py`         |
| Pruebas (92)          | `python -m pytest -q`          |
| Bitácora E01–E15      | `python generar_bitacora.py`   |
| API                   | `uvicorn app.api:app --reload` |

La bitácora se genera como `BITACORA.md` en la raíz; la versión entregada se conserva en
`evidencias/BITACORA.md`.

Con la API arriba: Swagger en <http://127.0.0.1:8000/docs> y contrato en
<http://127.0.0.1:8000/openapi.json>. Para repetir un caso de prueba desde cero,
reinicia el servidor (los fixtures se recargan al iniciar).

## Reglas de negocio

- **Money:** `Decimal`, inmutable, sin importes negativos ni no finitos, sin mezclar monedas.
- **OrderItem:** SKU no vacío y cantidad > 0; `subtotal` se calcula.
- **Límite:** máximo **20 unidades** por pedido (suma de unidades, no de renglones). Solo MXN.
- **Artículos:** solo se agregan en estado `DRAFT`.
- **Descuento 10 %:** cliente VIP **y** total **> 500** **y** ≥ 4 unidades **y** sin promoción.
- **Descuento 5 %:** total **> 5000** **y** sin promoción.
- **Prioridad:** si se cumplen ambas, aplica 10 %.
- **Inventario:** `existencia` es solo información de catálogo; no se descuenta.

## Máquina de estados

```text
DRAFT --confirm--> CONFIRMED --ship--> SHIPPED --deliver--> DELIVERED
                       |                  |
                    cancel             return
                       v                  v
                   CANCELLED           RETURNED
```

Toda operación valida primero, cambia el estado después y registra el evento al final.
Una operación rechazada no cambia el estado ni agrega eventos. El diagrama en Mermaid y la
explicación de los eventos están en
[evidencias/Diagrama de estados y Explicacion de los Domain Events.md](evidencias/Diagrama%20de%20estados%20y%20Explicacion%20de%20los%20Domain%20Events.md).

| Método           | Requisitos                          | Evento           |
| ---------------- | ----------------------------------- | ---------------- |
| `confirm()`      | DRAFT, cliente activo, ≥ 1 artículo | `OrderConfirmed` |
| `ship(guía)`     | CONFIRMED, guía no vacía            | `OrderShipped`   |
| `cancel(motivo)` | CONFIRMED, motivo no vacío          | `OrderCancelled` |
| `deliver()`      | SHIPPED                             | `OrderDelivered` |
| `return_order()` | SHIPPED                             | `OrderReturned`  |

## Endpoints

| Método | Ruta                         | Cuerpo JSON                     | Respuestas         |
| ------ | ---------------------------- | ------------------------------- | ------------------ |
| GET    | `/orders/{order_id}`         | —                               | 200, 404           |
| POST   | `/orders/{order_id}/confirm` | —                               | 200, 404, 409, 422 |
| POST   | `/orders/{order_id}/ship`    | `{"tracking_number": "GUIA-1"}` | 200, 404, 409, 422 |
| POST   | `/orders/{order_id}/cancel`  | `{"reason": "motivo"}`          | 200, 404, 409, 422 |
| POST   | `/orders/{order_id}/deliver` | —                               | 200, 404, 409      |
| POST   | `/orders/{order_id}/return`  | —                               | 200, 404, 409      |

Los cuatro primeros son los endpoints obligatorios de la práctica; `deliver` y `return` son
una ampliación que permite recorrer todo el ciclo de vida desde la API (ambos requieren
estado `SHIPPED`).

| Código | Cuándo                                                                  |
| ------ | ----------------------------------------------------------------------- |
| 404    | El pedido no existe                                                     |
| 409    | `InvalidOrderTransition`: operación no permitida desde el estado actual |
| 422    | `InvalidOrderData` / `OrderItemLimitExceeded`, o cuerpo mal formado     |

Ejemplo (ciclo hasta la entrega):

```bash
curl -X POST http://127.0.0.1:8000/orders/O016/confirm
curl -X POST http://127.0.0.1:8000/orders/O016/ship \
     -H "Content-Type: application/json" -d '{"tracking_number": "GUIA-123"}'
curl -X POST http://127.0.0.1:8000/orders/O016/deliver
```

## Pruebas

```bash
python -m pytest -q
```

Resultado esperado: **92 pruebas aprobadas** (63 de dominio y Specifications, 29 de la API).
Pytest puede mostrar una advertencia de `httpx` proveniente de la librería del cliente de
pruebas de FastAPI; no afecta los resultados. Las pruebas de la API recargan los datos antes
de cada prueba, por lo que son independientes entre sí.

## Evidencias

Las evidencias se encuentran en la carpeta [`evidencias/`](evidencias/).

### Carga exitosa de los 16 pedidos

![Carga exitosa de los 16 pedidos](evidencias/Captura%20carga%20exitosa%20de%20los%2016%20pedidos.png)

### Bitácora resuelta de los 15 escenarios

![Bitácora resuelta de los 15 escenarios](evidencias/Captura%20bitacora%20resuelta%20de%20los%2015%20escenarios.png)

El detalle completo está en [evidencias/BITACORA.md](evidencias/BITACORA.md).

### Pruebas pytest y resultados

![Pruebas pytest y resultados](evidencias/Captura%20pruebas%20pytest%20y%20resultados.png)

### Swagger `/docs`: operación exitosa

![Swagger operación exitosa](evidencias/Captura%20Swagger%20docs%20operacion%20exitosa.png)

### Swagger `/docs`: operación rechazada

![Swagger operación rechazada](evidencias/Captura%20Swagger%20docs%20operacion%20rechazada.png)

## Documentación complementaria

| Documento                                                                                                                                                    | Contenido                                                        |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------- |
| [evidencias/BITACORA.md](evidencias/BITACORA.md)                                                                                                             | Ejecución de los escenarios E01–E15 con resultado real y eventos |
| [evidencias/REFLEXION.md](evidencias/REFLEXION.md)                                                                                                           | Tres errores encontrados, cómo se solucionaron y qué se aprendió |
| [evidencias/Diagrama de estados y Explicacion de los Domain Events.md](evidencias/Diagrama%20de%20estados%20y%20Explicacion%20de%20los%20Domain%20Events.md) | Diagrama de estados y descripción de los Domain Events           |
