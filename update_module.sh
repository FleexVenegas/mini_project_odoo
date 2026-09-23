#!/bin/bash

# -----------------------------
# Script para actualizar módulos de Odoo en Docker
# Uso:
#   ./update_module.sh nombre_modulo
#   ./update_module.sh nombre_modulo --rebuild   # fuerza rebuild de imagen
# -----------------------------

set -euo pipefail

FORCE_REBUILD=0
MODULE=""

for arg in "$@"; do
    case "$arg" in
        --rebuild|-f)
            FORCE_REBUILD=1
            ;;
        -h|--help)
            echo "Uso: ./update_module.sh nombre_modulo [--rebuild]"
            echo "  --rebuild, -f  Fuerza rebuild de la imagen Docker"
            exit 0
            ;;
        -*)
            echo "❌ Opción desconocida: $arg"
            echo "Uso: ./update_module.sh nombre_modulo [--rebuild]"
            exit 1
            ;;
        *)
            if [ -z "$MODULE" ]; then
                MODULE="$arg"
            else
                echo "❌ Solo se admite un nombre de módulo."
                exit 1
            fi
            ;;
    esac
done

if [ -z "$MODULE" ]; then
    echo "❌ Error: Debes proporcionar el nombre del módulo."
    echo "Uso: ./update_module.sh nombre_modulo [--rebuild]"
    exit 1
fi

CONTAINER_NAME="odoo"
DB_NAME="odoo_development"
ODOO_IMAGE="odoo-custom:17.0"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
HASH_FILE="$SCRIPT_DIR/.odoo_image_build.hash"

# Hash de lo que realmente afecta la imagen (addons van montados por volumen)
image_deps_hash() {
    cat "$SCRIPT_DIR/Dockerfile" "$SCRIPT_DIR/requirements.txt" | shasum -a 256 | awk '{print $1}'
}

needs_rebuild() {
    if [ "$FORCE_REBUILD" -eq 1 ]; then
        return 0
    fi

    if ! docker image inspect "$ODOO_IMAGE" > /dev/null 2>&1; then
        echo "ℹ️  Imagen $ODOO_IMAGE no existe."
        return 0
    fi

    local current_hash saved_hash
    current_hash="$(image_deps_hash)"
    saved_hash=""
    if [ -f "$HASH_FILE" ]; then
        saved_hash="$(cat "$HASH_FILE")"
    fi

    if [ "$current_hash" != "$saved_hash" ]; then
        echo "ℹ️  Dockerfile o requirements.txt cambiaron."
        return 0
    fi

    return 1
}

echo "🔄 Actualizando módulo: $MODULE ..."

if needs_rebuild; then
    echo "🔨 Reconstruyendo imagen Odoo (dependencias)..."
    docker compose build web
    image_deps_hash > "$HASH_FILE"
else
    echo "⏭️  Imagen al día — omitiendo rebuild (usa --rebuild para forzar)."
fi

# Detener el contenedor principal
echo "⏸️  Deteniendo contenedor Odoo..."
docker stop "$CONTAINER_NAME" > /dev/null 2>&1 || true

# Ejecutar actualización usando un contenedor temporal con el mismo volumen
echo "📦 Ejecutando actualización del módulo..."
set +e
docker run --rm \
    --network dev-network \
    -v odoo-web-data:/var/lib/odoo \
    -v "$SCRIPT_DIR/config:/etc/odoo" \
    -v "$SCRIPT_DIR/addons:/mnt/extra-addons" \
    -e DB_HOST=postgres-central \
    -e DB_PORT=5432 \
    -e DB_USER=admin \
    -e DB_PASSWORD=adminpass \
    "$ODOO_IMAGE" \
    odoo -c /etc/odoo/odoo.conf \
    -d "$DB_NAME" \
    -u "$MODULE" \
    --stop-after-init \
    --log-level=info
UPDATE_EXIT=$?
set -e

# Reiniciar el contenedor principal siempre
echo "🔄 Reiniciando Odoo..."
docker start "$CONTAINER_NAME" > /dev/null 2>&1 || true

if [ $UPDATE_EXIT -eq 0 ]; then
    echo "✅ Módulo '$MODULE' actualizado correctamente."
    echo "⏳ Esperando a que Odoo esté listo..."
    sleep 5
    echo "🚀 Odoo está listo en http://localhost:8069"
    exit 0
else
    echo "❌ Error al actualizar el módulo '$MODULE'"
    exit 1
fi
