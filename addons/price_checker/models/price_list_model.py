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

    enable_conditional_label = fields.Boolean(
        string="Habilitar etiqueta condicional",
        help="Si está activado, se mostrará una etiqueta en el checador de precios.",
    )

    text_conditional_label = fields.Char(
        string="Texto de la etiqueta condicional",
        help="Texto que se mostrará en la etiqueta condicional.",
    )
