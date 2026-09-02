# PickFlow - Warehouse Pick Management System

## Propósito
Sistema de gestión de almacén para fabricantes de muebles. Permite recibir inventario en ubicaciones de overflow, seleccionar partes para órdenes de trabajo, rastrear entregas, registrar pérdidas/daños y supervisar el flujo operacional.

## Stack
- Backend: Python/Flask + PostgreSQL
- Frontend: HTML5/CSS3 + JavaScript (vanilla)
- Autenticación: Flask sessions con decorators @auth
- Base de datos: PostgreSQL con SQLAlchemy ORM
- Servidor: Linux (Fedora), local: Debian Server en MacBook Air
- GitHub: https://github.com/sarwin-dev/pickflow

## Arquitectura de Almacén

```
Warehouse Layout:
├─ Aisles (filas): 1 → N configurable
│  └─ Bays (columnas): 1 → N configurable
│     └─ Shelves (niveles): 
│        ├─ Active shelves: 1 → config.active_shelves (picking)
│        └─ Overflow shelves: config.active_shelves+1 → config.total_shelves
│           └─ Locations (sub-posiciones): 1 → config.total_locations (opcional)
```

**Concepto clave:** Una part tiene:
- `active_aisle`, `active_bay`, `active_shelf`, `active_location` - ubicación de picking
- En overflow puede haber N cajas de la misma parte en diferentes ubicaciones
- Cada ubicación (Aisle-Bay-Shelf-Location) solo puede tener UNA caja, sin excepciones

---

## Getting Started Wizard

Modal de bienvenida que aparece cuando la app está vacía (sin WarehouseConfig).

**Flujo:**
1. **Step 1:** Datos del almacén (Company Name opcional, Aisles/Bays/Shelves/Active Shelves/Locations obligatorio)
2. **Step 2:** Checklist de tareas iniciales (crear cabinet types, cargar partes, etc.)
3. Guarda WarehouseConfig.name para mostrar en PDFs y headers

**Endpoint:**
- `POST /admin/setup-wizard` - guardar configuración inicial

---

## Módulos Completados

### 1. **Admin** (`routes/admin.py`)
Configuración del almacén y gestión de datos maestros.

**Secciones:**
- Usuarios y roles (admin, supervisor, warehouse, order_entry, picker)
- Warehouse Configuration (aisles, bays, shelves activos/overflow, locations, nombre empresa)
- Cabinet Types (tipos de muebles: base, wall, tall, etc.)
- Colors (colores disponibles para órdenes)
- Parts (partes del inventario con ubicación activa)
- Demo Tools (cargar/limpiar datos de prueba, simular órdenes)

**Endpoints principales:**
- `GET /admin/` - dashboard de configuración
- `POST /admin/setup-wizard` - guardar wizard inicial
- `POST /admin/demo/reset` - cargar demo_seed.json
- `POST /admin/demo/generate-order` - crear orden de trabajo aleatoria
- `POST /admin/demo/simulate-orders` - generar órdenes completadas con prefijo SIM-
- `POST /admin/demo/clear-simulated-orders` - limpiar órdenes simuladas
- `POST /admin/demo/clear-all` - borrar todos los datos

---

### 2. **Receiving** (`routes/receiving.py`, `templates/receiving/index.html`)
Registro de cajas entrantes en ubicaciones de overflow.

**Flujo:**
1. User selecciona Part (autocomplete que busca en partes existentes)
2. Ingresa cantidad
3. Elige tipo de recepción:
   - **Direct to Active:** suma a stock en active location de la parte
   - **To Overflow Location:** usuario especifica Aisle/Bay/Shelf/Location

**Validaciones criticas:**
- Part debe existir - autocomplete only, no se aceptan nombres nuevos
- Location puede ser `None` (sin sub-posición) o número
- **Una location solo puede tener UNA caja**, sin excepciones
- Shelf debe estar en rango overflow: >= config.active_shelves + 1
- Ubicación duplicada previene cajas múltiples en mismo lugar

**Endpoints:**
- `GET /receiving/` - formulario de recepción + historial reciente
- `POST /receiving/receive` - registrar caja
- `POST /receiving/pulldown/<record_id>` - bajar caja de overflow a active
- `GET /receiving/free-locations` - JSON de ubicaciones libres
- `POST /receiving/demo-fill` - llenar overflow con partes aleatorias
- `POST /receiving/demo-clear` - borrar todos registros de overflow

---

### 3. **Inventory** (`routes/inventory.py`, `templates/inventory/`)
Visualización del stock actual por parte, con filtros y búsqueda.

**Optimización reciente:**
- 3 queries globales en el loop de `index()` en lugar de N queries por parte
- Registros con quantity ≤ 0 se filtran y ocultan
- Registros vacíos se eliminan automáticamente cuando son consumidos por simulación

**Vistas:**
- Listado de partes activas y overflow
- Búsqueda por nombre con normalización (toe33 → Toe 33)
- Filtros: solo bajo stock, en shopping list
- Notificación badge rojo en botón Inventory si hay partes agotadas

**Features:**
- Badge rojo con número en esquina superior derecha del botón Inventory
- Muestra cantidad de partes completamente agotadas (quantity = 0)
- Shopping List para partes a reabastecer
- PDF de Reorder List con nombre de empresa en header

**Endpoints:**
- `GET /inventory/` - listado con filtros y búsqueda
- `GET /inventory/search-parts` - búsqueda en tiempo real (JSON)
- `GET /inventory/shopping/pdf` - exportar lista de compra como PDF

---

### 4. **Order Entry** (`routes/orders.py`, `templates/orders/`)
Crear órdenes de trabajo con gabinetes y colores especificados.

**Flujo:**
1. Usuario ingresa Job Name (ej: "Project-2025-Alpha")
2. Selecciona Color
3. Añade gabinetes dinámicamente (Base Cabinet, Wall Cabinet, etc.)
4. Sistema valida cantidad de partes disponibles
5. Crea orden y genera list de picking

**Órdenes simuladas:**
- Órdenes generadas por Demo Tools tienen prefijo SIM- (ej: SIM-20260901-12345)
- Aparecen al final del listado, ordenadas por número
- Tienen is_simulated=False (se usan prefijo SIM- en lugar de flag)

**Estructura Orden:**
```
Work Order
├─ Job Name (string)
├─ Order Number (único, SIM- para simuladas)
├─ Color (FK → Color)
├─ Cabinets (list dinamico)
│  └─ Cabinet Type → Parts requeridas
├─ Status (pending/in_progress/completed)
└─ Timestamps
```

**Endpoints:**
- `GET /orders/` - crear orden
- `POST /orders/create` - guardar nueva orden
- `GET /orders/<order_id>` - ver detalles orden

---

### 5. **Pick** (`routes/pick.py`, `templates/pick/`)
Seleccionar partes para órdenes confirmadas.

**Tristate por parte:**
- ✓ Picked (seleccionada)
- ✗ Missing (no hay stock)
- ⏳ Pending (sin marcar)

**Features:**
- Barra de progreso: cuántas partes seleccionadas vs total
- Búsqueda/filtro de órdenes
- Botón "Mark as Completed" cuando todas partes están picked
- Botón "Complete" para admin/supervisor: genera PickItems si no existen y marca todas como picked
- PDF de Case Pick List con nombre de empresa en header
- Interfaz responsive

**Endpoints:**
- `GET /pick/` - listado de órdenes
- `GET /pick/<order_id>` - detalles de picking
- `POST /pick/mark-part` - marcar parte como picked/missing/pending
- `POST /pick/complete-order` - marcar orden como completada
- `POST /pick/<order_id>/complete-all` - admin/supervisor completa todos los picks
- `GET /pick/<order_id>/pdf` - generar PDF de picking

---

### 6. **Losses** (Completamente implementado)
Registrar daños y pérdidas de inventario.

**Features:**
- Categorías: damage, lost, expired, defect, other
- Filtro por período (última semana, mes, etc.)
- Filtro por categoría
- Panel de resumen: total de partes perdidas, categoría más común
- Edición de registros
- PDF en escala de grises con nombre de empresa en header

**Endpoints:**
- `GET /losses/` - listado con filtros
- `POST /losses/report` - registrar pérdida/daño
- `POST /losses/update/<record_id>` - editar registro
- `POST /losses/delete/<record_id>` - eliminar registro
- `GET /losses/pdf` - exportar PDF de pérdidas

---

### 7. **Supervision** (Completamente implementado)
Supervisar estado general del almacén y control de calidad.

**Métricas:**
- Active Orders: órdenes en progreso
- Completed Today: órdenes finalizadas hoy
- Missing Items: partes sin stock en órdenes activas

**Features:**
- Filtro por fecha
- Auto-refresh cada 60 segundos
- Botón "Complete Order" para admin/supervisor que llama a `/pick/<order_id>/complete-all`
- Progreso calculado como picked/total (no incluye missing)
- Interfaz responsive

**Endpoints:**
- `GET /supervision/` - dashboard de supervisión
- `POST /supervision/refresh` - actualizar métricas (JSON)

---

### 8. **Analytics** (Completamente implementado)
Proyecciones de consumo de partes basadas en historial de órdenes.

**Concepto:**
- Analiza órdenes completadas en los últimos N meses (history_months)
- Calcula consumo promedio mensual por parte
- Proyecta consumo futuro para los próximos M meses (period_months)

**Jerarquía de fuentes de datos:**
1. **Real:** órdenes completadas y no-simuladas (tiene is_simulated=False, no SIM- en order_number)
2. **Simulated:** órdenes con prefijo SIM- (generadas por demo/simulate-orders)
3. **Estimate:** si no hay datos reales ni simulados, asume cantidad mínima

**Inputs:**
- `period_months`: 1-24 (meses a proyectar)
- `history_months`: 1-24 (meses históricos a analizar)

**Métricas:**
- Consumo mensual promedio
- Proyección total
- Stock actual en overflow
- Cantidad a pedir
- Estado: out (agotado) / low (bajo) / ok (disponible)

**Endpoints:**
- `GET /analytics/` - dashboard
- `GET /analytics/parts` - análisis de partes con filtros
- `GET /analytics/parts/<part_id>` - detalles de consumo por cabinet type

---

### 9. **Demo Tools** (Reorganizado)
Herramientas para cargar datos de prueba y simular operaciones.

**Componentes:**

**Load Demo State**
- Carga colors, cabinet types, partes, warehouse config e inventario de `demo_seed.json`
- Deshabilitado si archivo no existe

**Fill Overflow Warehouse**
- Llena todas las ubicaciones libres con partes aleatorias
- Cantidad por caja: 90, 100 o 120 unidades
- Garantiza que todas las partes aparecen al menos una vez

**Generate Random Work Order**
- Crea una orden con 8-16 gabinetes aleatorios
- Job name estilo subdivisión, lot número 3-dígitos
- Order number en formato XXX.Y
- Se pueden generar múltiples órdenes

**Simulate X Months of Orders**
- Genera órdenes completadas con prefijo SIM-
- Cantidad de gabinetes calculada como: `random(75%-100% de max_cart_slots)`
- Distribuye órdenes en el pasado con fechas realistas
- Consume inventario de overflow durante la simulación
- Registros con quantity ≤ 0 se eliminan automáticamente

**Clear Simulated Orders**
- Elimina todas las órdenes con prefijo SIM-
- Preserva órdenes reales e inventario

**Clear Everything**
- Borra inventory, partes, cabinet types, colores, warehouse config
- Mantiene usuarios intactos

---

## Autenticación y Control de Acceso

**Patrón:** Decorators en `routes/auth.py` usando `@functools.wraps`

```python
@admin_required              # solo admin
@supervisor_required         # admin o supervisor
@order_entry_required        # admin, supervisor, order_entry
@picker_required            # admin, supervisor, picker
@warehouse_supervisor_required # admin, supervisor, warehouse
```

**Roles:**
- `admin` - acceso total, configuración, demo tools
- `supervisor` - órdenes, picking, pérdidas, supervisión
- `warehouse` - recepción, inventario
- `order_entry` - crear órdenes
- `picker` - picking, marcar partes

**Endpoints protegidos:**
- Admin: todos los `/admin/*`
- Orders: `/orders/*`
- Pick: `/pick/*`
- Losses: `/losses/*`
- Supervision: `/supervision/*`
- Analytics: `/analytics/*`
- Receiving: `/receiving/*`
- Inventory: `/inventory/*`

---

## PDFs Mejorados

**Campos añadidos:** Nombre de la empresa (WarehouseConfig.name) en header de todos los PDFs

**Tipos de PDF:**

1. **LOSS & DAMAGE REPORT** (`/losses/pdf`)
   - Tabla: Parte, Cantidad, Categoría, Motivo, Reportado por, Fecha
   - Header con nombre de empresa

2. **REORDER LIST** (`/inventory/shopping/pdf`)
   - Tabla: #, Parte, Cantidad Necesaria, Solicitado por, Fecha
   - Header con nombre de empresa

3. **CASE PICK LIST** (`/pick/<order_id>/pdf`)
   - Múltiples secciones por carrito (cart A, cart B)
   - Tabla: Ubicación, Cantidad, Nombre parte
   - Slots de picking
   - Header con nombre de empresa

---

## Base de Datos - Modelos Clave (`models.py`)

### Inventory
```python
Inventory:
  - part_id (FK → Part)
  - aisle, bay, shelf, location (strings/nullable)
  - quantity (int)
  - is_active (bool: True = active shelf, False = overflow)
  - min_quantity (int, para alertas)
  - received_at, updated_at
```

### Part
```python
Part:
  - name (string, unique)
  - active_aisle, active_bay, active_shelf, active_location
  - is_on_hold (bool)
  - is_shared (bool)
```

### CabinetType
```python
CabinetType:
  - code, name, width, height, color
  - is_custom (bool)
  - parts (relationship → PartTemplate)
  # Nota: annual_qty REMOVIDO (estaba causando problemas)
```

### WarehouseConfig
```python
WarehouseConfig:
  - name (string, nombre de la empresa)
  - total_aisles, total_bays, total_shelves, total_locations
  - active_shelves (número de shelves para picking)
  - max_cart_slots (slot máximos por carrito)
  - label_* y prefix_* (etiquetas y prefijos dinámicos)
```

### WorkOrder
```python
WorkOrder:
  - order_number (string, unique, SIM- para simuladas)
  - job_name, lot_number
  - color (FK → Color)
  - status (pending/in_progress/completed)
  - created_by, created_at, updated_at
  # Nota: is_simulated REMOVIDO (usar prefijo SIM- en lugar de flag)
```

### Loss
```python
Loss:
  - part_id (FK → Part)
  - quantity (cantidad perdida/dañada)
  - reason, category (string: damage/lost/expired/defect/other)
  - comments
  - reported_by, reported_at
```

### REMOVIDOS
- `ProductionPlan` - table y model eliminados completamente
- `WorkOrder.is_simulated` - reemplazado por prefijo SIM-
- `CabinetType.annual_qty` - ya no se usa

---

## Cambios Recientes (Septiembre 2026)

### Optimizaciones de Performance
1. **Inventory Index:** 3 queries globales en lugar de N queries por parte
2. **Shopping List:** set() para búsquedas O(1)
3. **Demo Simulate:** elimina registros con quantity ≤ 0 en lugar de dejar en 0

### Completado
1. Losses module: categorías, filtros, resumen, PDF
2. Supervision module: métricas, auto-refresh, Complete Order button
3. Analytics module: proyecciones, tres fuentes de datos, period/history inputs
4. PDFs: nombre de empresa en headers
5. Auth: decorators pattern en todos los routes
6. Demo Tools: reorganizado, simulación con SIM- prefix

### Eliminado
1. ProductionPlan model y table
2. annual_qty de CabinetType
3. is_simulated flag en WorkOrder
4. stack_confirmed y pending_receive en Receiving

---

## Git Workflow

**El usuario controla completamente git:**
- ✅ `git add` - usuario lo hace manualmente
- ✅ `git commit` - usuario lo hace manualmente
- ✅ `git push` - usuario lo hace manualmente
- ❌ Claude Code NUNCA hace git sin autorización explícita

**Cuando el usuario pide cambios:**
1. Claude ejecuta los cambios en el código
2. Claude muestra los cambios modificados
3. El usuario revisa con su asistente
4. Si está OK, el usuario hace git add/commit/push

---

## Reglas de Negocio Críticas

1. **Una location = Una caja:** Nunca dos cajas en mismo lugar
2. **Part debe existir:** No auto-create parts, solo seleccionar de lista
3. **Overflow válido:** Shelf >= config.active_shelves + 1
4. **Direct to Active:** Suma a stock en ubicación activa de la parte
5. **Only free > 0:** Panel muestra solo ubicaciones con espacio disponible
6. **Location null handling:** `None` y `''` tratados como "sin location"
7. **SIM- prefix:** Órdenes simuladas se identifican por prefijo, no por flag
8. **Quantity ≤ 0:** Registros de inventario con cantidad ≤ 0 se ocultan y eliminan
9. **WarehouseConfig.name:** Aparece en PDFs, Getting Started Wizard, headers

---

## Cómo Trabajar Conmigo

- Soy desarrollador autodidacta aprendiendo
- Explícame qué está mal y por qué lo arreglas así
- Muéstrame siempre el plan antes de hacer cambios grandes
- Si detectas errores, pregúntame si deseo corregirlos
- Analiza riesgos antes de cambios que afecten validaciones
