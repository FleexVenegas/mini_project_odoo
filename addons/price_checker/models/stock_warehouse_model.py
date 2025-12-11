from odoo import models, fields


class StockWarehouse(models.Model):
    _inherit = "stock.warehouse"

    price_checker_pricelist_id = fields.Many2many(
        "product.pricelist",
        string="Price List for Price Checker",
        help="Price list to be used in the price checker for this warehouse",
    )

    identifier_name = fields.Char(
        string="Identificador de Almacén",
        help="Identificador o nombre corto del almacén para mostrar en el checador de precios",
    )
