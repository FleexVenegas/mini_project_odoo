from odoo import models, api, fields


class ProductSize(models.Model):
    _name = "product.size"
    _description = "Product Size"
    _order = "name"

    name = fields.Char(
        string="Size",
        required=True,
        help="Product size presentation (e.g.: 100ML, 50ML)",
    )

    _sql_constraints = [
        ("unique_name", "UNIQUE(name)", "This size already exists."),
    ]

    @api.model
    def create(self, vals):
        """Normalizes the name to uppercase when creating"""
        if "name" in vals and vals["name"]:
            vals["name"] = vals["name"].strip().upper()
        return super().create(vals)

    def write(self, vals):
        """Normalizes the name to uppercase when updating"""
        if "name" in vals and vals["name"]:
            vals["name"] = vals["name"].strip().upper()
        return super().write(vals)
