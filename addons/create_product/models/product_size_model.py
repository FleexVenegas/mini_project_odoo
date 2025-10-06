from odoo import models, api, fields  # type: ignore


class ProductSize(models.Model):
    _name = "product.size"
    _description = "Tamaño del producto"

    name = fields.Char(string="Tamaño", required=True)

    _sql_constraints = [
        ("unique_name", "UNIQUE(name)", "Este tamaño ya existe."),
    ]

    @api.model
    def create(self, vals):
        if "name" in vals and isinstance(vals["name"], str):
            vals["name"] = vals["name"].upper()

        return super().create(vals)

    def write(self, vals):
        if "name" in vals and isinstance(vals["name"], str):
            vals["name"] = vals["name"].upper()

        return super().write(vals)
