# Recomendaciones de Seguridad - Módulo Llavero

## 1. Gestión de la Clave de Encriptación

### Problema

La clave Fernet está hardcodeada en el código, lo cual es un riesgo crítico de seguridad.

### Solución

- La clave debería generarse una sola vez durante la instalación del módulo
- Almacenarla en `ir.config_parameter` con permisos restringidos
- Nunca incluir claves en el código fuente

### Implementación sugerida:

```python
@api.model
def _generate_and_store_key(self):
    """Genera y guarda la clave de encriptación solo si no existe."""
    IrConfig = self.env['ir.config_parameter'].sudo()
    existing_key = IrConfig.get_param('llavero.fernet_key')
    if not existing_key:
        new_key = Fernet.generate_key()
        IrConfig.set_param('llavero.fernet_key', new_key.decode('utf-8'))
```

## 2. Permisos de Acceso

### Actual (ir.model.access.csv)

```csv
access_llavero_password_user,llavero.password user,model_llavero_password,base.group_user,1,1,1,1
```

### Propuesta - Opción A (Más Restrictiva)

```csv
# Solo lectura, escritura y creación. Sin eliminación
access_llavero_password_user,llavero.password user,model_llavero_password,base.group_user,1,1,1,0
```

### Propuesta - Opción B (Con grupo específico)

Crear un grupo específico para gestión de contraseñas:

```xml
<record id="group_llavero_user" model="res.groups">
    <field name="name">Llavero: Usuario</field>
    <field name="category_id" ref="base.module_category_tools"/>
</record>

<record id="group_llavero_manager" model="res.groups">
    <field name="name">Llavero: Administrador</field>
    <field name="category_id" ref="base.module_category_tools"/>
    <field name="implied_ids" eval="[(4, ref('group_llavero_user'))]"/>
</record>
```

## 3. Reglas de Registro (Record Rules)

### Problema Actual

La regla permite acceso a registros sin propietario:

```xml
('user_id','=',False)
```

### Propuesta

```xml
<record id="llavero_password_rule_user" model="ir.rule">
    <field name="name">Regla de usuario para contraseñas</field>
    <field name="model_id" ref="model_llavero_password"/>
    <!-- Solo sus propias contraseñas -->
    <field name="domain_force">[('user_id','=',user.id)]</field>
    <field name="groups" eval="[(4, ref('base.group_user'))]"/>
</record>

<!-- Regla para administradores (ver todo) -->
<record id="llavero_password_rule_admin" model="ir.rule">
    <field name="name">Regla de administrador para contraseñas</field>
    <field name="model_id" ref="model_llavero_password"/>
    <field name="domain_force">[(1,'=',1)]</field>
    <field name="groups" eval="[(4, ref('base.group_system'))]"/>
</record>
```

## 4. Seguridad en Categorías

### Agregar regla para key.category

```xml
<record id="key_category_rule_user" model="ir.rule">
    <field name="name">Categorías: acceso global lectura</field>
    <field name="model_id" ref="model_key_category"/>
    <field name="domain_force">[(1,'=',1)]</field>
    <field name="groups" eval="[(4, ref('base.group_user'))]"/>
    <field name="perm_read" eval="True"/>
    <field name="perm_write" eval="False"/>
    <field name="perm_create" eval="False"/>
    <field name="perm_unlink" eval="False"/>
</record>

<record id="key_category_rule_admin" model="ir.rule">
    <field name="name">Categorías: acceso total admin</field>
    <field name="model_id" ref="model_key_category"/>
    <field name="domain_force">[(1,'=',1)]</field>
    <field name="groups" eval="[(4, ref('base.group_system'))]"/>
</record>
```

## 5. Auditoría y Logging

### Agregar tracking a los modelos

```python
class LlaveroPassword(models.Model):
    _name = 'llavero.password'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="Descripción", required=True, tracking=True)
    user_id = fields.Many2one('res.users', string="Propietario", tracking=True)
```

## 6. Validaciones Adicionales

### En el modelo llavero.password

```python
@api.constrains('user_id')
def _check_user_id(self):
    """Asegurar que un usuario no pueda cambiar el propietario."""
    for rec in self:
        if rec.user_id != self.env.user and not self.env.user.has_group('base.group_system'):
            raise ValidationError(_('No puedes crear contraseñas para otros usuarios.'))

@api.model
def create(self, vals):
    """Forzar que el usuario actual sea el propietario."""
    if 'user_id' not in vals or not self.env.user.has_group('base.group_system'):
        vals['user_id'] = self.env.user.id
    return super().create(vals)

def write(self, vals):
    """Prevenir cambio de propietario."""
    if 'user_id' in vals and not self.env.user.has_group('base.group_system'):
        raise ValidationError(_('No puedes cambiar el propietario de una contraseña.'))
    return super().write(vals)
```

## Prioridad de Implementación

1. **URGENTE**: Eliminar la clave hardcodeada y usar solo ir.config_parameter
2. **ALTO**: Eliminar la condición `('user_id','=',False)` de la regla
3. **ALTO**: Remover permisos de eliminación para usuarios normales
4. **MEDIO**: Agregar reglas de registro para categorías
5. **MEDIO**: Implementar validaciones de seguridad en create/write
6. **BAJO**: Agregar tracking y auditoría

## Comandos para Actualizar

Después de hacer los cambios:

```bash
./update_module.sh modulo_llavero
```
