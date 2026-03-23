"""
Script para recalcular todos los Fill Rate después de la corrección de bugs.
Ejecutar desde: Configuración > Técnico > Ejecutar código Python (modo desarrollador)

O desde una acción de servidor.
"""

# 0. Crear registros faltantes para órdenes existentes
print("Creando registros de Fill Rate para órdenes existentes...")
orders_without_fillrate = env["purchase.order"].search(
    [("state", "in", ["purchase", "done"]), ("fill_rate_created", "=", False)]
)
total_orders = len(orders_without_fillrate)
print(f"Encontradas {total_orders} órdenes sin registros de Fill Rate")

created_count = 0
errors = 0
for idx, order in enumerate(orders_without_fillrate, 1):
    try:
        order.create_missing_fill_rate_lines()
        created_count += len(order.fill_rate_line_ids)
        if idx % 10 == 0:
            print(f"Procesadas {idx}/{total_orders} órdenes...")
    except Exception as e:
        errors += 1
        print(f"Error en orden {order.name}: {str(e)[:100]}")
        continue

print(f"✅ {created_count} registros nuevos creados")
if errors > 0:
    print(f"⚠️  {errors} órdenes con errores (continuar de todos modos)")

# 1. Recalcular todas las cantidades recibidas desde stock.move
print("\nActualizando cantidades recibidas...")
fill_rate_lines = env["fill.rate.line"].search([])
total = len(fill_rate_lines)
for idx, line in enumerate(fill_rate_lines, 1):
    line.update_received_quantity()
    if idx % 50 == 0:
        print(f"Procesadas {idx}/{total} líneas...")

print(f"✅ {total} líneas actualizadas correctamente")

# 2. Recalcular Fill Rate de todos los proveedores
print("\nRecalculando Fill Rate de proveedores...")
partners = env["res.partner"].search([("fill_rate_history_ids", "!=", False)])
total_partners = len(partners)
for idx, partner in enumerate(partners, 1):
    partner._compute_fill_rate()
    partner._compute_supplier_class()
    partner._compute_fill_rate_stats()
    if idx % 10 == 0:
        print(f"Procesados {idx}/{total_partners} proveedores...")

print(f"✅ {total_partners} proveedores actualizados")
print("\n🎉 Proceso completado exitosamente")
