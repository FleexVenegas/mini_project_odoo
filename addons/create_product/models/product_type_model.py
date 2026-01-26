from odoo import models, api, fields


class ProductType(models.Model):
    _name = "product.type"
    _description = "Product Type"
    _order = "name"

    name = fields.Char(
        string="Perfume Type",
        required=True,
        help="Full name of the perfume type. Example: Eau de Parfum, Eau de Toilette, etc.",
    )

    code = fields.Char(
        string="Code or Abbreviation",
        required=True,
        help="Abbreviation of the perfume type. Example: EDP for Eau de Parfum, EDT for Eau de Toilette.",
    )

    _sql_constraints = [
        ("unique_code", "UNIQUE(code)", "This code already exists."),
        ("unique_name", "UNIQUE(name)", "This name already exists."),
    ]

    @api.model
    def create(self, vals):
        """Normalizes name and code to uppercase when creating"""
        if "name" in vals and vals["name"]:
            vals["name"] = vals["name"].strip().upper()
        if "code" in vals and vals["code"]:
            vals["code"] = vals["code"].strip().upper()
        return super().create(vals)

    def write(self, vals):
        """Normalizes name and code to uppercase when updating"""
        if "name" in vals and vals["name"]:
            vals["name"] = vals["name"].strip().upper()
        if "code" in vals and vals["code"]:
            vals["code"] = vals["code"].strip().upper()
        return super().write(vals)
