# Wizard Genérico de Confirmación

Este módulo incluye un **wizard genérico de confirmación** (`confirmation.wizard`) que puede reutilizarse para cualquier acción que requiera confirmación del usuario. **Diseño minimalista y profesional con estilos incorporados.**

## ✨ Características

- ✅ **Solo texto plano**: No necesitas escribir HTML, el wizard lo formatea automáticamente
- ✅ **Diseño minimalista**: Estilos profesionales incorporados en el wizard
- ✅ **Reutilizable**: Un solo wizard para todas tus confirmaciones
- ✅ **Fácil de usar**: Solo 4 líneas de código
- ✅ **Tamaño personalizable**: Elige entre 4 tamaños predefinidos

## 📏 Tamaños Disponibles

Puedes personalizar el tamaño del wizard con el parámetro `dialog_size`:

| Tamaño       | Valor           | Ancho aproximado |
| ------------ | --------------- | ---------------- |
| Pequeño      | `"small"`       | ~300px           |
| Mediano      | `"medium"`      | ~500px (default) |
| Grande       | `"large"`       | ~800px           |
| Extra Grande | `"extra-large"` | ~1140px          |

**Ejemplo:**

```python
return confirmation_wizard.create_confirmation(
    model_name='mi.modelo',
    method_name='mi_metodo',
    title='Mi título',
    description='Mi descripción',
    dialog_size='large'  # Wizard grande
)
```

## ¿Cómo funciona?

El wizard recibe:

- **Modelo**: El modelo técnico de Odoo (ej: `odoo.wp.sync`)
- **Método**: El método a ejecutar (ej: `action_sync`)
- **Título**: Título personalizado del wizard (opcional)
- **Descripción**: **Solo texto plano** - se formatea automáticamente (opcional)
- **Record ID**: ID de un registro específico si se requiere (opcional)

Cuando el usuario confirma, el wizard ejecuta automáticamente el método especificado.

---

## Ejemplo 1: Sincronización de WooCommerce (caso actual)

```python
def action_open_sync_wizard(self):
    """Abre el wizard de confirmación para sincronizar con WooCommerce"""
    confirmation_wizard = self.env['confirmation.wizard']

    # Solo texto plano, sin HTML
    description = "Esta acción descargará todas las órdenes recientes desde WooCommerce y las importará en Odoo. Este proceso puede tardar unos minutos dependiendo de la cantidad de órdenes."

    return confirmation_wizard.create_confirmation(
        model_name='odoo.wp.sync',
        method_name='action_sync',
        title='¿Sincronizar con WooCommerce?',
        description=description,
        dialog_size='medium'  # Tamaño mediano (default)
    )
```

---

## Ejemplo 2: Eliminar todos los registros

```python
def action_confirm_delete_all(self):
    """Abre wizard para confirmar eliminación masiva"""
    confirmation_wizard = self.env['confirmation.wizard']

    # Solo texto plano
    description = "Esta acción eliminará todos los registros de forma permanente. Esta acción no se puede deshacer."

    return confirmation_wizard.create_confirmation(
        model_name='odoo.wp.sync',
        method_name='delete_all_records',
        title='¡Advertencia! Confirmar eliminación',
        description=description,
        dialog_size='small'  # Wizard pequeño para alertas rápidas
    )

def delete_all_records(self):
    """Método que elimina todos los registros"""
    records = self.search([])
    count = len(records)
    records.unlink()

    return {
        'type': 'ir.actions.client',
        'tag': 'display_notification',
        'params': {
            'title': 'Registros eliminados',
            'message': f'Se eliminaron {count} registros correctamente',
            'type': 'success',
        }
    }
```

---

## Ejemplo 3: Aprobar un registro específico

```python
def action_confirm_approval(self):
    """Abre wizard para confirmar aprobación de un registro"""
    self.ensure_one()  # Asegura que solo sea un registro

    confirmation_wizard = self.env['confirmation.wizard']

    # Texto plano con saltos de línea
    description = f"¿Aprobar el pedido {self.order_number}?\n\nCliente: {self.customer_name}\nTotal: {self.total} {self.currency}"

    return confirmation_wizard.create_confirmation(
        model_name='odoo.wp.sync',
        method_name='approve_order',
        record_id=self.id,  # <-- Importante: pasa el ID del registro específico
        title='Confirmar Aprobación',
        description=description
    )

def approve_order(self):
    """Método que aprueba un pedido específico"""
    self.ensure_one()
    self.write({'status': 'approved'})

    return {
        'type': 'ir.actions.client',
        'tag': 'display_notification',
        'params': {
            'title': 'Pedido aprobado',
            'message': f'El pedido {self.order_number} ha sido aprobado',
            'type': 'success',
        }
    }
```

---

## Ejemplo 4: Usar desde un botón en la vista

### En el modelo (model.py):

```python
def action_confirm_export(self):
    """Abre wizard para confirmar exportación"""
    return self.env['confirmation.wizard'].create_confirmation(
        model_name='my.model',
        method_name='export_data',
        title='Exportar Datos',
        description='<p>¿Desea exportar todos los datos a Excel?</p>'
    )

def export_data(self):
    """Realiza la exportación"""
    # Tu código de exportación aquí
    return {'type': 'ir.actions.act_window_close'}
```

### En la vista (view.xml):

```xml
<button name="action_confirm_export"
        type="object"
        string="Exportar"
        class="btn-primary"
        icon="fa-download"/>
```

---

## Ejemplo 5: Usar desde un menú

### En el archivo de vistas (views.xml):

```xml
<record id="action_server_my_action" model="ir.actions.server">
    <field name="name">Mi Acción</field>
    <field name="model_id" ref="model_my_model"/>
    <field name="state">code</field>
    <field name="code">
action = model.action_confirm_my_action()
    </field>
</record>
```

### En el menú (menu.xml):

```xml
<menuitem id="menu_my_action"
          name="Ejecutar Acción"
          parent="my_menu_root"
          action="action_server_my_action"
          sequence="10"/>
```

---

## Personalización Avanzada

### Con iconos de FontAwesome:

```python
description = """
    <div style="text-align: center; padding: 20px;">
        <i class="fa fa-check-circle" style="font-size: 60px; color: #5CB85C;"></i>
        <h3>Título personalizado</h3>
        <p>Descripción con <strong>HTML</strong></p>
    </div>
"""
```

### Iconos útiles:

- `fa-refresh` - Sincronización
- `fa-trash` - Eliminar
- `fa-warning` - Advertencia
- `fa-check-circle` - Éxito
- `fa-download` - Descargar
- `fa-upload` - Subir
- `fa-send` - Enviar

---

## Ventajas del Wizard Genérico

✅ **Reutilizable** - Un solo wizard para múltiples casos
✅ **Personalizable** - Título y descripción HTML dinámicos
✅ **Flexible** - Funciona con o sin registro específico
✅ **Consistente** - UI uniforme en todo el módulo
✅ **Fácil de usar** - Solo requiere 2 líneas de código

---

## Notas Importantes

1. El método ejecutado debe estar en el modelo especificado
2. Si el método retorna una acción de Odoo, el wizard la ejecutará automáticamente
3. Si no retorna nada, el wizard simplemente se cerrará
4. Para mensajes de éxito/error, usa notificaciones de Odoo
5. El wizard es transient (temporal), no persiste en la base de datos

---

## Estructura de Archivos

```
models/
  └── woo_sync_wizard.py          # Modelo del wizard genérico
views/
  └── wizards/
      └── odoo_wp_confirm_sync_views.xml  # Vista del wizard
security/
  └── ir.model.access.csv         # Permisos (confirmation.wizard)
```
