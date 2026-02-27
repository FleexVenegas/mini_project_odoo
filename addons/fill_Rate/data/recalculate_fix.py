"""
Script para recalcular todos los Fill Rate después de la corrección de bugs.
Ejecutar desde: Configuración > Técnico > Ejecutar código Python (modo desarrollador)

O desde una acción de servidor.
"""

# 1. Recalcular todas las cantidades recibidas desde stock.move
print("Actualizando cantidades recibidas...")
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
    if idx % 10 == 0:
        print(f"Procesados {idx}/{total_partners} proveedores...")

print(f"✅ {total_partners} proveedores actualizados")
print("\n🎉 Proceso completado exitosamente")
