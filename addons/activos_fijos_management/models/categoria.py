from odoo import models, fields


class ActivoFijoCategoria(models.Model):
    _name = "activo.fijo.categoria"
    _description = "Fixed Asset Category"
    _order = "name"

    name = fields.Char(string="Category Name", required=True)
    codigo_prefijo = fields.Char(
        string="Folio Prefix",
        required=True,
        help="Prefix used to generate unique folios by category. For example: TR for Transport, ME for Machinery.",
    )
    cuenta_contable_default_id = fields.Many2one(
        "account.account",
        string="Default Accounting Account",
        help="Administrative accounting account that will be used by default when registering assets in this category.",
    )
    descripcion = fields.Text(string="Description")

    _sql_constraints = [
        (
            "codigo_prefijo_unique",
            "unique(codigo_prefijo)",
            "The prefix must be unique per category.",
        )
    ]
