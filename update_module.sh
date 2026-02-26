#!/bin/bash

# -----------------------------
# Script para actualizar módulos de Odoo en Docker
# Uso:
#   ./update_module.sh nombre_modulo
# -----------------------------

# Verificar que se pase el nombre del módulo
if [ -z "$1" ]; then
    echo "❌ Error: Debes proporcionar el nombre del módulo."
    echo "Uso: ./update_module.sh nombre_modulo"
    exit 1
fi

MODULE=$1
CONTAINER_NAME="odoo"  
DB_NAME="odoo_development"

echo "🔄 Actualizando módulo: $MODULE ..."

# Detener el contenedor principal
echo "⏸️  Deteniendo contenedor Odoo..."
docker stop $CONTAINER_NAME > /dev/null 2>&1

# Ejecutar actualización usando un contenedor temporal con el mismo volumen
echo "📦 Ejecutando actualización del módulo..."
docker run --rm \
    --network dev-network \
    -v odoo-web-data:/var/lib/odoo \
    -v "$(pwd)/config:/etc/odoo" \
    -v "$(pwd)/addons:/mnt/extra-addons" \
    -e DB_HOST=postgres-central \
    -e DB_PORT=5432 \
    -e DB_USER=admin \
    -e DB_PASSWORD=adminpass \
    odoo:17.0 \
    odoo -c /etc/odoo/odoo.conf \
    -d $DB_NAME \
    -u $MODULE \
    --stop-after-init \
    --log-level=info

# Verificar si la actualización fue exitosa
if [ $? -eq 0 ]; then
    echo "✅ Módulo '$MODULE' actualizado correctamente."
    
    # Reiniciar el contenedor principal
    echo "🔄 Reiniciando Odoo..."
    docker start $CONTAINER_NAME > /dev/null 2>&1
    
    echo "⏳ Esperando a que Odoo esté listo..."
    sleep 5
    echo "🚀 Odoo está listo en http://localhost:8069"
else
    echo "❌ Error al actualizar el módulo '$MODULE'"
    echo "🔄 Reiniciando contenedor principal..."
    docker start $CONTAINER_NAME > /dev/null 2>&1
    exit 1
fi

exit 0