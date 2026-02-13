from odoo import models, fields

class ActivoFijoCategoria(models.Model):
    _name = 'activo.fijo.categoria'
    _description = 'Categoría de Activos Fijos'
    _order = 'name'

    name = fields.Char(string='Nombre de la Categoría', required=True)
    codigo_prefijo = fields.Char(
        string='Prefijo para Folio',
        required=True,
        help="Prefijo utilizado para generar folios únicos por categoría. Ejemplo: TR para Transporte, ME para Maquinaria."
    )
    cuenta_contable_default_id = fields.Many2one(
        'account.account',
        string='Cuenta Contable Predeterminada',
        help="Cuenta contable administrativa que se usará por defecto al registrar activos de esta categoría."
    )
    descripcion = fields.Text(string='Descripción')

    _sql_constraints = [
        ('codigo_prefijo_unique', 'unique(codigo_prefijo)', 'El prefijo debe ser único por categoría.')
    ]