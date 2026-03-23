cat > CONTEXT.md << 'EOF'
# PickFlow - Warehouse Pick Management System

## Stack
- Python/Flask + PostgreSQL + HTML/CSS/JavaScript
- Linux (Kubuntu) + VS Code
- GitHub: https://github.com/sarwin-dev/pickflow

## Modulos completados
- Admin (usuarios, cabinet types, warehouse config, colors, locations)
- Receiving (activo y overflow, direct to active)
- Order Entry (crear ordenes con slots dinamicos)
- Pick (tristate: picked/missing/pending, barra de progreso)

## Modulos pendientes
- Reset Order button (Supervision)
- PDF de pick list
- Mobile optimization (Pick module)
- Notificaciones de cambios en ordenes
- Supervision module
- Losses module
- Inventory module

## Roles
admin, supervisor, order_entry, warehouse

## Pendientes tecnicos
- Boton Reset Order en Supervision
- PDF con reportlab
- Mobile-first para Pick
EOF


<!-- "Hola, estamos trabajando en un proyecto llamado PickFlow — un sistema de gestión de picking para almacenes. Aquí está el contexto del proyecto:"
Y luego pega el contenido del archivo CONTEXT.md>