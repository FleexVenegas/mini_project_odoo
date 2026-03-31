from odoo import models, fields


class SaleOrder(models.Model):
    _inherit = "sale.order"

    x_woo_id = fields.Char(string="Woo ID", index=True)
