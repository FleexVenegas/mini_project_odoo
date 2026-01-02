#!/bin/bash

# ===================== CONFIGURACIÓN =====================
MODULE_NAME="$1"
ADDONS_PATH="addons"

if [ -z "$MODULE_NAME" ]; then
    echo "Uso: ./create_module.sh nombre_modulo"
    exit 1
fi

# Verificar que addons exista
if [ ! -d "$ADDONS_PATH" ]; then
    echo "❌ La carpeta 'addons' no existe en este directorio."
    exit 1
fi

MODULE_PATH="$ADDONS_PATH/$MODULE_NAME"

# Rollback si algo falla
rollback() {
    echo "❌ Ocurrió un error. Eliminando módulo '$MODULE_NAME'..."
    rm -rf "$MODULE_PATH"
    echo "Rollback completado."
    exit 1
}

trap rollback ERR

# ===================== NOMBRES DINÁMICOS =====================

# Clase como PurchasingRequirements
MODEL_CLASS=$(echo "$MODULE_NAME" | awk -F'_' '{for(i=1;i<=NF;i++){ $i=toupper(substr($i,1,1)) substr($i,2) } print}' | tr -d ' ')

# Nombre técnico como purchasing.requirements
MODEL_NAME=$(echo "$MODULE_NAME" | sed 's/_/./g')

MODEL_FILE="${MODULE_NAME}_models.py"
VIEW_FILE="${MODULE_NAME}_views.xml"

echo "Creando módulo en addons: $MODULE_PATH ..."

# ===================== ESTRUCTURA DE CARPETAS =====================

mkdir -p $MODULE_PATH/{models,views,controllers,security,data,static/src/js,static/src/scss,static/src/description}

# ===================== ARCHIVOS BASE =====================

# __init__.py
cat <<EOF > $MODULE_PATH/__init__.py
from . import models
from . import controllers
EOF

# __manifest__.py
cat <<EOF > $MODULE_PATH/__manifest__.py
{
    'name': '$MODULE_NAME',
    'version': '1.0',
    'author': 'Ing. Diego Venegas', 
    'category': 'Custom',
    "license": "LGPL-3",
    'summary': 'Módulo generado automáticamente',
    'depends': ['base'],
    'data': [
        'security/ir.model.access.csv',
        'views/$VIEW_FILE'
    ],
    'assets': {
        'web.assets_backend': [
            '$MODULE_NAME/static/src/js/script.js',
            '$MODULE_NAME/static/src/scss/styles.scss'
        ]
    },
    'installable': True,
    'application': False
}
EOF

# ===================== MODELOS =====================

cat <<EOF > $MODULE_PATH/models/__init__.py
from . import ${MODULE_NAME}_models
EOF

cat <<EOF > $MODULE_PATH/models/$MODEL_FILE
from odoo import models, fields

class ${MODEL_CLASS}(models.Model):
    _name = '$MODEL_NAME'
    _description = 'Modelo generado automáticamente'

    name = fields.Char(string="Nombre")
EOF

# ===================== VIEWS =====================

cat <<EOF > $MODULE_PATH/views/$VIEW_FILE
<odoo>

    <!-- Acción primero (evita ParseError) -->
    <record id="action_${MODULE_NAME}" model="ir.actions.act_window">
        <field name="name">${MODEL_CLASS}</field>
        <field name="res_model">$MODEL_NAME</field>
        <field name="view_mode">tree,form</field>
    </record>

    <!-- Vista Tree -->
    <record id="view_${MODULE_NAME}_tree" model="ir.ui.view">
        <field name="name">${MODULE_NAME}.tree</field>
        <field name="model">$MODEL_NAME</field>
        <field name="arch" type="xml">
            <tree>
                <field name="name"/>
            </tree>
        </field>
    </record>

    <!-- Menú raíz -->
    <menuitem id="${MODULE_NAME}_menu_root" name="${MODEL_CLASS}"/>

    <!-- Submenú -->
    <menuitem 
        id="${MODULE_NAME}_menu_modelo" 
        name="Registros"
        parent="${MODULE_NAME}_menu_root"
        action="action_${MODULE_NAME}"
    />

</odoo>
EOF

# ===================== SECURITY =====================

cat <<EOF > $MODULE_PATH/security/ir.model.access.csv
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
access_${MODULE_NAME},access_${MODULE_NAME},model_${MODULE_NAME},base.group_user,1,1,1,1
EOF

# ===================== CONTROLLERS =====================

cat <<EOF > $MODULE_PATH/controllers/__init__.py
from . import main
EOF

cat <<EOF > $MODULE_PATH/controllers/main.py
from odoo import http

class ${MODEL_CLASS}Controller(http.Controller):

    @http.route('/$MODULE_NAME/hello', auth='public')
    def index(self, **kw):
        return "Hola desde el módulo $MODULE_NAME!"
EOF

# ===================== STATIC FILES =====================

echo "// JS base" > $MODULE_PATH/static/src/js/script.js
echo "/* SCSS base */" > $MODULE_PATH/static/src/scss/styles.scss
touch $MODULE_PATH/static/src/description/icon.png

# README
cat <<EOF > $MODULE_PATH/README.md
# Módulo $MODULE_NAME
Generado automáticamente con create_module.sh
EOF

echo "✅ Módulo '$MODULE_NAME' creado exitosamente en addons/"
exit 0
