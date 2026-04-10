"""
Modelo de marcas de WooCommerce.

Compatible con los plugins más usados:
  - Perfect WooCommerce Brands
  - WooCommerce Brands (oficial)
  - YITH WooCommerce Brands

El campo ``woo_id`` es el term_id de la marca en WooCommerce.
El payload se envía como ``"brands": [{"id": 121880}]``.
"""

from odoo import models, fields


class WooBrand(models.Model):
    _name = "woo.brand"
    _description = "WooCommerce Brand"
    _order = "name"

    instance_id = fields.Many2one(
        "woo.instance",
        string="Instancia",
        required=True,
        ondelete="cascade",
        index=True,
    )
    woo_id = fields.Integer(
        string="WooCommerce ID",
        index=True,
        default=0,
        help="ID numérico de la marca en WooCommerce (0 = no sincronizada aún).",
    )
    name = fields.Char(string="Nombre", required=True)
    slug = fields.Char(
        string="Slug", help="Identificador URL de la marca en WooCommerce."
    )
