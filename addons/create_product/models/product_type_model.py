from odoo import models, api, fields  # type: ignore
from odoo.exceptions import UserError  # type: ignore


class ProductType(models.Model):
    _name = "product.type"
    _description = "Tipo del producto"

    name = fields.Char(
        string="Tipo de perfume",
        required=True,
        help="Nombre completo del tipo de perfume. Ejemplo: Eau de Parfum, Eau de Toilette, etc.",
    )

    code = fields.Char(
        string="Código o abreviatura",
        required=True,
        help="Abreviatura del tipo de perfume. Ejemplo: EDP para Eau de Parfum, EDT para Eau de Toilette.",
    )

    _sql_constraints = [
        ("unique_code", "UNIQUE(code)", "Este código ya existe."),
    ]

    @api.model
    def create(self, vals):
        if "name" in vals and isinstance(vals["name"], str):
            vals["name"] = vals["name"].upper()

        if "code" in vals and isinstance(vals["code"], str):
            vals["code"] = vals["code"].upper()
        return super().create(vals)

    def write(self, vals):
        if "name" in vals and isinstance(vals["name"], str):
            vals["name"] = vals["name"].upper()

        if "code" in vals and isinstance(vals["code"], str):
            vals["code"] = vals["code"].upper()
        return super().write(vals)
