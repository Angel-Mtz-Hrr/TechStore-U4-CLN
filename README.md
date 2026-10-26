# TechStore U4 — Núcleo de negocio (DDD + FastAPI)

Actividad 4 · Componentes de Lógica de Negocio · FIME-UANL.
Sistema de gestión de pedidos **en memoria** (sin base de datos): los datos se cargan
desde CSV al iniciar y los cambios se pierden al cerrar el programa.

## Estructura

```text
techstore-u4/
├── datos/                  # CSV: clientes, productos, pedidos, detalle_pedidos, escenarios
├── app/
│   ├── domain.py           # Money, OrderItem, Customer, Order (Aggregate Root), eventos, excepciones
│   ├── specifications.py   # Patrón Specification + reglas de descuento 10 % / 5 %
│   └── api.py              # API REST con FastAPI
├── tests/
│   ├── test_domain.py      # Dominio y Specifications
│   └── test_api.py         # Endpoints (200, 404, 409, 422)
├── cargar_csv.py           # Carga los CSV en objetos Order
├── generar_bitacora.py     # Ejecuta E01–E15 y genera BITACORA.md
├── BITACORA.md             # Resultado de los 15 escenarios
└── REPORTE.md              # Diagrama de estados, eventos y preguntas del reporte
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

## Ejecución

| Acción | Comando |
| --- | --- |
| Cargar los 16 pedidos | `python cargar_csv.py` |
| Pruebas | `python -m pytest -q` |
| Bitácora E01–E15 | `python generar_bitacora.py` |
| API | `uvicorn app.api:app --reload` |

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
Una operación rechazada no cambia el estado ni agrega eventos.

| Método | Requisitos | Evento |
| --- | --- | --- |
| `confirm()` | DRAFT, cliente activo, ≥ 1 artículo | `OrderConfirmed` |
| `ship(guía)` | CONFIRMED, guía no vacía | `OrderShipped` |
| `cancel(motivo)` | CONFIRMED, motivo no vacío | `OrderCancelled` |
| `deliver()` | SHIPPED | `OrderDelivered` |
| `return_order()` | SHIPPED | `OrderReturned` |

## Endpoints

| Método | Ruta | Cuerpo JSON | Respuestas |
| --- | --- | --- | --- |
| GET | `/orders/{order_id}` | — | 200, 404 |
| POST | `/orders/{order_id}/confirm` | — | 200, 404, 409, 422 |
| POST | `/orders/{order_id}/ship` | `{"tracking_number": "GUIA-1"}` | 200, 404, 409, 422 |
| POST | `/orders/{order_id}/cancel` | `{"reason": "motivo"}` | 200, 404, 409, 422 |

| Código | Cuándo |
| --- | --- |
| 404 | El pedido no existe |
| 409 | `InvalidOrderTransition`: operación no permitida desde el estado actual |
| 422 | `InvalidOrderData` / `OrderItemLimitExceeded`, o cuerpo mal formado |

Ejemplo:

```bash
curl -X POST http://127.0.0.1:8000/orders/O013/confirm
curl -X POST http://127.0.0.1:8000/orders/O013/ship \
     -H "Content-Type: application/json" -d '{"tracking_number": "GUIA-123"}'
```

## Evidencias a adjuntar en el repositorio

Capturas de: `python cargar_csv.py` (16 pedidos), `python -m pytest -q`, y Swagger `/docs`
con una operación exitosa y una rechazada (404, 409 o 422).
