# PickFlow - Warehouse Pick Management System

## Propósito
Sistema de gestión de almacén para fabricantes de muebles. Permite recibir inventario en ubicaciones de overflow, seleccionar partes para órdenes de trabajo y rastrear entregas.

## Stack
- Backend: Python/Flask + PostgreSQL
- Frontend: HTML5/CSS3 + JavaScript (vanilla)
- Autenticación: Flask sessions
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

## Módulos Completados

### 1. **Admin** (`routes/admin.py`)
Configuración del almacén y gestión de datos maestros.

**Secciones:**
- Usuarios y roles (admin, supervisor, warehouse, order_entry)
- Warehouse Configuration (aisles, bays, shelves activos/overflow, locations)
- Cabinet Types (tipos de muebles: base, wall, tall, etc.)
- Colors (colores disponibles para órdenes)
- Parts (partes del inventario con ubicación activa)
- Demo Tools (cargar/limpiar datos de prueba)

**Endpoints principales:**
- `GET /admin/` - dashboard de configuración
- `POST /admin/demo/reset` - cargar demo_seed.json
- `POST /admin/demo/fill-overflow` - llenar ubicaciones libres con partes aleatorias
- `POST /admin/demo/generate-order` - crear orden de trabajo aleatoria
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

**Validaciones criticas (Aug 2026):**
- Part debe existir - autocomplete only, no se aceptan nombres nuevos
- Location puede ser `None` (sin sub-posición) o número
- **Una location solo puede tener UNA caja**, sin excepciones (eliminada lógica de stacking)
- Shelf debe estar en rango overflow: >= config.active_shelves + 1
- Ubicación duplicada previene cajas múltiples en mismo lugar

**Backend JSON - Free Locations** (`/receiving/free-locations`):
```json
{
  "total_free": 47,
  "aisles": [
    {
      "aisle": 1,
      "free": 12,
      "occupied": 8,
      "total": 20,
      "bays": [
        {
          "bay": 1,
          "free": 5,
          "occupied": 3,
          "total": 8,
          "shelves": [
            {
              "shelf": 3,
              "free": 1,
              "occupied": 3,
              "total": 4
            }
          ]
        }
      ]
    }
  ]
}
```

**Frontend - Panel de Ubicaciones Libres (Aug 2026 - Redesigned):**
- Navegación de 3 pantallas sin recargar datos
- **Pantalla 1 (Aisles):** Lista de aisles con free > 0, arrow "→"
- **Pantalla 2 (Bays):** Bays dentro de aisle, back button "← Aisle XX"
- **Pantalla 3 (Shelves):** Shelves dentro de bay, back button "← Bay XX"
- Mobile-first: filas grandes (16px), táctiles, scroll vertical
- Solo muestra items con free > 0 en cada nivel

**Autocomplete Part:**
- Busca en tiempo real mientras escribe
- Formatea entrada: "toe33" → "Toe 33"
- Solo acepta selección de lista (no tipeo libre)
- Si no existe la parte, muestra error: "Part not found. Go to Admin → Parts"

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

**Vistas:**
- Listado de partes activas y overflow
- Barra de progreso: free vs occupied
- Búsqueda por nombre
- Filtros: solo activo, solo overflow, solo agotado
- Notificación badge rojo en botón Inventory si hay partes agotadas

**Features (notificaciones):**
- Badge rojo con número en esquina superior derecha del botón Inventory
- Muestra cantidad de partes completamente agotadas (quantity = 0)
- Mensaje genérico: "Supervisor will be notified of depleted parts"

**Endpoints:**
- `GET /inventory/` - listado con filtros y búsqueda
- `GET /inventory/search-parts` - búsqueda en tiempo real (JSON)

---

### 4. **Order Entry** (`routes/orders.py`, `templates/orders/`)
Crear órdenes de trabajo con gabinetes y colores especificados.

**Flujo:**
1. Usuario ingresa Job Name (ej: "Project-2025-Alpha")
2. Selecciona Color
3. Añade gabinetes dinámicamente (Base Cabinet, Wall Cabinet, etc.)
4. Sistema valida cantidad de partes disponibles
5. Crea orden y genera list de picking

**Estructura Orden:**
```
Work Order
├─ Job Name (string, unique)
├─ Color (FK → Color)
├─ Cabinets (list dinamico)
│  └─ Cabinet Type → Parts requeridas
├─ Status (draft/confirmed/in_progress/completed)
└─ Timestamp
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
- Interfaz responsive

**Endpoints:**
- `GET /pick/` - listado de órdenes
- `POST /pick/mark-part` - marcar parte como picked/missing/pending
- `POST /pick/complete-order` - marcar orden como completada

---

### 6. **Losses** (`routes/losses.py`)
Registrar daños y pérdidas de inventario (stub).

---

### 7. **Supervision** (`routes/supervision.py`)
Supervisar estado general del almacén (stub).

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
```

### WarehouseConfig
```python
WarehouseConfig:
  - total_aisles, total_bays, total_shelves, total_locations
  - active_shelves (número de shelves para picking)
```

---

## Cambios Recientes (Agosto 2026)

### Receiving Module Improvements
1. **Autocomplete Part Field:**
   - Búsqueda en tiempo real, solo lista (no tipeo libre)
   - Rechaza partes que no existen
   - Error claro: "Part not found. Go to Admin → Parts"

2. **Location Duplicate Validation:**
   - Maneja `location = None` y `location = ''` como equivalentes
   - Una location solo puede tener UNA caja (sin excepciones)
   - Previene registros duplicados que causaban conteos negativos

3. **Removed Stacking Logic:**
   - Eliminada lógica `stack_confirmed` y `pending_receive`
   - Eliminada sesión de confirmación de cajas duplicadas
   - Restricción absoluta: 1 location = 1 caja

4. **Free Locations Panel Redesign (Aug 23 2026):**
   - Cambio de accordion (anidado) a 3 pantallas de navegación
   - Mobile-first: filas grandes, fácil de tocar
   - Navegación instantánea sin recargar datos
   - Back buttons contextuales: "← Aisle XX", "← Bay XX"

---

## Reglas de Negocio Críticas

1. **Una location = Una caja:** Nunca dos cajas en mismo lugar
2. **Part debe existir:** No auto-create parts, solo seleccionar de lista
3. **Overflow valido:** Shelf >= config.active_shelves + 1
4. **Direct to Active:** Suma a stock en ubicación activa de la parte
5. **Only free > 0:** Panel muestra solo ubicaciones con espacio disponible
6. **Location null handling:** `None` y `''` tratados como "sin location"

---

## Cómo Trabajar Conmigo

- Soy desarrollador autodidacta aprendiendo
- Explícame qué está mal y por qué lo arreglas así
- Muéstrame siempre el plan antes de hacer cambios grandes
- Si detectas errores, pregúntame si deseo corregirlos
- Analiza riesgos antes de cambios que afecten validaciones

---

## Git Workflow

- ✅ `git add` y `git commit` cuando termine cambios
- ✅ Mensajes descriptivos en español
- ✅ `git push` al final de cada sesión
- No destruir commits existentes sin avisar