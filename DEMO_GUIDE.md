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
5. **Clic en "Simulate Production"** (en Admin → Demo Tools)
   - Esto establece cantidades anuales realistas
   - Necesario para que Analytics funcione
6. **Clic en "Simulate X Months of Orders"** con valor = 3
   - Genera 3 meses de órdenes completadas
   - Esto llena el histórico de consumo
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
   - Elige Aisle/Bay/Shelf/Location manualmente
3. **Abre el panel "Free Locations"** (botón abajo)
   - **Muestra la navegación de 3 pantallas:**
     - Pantalla 1: Lista de aisles con espacio disponible
     - Click en un aisle → Pantalla 2
     - Pantalla 2: Bays dentro de ese aisle
     - Click en un bay → Pantalla 3
     - Pantalla 3: Shelves con espacio libre
   - "Esto evita que guardes cajas donde no caben"
4. **NO presiones Register** (solo mostración)
5. **Muestra "Recent Entries"** - historial de lo que se recibió

**Key message:** "Un registro central, sin errores de duplicados"

---

### Demostración 2: Inventory - Ver Stock (2 min)

**Contexto:** "Supervisor ve dónde está cada parte y cuántas hay"

1. **Navega a Inventory**
2. **Busca una parte** (escribe "side" en search)
3. **Muestra la lista:**
   - Nombre de la parte
   - Badge rojo si está agotada
   - Ubicaciones activas y overflow
   - Cantidad en cada lugar
4. **Explica los estados:**
   - Verde "OK" = hay stock suficiente
   - Amarillo "LOW" = poca cantidad
   - Rojo "OUT" = completamente agotada
5. **Abre el badge rojo** (si hay partes agotadas)
   - "Esto notifica de inmediato qué falta"

**Key message:** "Visibilidad total del inventario en tiempo real"

---

### Demostración 3: Analytics - El Corazón de la Demo (5 min)

**Contexto:** "Aquí es donde la magia sucede - predecimos qué va a faltar"

#### Pantalla A: Parts Analytics

1. **Navega a Analytics → (card grande)**
2. **Muestra el selector de meses** arriba a la derecha
3. **Explica qué ves:**
   - "Parts tracked" - cuántas partes diferentes seguimos
   - "Total X-mo units" - cuántas partes se van a usar en ese período
   - "Critical" - cuáles van a faltar en menos de 1 mes
4. **Muestra la tabla:**
   - Ranking por consumo (más consumida arriba)
   - Colores: rojo (crítico), naranja (bajo), amarillo (watch), verde (OK)
5. **Click en una parte** (cualquiera en rojo o naranja)
   - **Drill-down:** Ve qué tipos de gabinete la usan
   - Muestra: Cabinet Type, Annual Qty, Proyección

**Cambia período:** click en "6 mo" - ve cómo cambian los números
- "Enero necesitamos 500, pero en 6 meses necesitamos 3000"

#### Pantalla B: Production Plan

1. **Navega a Analytics → Production Plan**
2. **Muestra la tabla:**
   - Cabinet Type (nombre del gabinete)
   - Annual Qty (cuántos fabricamos/año)
   - 4-mo Projection (cuántos necesitamos en 4 meses)
3. **Explica el flujo:**
   - "Si fabricamos 100 gabinetes base por año..."
   - "...necesitamos 4 paneles laterales cada uno..."
   - "...en 4 meses necesitamos 1,300 paneles"
4. **Clic en "Auto-Simulate"**
   - Llena automáticamente basado en tamaño del gabinete
   - Realista: gabinetes chicos = más cantidad/año
5. **Muestra edición manual:**
   - Cambia un valor (ej: base cabinet 150 → 200)
   - Click "Save Changes"
   - Verás "Saved X cabinet types"

**Key message:** "Planeación automática basada en tu producción real"

---

### Demostración 4: Order Entry - Crear Órdenes (2 min)

**Contexto:** "Aquí se crean los trabajos que vamos a pick"

1. **Navega a Order Entry**
2. **Clic en "Create New Order"**
3. **Rellena:**
   - Order Number: "DEMO-001"
   - Color: selecciona cualquiera
   - Cabinets: agrega 2-3 tipos
4. **Explica slots:** "Cada gabinete es una línea del trabajo"
5. **NO presiones Create** (solo mostración)

**Key message:** "Órdenes estructuradas, con visibilidad de partes necesarias"

---

### Demostración 5: Pick - Seleccionar Partes (2 min)

**Contexto:** "El almacenero va aquí con esta lista y recoge las partes"

1. **Navega a Pick**
2. **Selecciona una orden existente** (de las simuladas)
3. **Muestra la barra de progreso:**
   - "3 de 15 partes seleccionadas"
   - Color cambia según progreso
4. **Marca una parte como "Picked"** (ej: click checkbox)
5. **Muestra "Pending", "Picked", "Missing":**
   - Verde = ya recogidas
   - Gris = esperando
   - Rojo = no hay stock

**Key message:** "Guía visual para el almacenero, sin confusiones"

---

### Demostración 6: Demo Tools - Preparación (1 min)

**Contexto:** "Herramientas para simular escenarios"

1. **Vuelve a Admin → Demo Tools**
2. **Muestra cada sección:**
   - "Load Demo" = resetea a datos iniciales
   - "Fill Overflow Warehouse" = llena todos los espacios
   - "Simulate X Months of Orders" = crea histórico
   - "Simulate Production" = auto-completa plan anual
3. **Explica el uso:**
   - "Para demos usamos esto"
   - "En producción real, tú cargas tus datos reales"

**Key message:** "Fácil de preparar, fácil de resetear"

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

### "¿Qué hace 'Auto-Simulate'?"
Completa automáticamente tu plan de producción basándose en el tamaño de cada gabinete.
- Gabinetes pequeños = más cantidad/año (más rápidos de hacer)
- Gabinetes grandes = menos cantidad/año (más lentos de hacer)
Es un punto de partida realista que puedes editar.

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
- Analytics: los números se recalculan automáticamente

### "¿Cómo sincroniza con mi sistema de producción?"
PickFlow es independiente. Carga tus datos:
- Partes manuales (Admin → Parts) o vía CSV
- Cantidades anuales (Production Plan)
- Luego funciona como sistema de control
Puede conectarse a otros sistemas vía API en el futuro.

---

## ⚠️ Sección 3: Qué NO Tocar Durante la Demo

**Botones peligrosos que resetean datos:**

### 🔴 NUNCA presiones estos:

1. **Admin → Demo Tools → "Clear All"**
   - Borra ABSOLUTAMENTE TODO
   - Colores, tipos, partes, usuarios, órdenes
   - Solo usa si quieres empezar de cero

2. **Admin → Demo Tools → "Clear Overflow"**
   - Borra todo el inventario de overflow
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

### 🛡️ Si algo se daña:

1. Ve a **Admin → Demo Tools**
2. **Clic en "Load Demo"** = resetea todo a estado inicial
3. Luego **"Simulate Production"** + **"Simulate X Months"** para repopular
4. Continúa demostrando

---

## 💡 Notas Finales

- **Tiempo total demo:** 15-20 minutos
- **Mejor horario:** después de "Load Demo", que tarda 10-15 seg
- **Flujo natural:** Demo Tools → Receiving → Inventory → Analytics → Pick → Orders
- **Si el cliente pregunta por API/integraciones:** "Está en roadmap, ahora es independiente"
- **Si pregunta por móvil:** "Pick module optimizado para móvil, otros módulos en web"

---

## 📝 Apuntes para Actualizar

Este documento se actualiza cuando aprendemos algo nuevo sobre cómo explicar la app mejor:

- Nuevas preguntas frecuentes que hacen clientes
- Pasos más cortos o más claros
- Errores comunes en demos
- Explicaciones que funcionan mejor
- Nuevas features que agreguemos

Cuando descubras algo, avísale al equipo para actualizar aquí.

