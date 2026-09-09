# PickFlow - Guía de Demostración

Una guía práctica para demostrar PickFlow a clientes. Fresca, directa, sin tecnicismos.

---

## 📋 Sección 1: Flujo de Demo Paso a Paso

### Antes de empezar (5 min)

1. **Abre la app** en localhost o el servidor de demostración
2. **Login como Admin** (para acceso total a todos los módulos)
3. **Ve a Admin → Demo Tools**
4. **Clic en "Load Demo"** - carga datos realistas de ejemplo
   - ⏱️ Espera 10 segundos
   - Verás: "Loaded: X colors, X cabinet types, X parts, X active records"
5. **Clic en "Simulate X Months of Orders"** con valor = 3
   - Genera 3 meses de órdenes completadas con prefijo SIM-
   - Distribuye órdenes en el pasado con fechas realistas
   - Esto llena el histórico de consumo para Analytics
   - ⏱️ Espera 5 segundos

**✅ Ahora tienes datos reales para demostrar**

---

### Demostración 1: Receiving - Recibir Inventario (3 min)

**Contexto:** "Cuando llega una caja del proveedor, el almacenero la registra aquí"

1. **Navega a Receiving**
2. **Muestra el formulario:**
   - Part: escribe "toe" - verás autocomplete filtrando
   - Quantity: ingresa 100
   - Tipo: selecciona "To Overflow Location"
   - **Location es OBLIGATORIA** - campo rojo si no está completo
3. **Abre el panel "Free Locations"** (botón abajo)
   - **Muestra la grilla dinámica:**
     - Barras de progreso por location (verde/amarillo/naranja/rojo según ocupación)
     - Verde: 0-25% lleno | Amarillo: 26-50% | Naranja: 51-75% | Rojo: 76-100%
     - Click en una celda → panel en el footer con:
       - ❌ Locations ocupadas (en rojo)
       - ✅ Locations libres (en verde)
     - Click en una location libre auto-llena el campo Location del formulario
   - "La app previene que pongas dos cajas en el mismo lugar"
4. **NO presiones Register** (solo mostración)
5. **Muestra "Recent Entries"** - historial de lo que se recibió

**Key message:** "Un registro central, sin errores de duplicados, con validación obligatoria de ubicación"

---

### Demostración 2: Inventory - Ver Stock (2 min)

**Contexto:** "Supervisor ve dónde está cada parte y cuántas hay"

1. **Navega a Inventory**
2. **Explica la carga lazy:**
   - "Por defecto solo muestra partes que necesitan pulldown"
   - "Checkbox 'Show All' revela todo el inventario"
   - "Búsqueda automáticamente desactiva el filtro"
3. **Busca una parte** (escribe "side" en search)
4. **Muestra la lista:**
   - Nombre de la parte
   - Badge rojo si está agotada
   - Ubicaciones activas y overflow
   - Cantidad en cada lugar
   - Botón "Swap" para cambiar ubicación activa de la parte
5. **Explica los estados:**
   - Verde "OK" = hay stock suficiente
   - Amarillo "LOW" = poca cantidad
   - Rojo "OUT" = completamente agotada
6. **Muestra badge rojo** (auto-actualizado cada 30 segundos)
   - "Esto notifica de inmediato qué falta"
   - "Se actualiza automáticamente sin que hagas nada"
7. **Muestra botón "Free Locations"** (esquina superior derecha)
   - Similar a Receiving: muestra grilla con barras de progreso
   - ❌ Locations ocupadas | ✅ Locations libres
   - "Modo informativo: solo consulta, no asigna"
8. **Muestra Shopping List** (botón abajo)
   - "Aquí agregamos partes a reabastecer"
   - "Click en PDF para generar lista de compra con el nombre de tu empresa"

**Key message:** "Visibilidad total del inventario, actualizaciones automáticas, control de ubicaciones"

---

### Demostración 3: Analytics - Proyecciones Inteligentes (5 min)

**Contexto:** "Aquí es donde la magia sucede - predecimos qué va a faltar"

#### Parts Analytics

1. **Navega a Analytics**
2. **Muestra los dos inputs arriba:**
   - **"Project for (months)"** - cuántos meses a proyectar (1-24)
   - **"Based on last (months)"** - cuántos meses históricos analizar (1-24)
   - Explica: "Miramos los últimos 3 meses de órdenes para predecir los próximos 4"
3. **Explica el badge de fuente:**
   - **Verde** = "Usando órdenes reales" (órdenes no-simuladas completadas)
   - **Azul** = "Usando órdenes simuladas" (prefijo SIM-, cuando no hay reales)
   - **Amarillo** = "Sin historial, usando estimación" (cuando no hay datos)
4. **Muestra la tabla:**
   - Ranking por consumo (más consumida arriba)
   - Colores: rojo (crítico), naranja (bajo), amarillo (watch), verde (OK)
5. **Muestra métricas clave:**
   - "Parts tracked" - cuántas partes diferentes seguimos
   - "Total X-mo units" - cuántas partes se van a usar en ese período
   - "Critical" - cuáles van a faltar en menos de 1 mes
6. **Click en una parte** (cualquiera en rojo o naranja)
   - **Drill-down:** Ve qué tipos de gabinete la usan
   - Muestra: Cabinet Type, Width, Per Unit, Projected

**Cambia período:** click en "6 mo" - ve cómo cambian los números
- "Enero necesitamos 500, pero en 6 meses necesitamos 3000"

**Key message:** "Predicción automática basada en historial real"

---

### Demostración 4: Order Entry - Crear Órdenes (2 min)

**Contexto:** "Aquí se crean los trabajos que vamos a pick"

1. **Navega a Order Entry**
2. **Clic en "Create New Order"**
3. **Rellena:**
   - Job Name: "DEMO-001"
   - Color: selecciona cualquiera
   - Cabinets: agrega 2-3 tipos
4. **Explica slots:** "Cada gabinete es una línea del trabajo"
5. **NO presiones Create** (solo mostración)

**Key message:** "Órdenes estructuradas, con visibilidad de partes necesarias"

---

### Demostración 4.5: Admin - Partes y Swap (1 min)

**Contexto:** "Gestión de partes: crear, editar, cambiar ubicación"

1. **Navega a Admin → Parts**
2. **Muestra el listado de partes:**
   - Nombre, ubicación activa, estado
   - Botones de acción: Edit, Swap, Pulldown
3. **Muestra formulario Edit:**
   - "Solo puedes editar el nombre aquí"
   - "Ubicación se maneja con Swap para evitar errores"
4. **Muestra botón Swap:**
   - Click abre diálogo para cambiar aisle/bay/shelf/location
   - "Cambias la ubicación activa donde los pickers buscan esta parte"
   - "Sistema evita conflictos automáticamente"

**Key message:** "Gestión de ubicaciones segura, sin confusiones"

---

### Demostración 5: Pick - Seleccionar Partes (3 min)

**Contexto:** "El almacenero va aquí con esta lista y recoge las partes"

1. **Navega a Pick**
2. **Selecciona una orden existente** (de las simuladas)
3. **Muestra el selector de carrito** (si total_carts=2):
   - Dropdown "Cart A" / "Cart B"
   - "Picker puede seleccionar qué carrito está usando"
   - "La pantalla muestra solo las partes de ese carrito"
4. **Muestra las barras de progreso:**
   - Dual-cart: "Cart A: 3 de 8" | "Cart B: 1 de 7" (si total_carts=2)
   - Single-cart: "3 de 15 partes seleccionadas"
   - Botones "Mark Missing" pequeños al lado de cada barra
   - "Marca todas las partes de ese carrito como faltantes de una vez"
5. **Marca una parte como "Picked"** (ej: click checkbox)
6. **Muestra "Pending", "Picked", "Missing":**
   - Verde = ya recogidas
   - Gris = esperando
   - Rojo = no hay stock
7. **Muestra botón "✓ All" / "✗ None" por cada parte**
   - Click marca TODOS los slots de esa parte como picked/pending de una vez
   - "Ahorra clicks cuando la parte tiene múltiples unidades"
   - Cambia automáticamente según estado (✓ si todos picked, ✗ si todos pending)
8. **Explica sincronización en tiempo real:**
   - "Si otro picker está en la misma orden, ve los cambios SIN recargar"
   - "Múltiples almaceneros pueden pick la misma orden simultáneamente"
   - "Los contadores se actualizan instantáneamente"
9. **Muestra botón "Print PDF"**
   - "Genera lista de picking con ubicaciones exactas"
   - "Dual-cart: incluye secciones separadas por carrito"
   - "Incluye el nombre de tu empresa en el header"

**Key message:** "Picking dual-carrito flexible, sincronización real-time, sin conflictos entre almaceneros"

---

### Demostración 6: Supervision - Supervisar Estado General (2 min)

**Contexto:** "El supervisor ve métricas en tiempo real sin hacer nada"

1. **Navega a Supervision**
2. **Muestra las tres métricas principales:**
   - **Active Orders** - órdenes en progreso ahora mismo
   - **Completed Today** - cuántas órdenes se terminaron hoy
   - **Missing Items** - cuántas partes no tienen stock en órdenes activas
   - "Todas se actualizan instantáneamente conforme los pickers marcan partes"
3. **Abre otra pestaña con Pick:**
   - "Ahora marca una parte como picked"
   - **Supervision auto-actualiza SIN refresh** ✨
   - "Los números cambian en tiempo real porque usa WebSockets"
4. **Muestra modal de órdenes:**
   - Click en una orden activa abre panel con detalles
   - Progreso por carrito (si dual-cart mode)
   - "Puedes ver exactamente dónde está cada orden"
5. **Explica el auto-refresh:**
   - "Cada 60 segundos se verifica si algo cambió"
   - "Pero la sincronización Socket.IO es instantánea"
6. **Muestra el botón "Complete"** (verde, solo para admin/supervisor)
   - "Click aquí marca toda la orden como completada"
   - "Genera automáticamente los picks si no existen"

**Key message:** "Supervisión en tiempo real, sin polling, instantáneo con Socket.IO"

---

### Demostración 7: Losses - Registrar Daños y Pérdidas (1 min)

**Contexto:** "Cuando algo se daña o se pierde, se registra aquí"

1. **Navega a Losses**
2. **Muestra el listado:**
   - Categorías: damage, lost, expired, defect, other
   - Filtro por período (última semana, mes, etc.)
   - Filtro por categoría
3. **Muestra el resumen:**
   - Total de partes perdidas
   - Categoría más común
4. **Explica la edición:**
   - "Click en un registro para editar o eliminar"
5. **Muestra el botón "Print PDF"**
   - "Genera reporte de pérdidas en escala de grises"
   - "Incluye el nombre de tu empresa en el header"

**Key message:** "Trazabilidad de pérdidas para análisis y auditoría"

---

### Demostración 8: Demo Tools - Herramientas de Simulación (1 min)

**Contexto:** "Herramientas para preparar demos y simular escenarios"

1. **Vuelve a Admin → Demo Tools**
2. **Muestra cada card:**

   **Load Demo State**
   - Resetea a datos iniciales desde demo_seed.json (incluye total_carts=2)
   - Limpia todo y recarga demo limpio
   - Dual-cart mode habilitado automáticamente

   **Fill Overflow Warehouse**
   - Llena todos los espacios de overflow con partes aleatorias
   - Cantidad: 90, 100 o 120 unidades por caja
   - Garantiza que cada parte aparece al menos una vez
   - **Botón "Clear"** dentro del mismo card elimina overflow

   **Generate Random Work Order**
   - Crea una orden con 8-16 gabinetes aleatorios
   - Genera automáticamente job name y lot number
   - Click múltiples veces para generar más órdenes

   **Simulate X Months of Orders**
   - Genera órdenes completadas con prefijo SIM-
   - Distribuye órdenes en el pasado con fechas realistas
   - Cantidad de gabinetes: 75%-100% de max_cart_slots
   - Consume inventario de overflow durante la simulación
   - Registros con cantidad ≤ 0 se eliminan automáticamente

   **Clear Simulated Orders**
   - Elimina todas las órdenes con prefijo SIM-
   - Preserva órdenes reales e inventario

   **Clear Everything**
   - ⚠️ Borra ABSOLUTAMENTE TODO
   - Colores, tipos, partes, usuarios, órdenes
   - Solo usa si quieres empezar de cero

3. **Explica el uso:**
   - "Para demos usamos esto"
   - "En producción real, tú cargas tus datos reales"
   - "Dual-cart mode incluido en seed: carts A y B automáticos"

**Key message:** "Fácil de preparar, fácil de resetear, dual-cart listo para usar"

---

### Demostración 8.5: Admin - Login History (1 min)

**Contexto:** "Panel de auditoría para rastrear acceso de usuarios"

1. **Navega a Admin → Login History**
2. **Muestra la tabla:**
   - Usuario (nombre en negrita)
   - Rol (con badge de color)
   - Fecha/Hora del login
   - Dispositivo (📱 Mobile o 💻 Desktop - detectado automáticamente)
3. **Explica el registro:**
   - "Cada login se registra automáticamente"
   - "Útil para auditoría y seguimiento de acceso"
   - "Último 100 logins disponibles"
4. **Muestra detección de dispositivo:**
   - "Mobile detecta: teléfonos, tablets, navegadores móviles"
   - "Desktop para acceso desde computadoras"

**Key message:** "Auditoría completa de acceso a la plataforma"

---

## ❓ Sección 2: Preguntas Frecuentes de Clientes

### "¿Qué es 'Months Remaining'?"
Es cuántos meses te dura el stock actual si consumes al ritmo que estás consumiendo.
- Rojo: menos de 1 mes (¡compra ahora!)
- Naranja: 1-2 meses (buena idea comprar pronto)
- Verde: más de 3 meses (estás bien)

### "¿Qué quiere decir 'Free Locations'?"
Lugares en el almacén donde aún cabe inventario. No todas las ubicaciones están llenas.
- Ayuda a saber dónde guardar una caja sin conflictos
- La app previene que pongas dos cajas en el mismo lugar

### "¿Cómo elige Analytics qué datos mostrar?"
Analytics analiza en orden de prioridad:
1. **Real:** órdenes completadas reales (sin prefijo SIM-)
2. **Simulated:** órdenes con prefijo SIM- (cuando no hay reales)
3. **Estimate:** valores por defecto (cuando no hay ningún dato)

Así siempre tienes un número, aunque sea estimado.

### "¿Qué hace 'Auto-Simulate' en Demo Tools?"
Genera órdenes simuladas (prefijo SIM-) con consumo realista.
- Cantidad de gabinetes por orden: aleatorio entre 75%-100% de max_cart_slots
- Distribuye órdenes en el pasado con fechas realistas
- Consume inventario de overflow
- Perfecto para llenar el histórico sin esperar meses reales

### "¿Para qué simulamos X meses de órdenes?"
Para probar el sistema con datos reales sin esperar meses.
- Generamos órdenes completas con consumo realista
- Popula Analytics con histórico
- Así ves cómo funciona la predicción sin datos reales

### "¿Qué diferencia hay entre 'Active' y 'Overflow'?"
- **Active shelves** = donde toman las partes los workers (acceso rápido)
- **Overflow shelves** = almacenamiento en exceso (para cuando hay mucho stock)
Analytics detecta cuándo algo va a faltar en la zona activa.

### "¿Qué pasa si alguien pone dos cajas en la misma ubicación?"
No puede. La app rechaza duplicados.
- Validación automática
- Mensaje claro: "Esta ubicación ya está en uso"

### "¿Se necesita entrenamiento para los usuarios?"
Poco. Los módulos son intuitivos.
- Receiving: buscar parte, cantidad, ubicación
- Pick: checkbox de recogida, nada más
- Inventory: búsqueda simple
- Admin/Supervisor: paneles más complejos, pero autodescriptivos

### "¿Qué pasa si cometemos un error al registrar?"
Se puede editar o eliminar:
- Inventory: edita ubicación, cantidad, o elimina el registro
- Receiving: no se puede editar (es un log), pero sí compensar con otro registro
- Losses: edita o elimina cualquier registro
- Analytics: los números se recalculan automáticamente

### "¿Cómo sincroniza con mi sistema de producción?"
PickFlow es independiente. Carga tus datos:
- Partes manuales (Admin → Parts) o vía CSV
- Luego funciona como sistema de control
- Puede conectarse a otros sistemas vía API en el futuro

### "¿Por qué aparecen órdenes con prefijo 'SIM-'?"
Son órdenes generadas por Demo Tools para simular histórico.
- Aparecen en Order Entry y Pick como órdenes normales
- Se pueden marcar como completadas como cualquier otra
- Útiles para demos sin esperar datos reales
- Se pueden limpiar con "Clear Simulated Orders" en Demo Tools

---

## ⚠️ Sección 3: Qué NO Tocar Durante la Demo

**Botones peligrosos que resetean datos:**

### 🔴 NUNCA presiones estos:

1. **Admin → Demo Tools → "Clear Everything"**
   - Borra ABSOLUTAMENTE TODO
   - Colores, tipos, partes, usuarios, órdenes
   - Solo usa si quieres empezar de cero

2. **Admin → Demo Tools → Fill Overflow Warehouse → "Clear"**
   - Borra todo el inventario de overflow
   - Está dentro del mismo card, cuidado no presiones por accidente
   - Queremos mostrar stock en la demo

3. **Inventory → "Delete Record"**
   - Elimina una caja específica
   - Es permanente

4. **Orders → "Delete Order"**
   - Borra una orden completa
   - Solo haz esto si algo sale MUY mal

### ✅ SEGURO tocar:

- Search y Filter en cualquier lado
- Crear órdenes (sin confirmar)
- Marcar partes en Pick
- Ver Analytics
- Clickear drill-downs
- Abrir/cerrar paneles
- Cambiar inputs de período en Analytics
- Ver histórico en Supervision

### 🛡️ Si algo se daña:

1. Ve a **Admin → Demo Tools**
2. **Clic en "Load Demo"** = resetea todo a estado inicial
3. Luego **"Simulate X Months"** (con valor 3) para repopular histórico
4. Continúa demostrando

---

## 💡 Notas Finales

- **Tiempo total demo:** 18-25 minutos
- **Mejor horario:** después de "Load Demo", que tarda 10-15 seg
- **Flujo natural:** Demo Tools → Receiving → Inventory → Analytics → Pick → Supervision → Losses
- **Si el cliente pregunta por API/integraciones:** "Está en roadmap, ahora es independiente"
- **Si pregunta por móvil:** "Pick module optimizado para móvil, otros módulos en web"
- **Si pregunta por roles:** "5 roles: admin, supervisor, order_entry, picker, warehouse"

---

## 📝 Apuntes para Actualizar

Este documento se actualiza cuando aprendemos algo nuevo sobre cómo explicar la app mejor:

- Nuevas preguntas frecuentes que hacen clientes
- Pasos más cortos o más claros
- Errores comunes en demos
- Explicaciones que funcionan mejor
- Nuevas features que agreguemos

Cuando descubras algo, avísale al equipo para actualizar aquí.
