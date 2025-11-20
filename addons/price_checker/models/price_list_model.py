from odoo import models, fields
import logging


class PriceListModel(models.Model):
    _inherit = "product.pricelist"

    use_in_price_checker = fields.Boolean(
        string="Usar como referencia del checador de precios"
    )
    price_checker_alias = fields.Char(
        string="Alias para Checador",
        help="Nombre corto que se mostrará en el checador de precios. Si está vacío, se usará el nombre de la lista.",
    )
