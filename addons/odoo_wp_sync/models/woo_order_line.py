from odoo import models, fields, api


class WooOrderLine(models.Model):
    _name = "woo.order.line"
    _description = "WooCommerce Order Line"
    _order = "sequence, id"

    order_id = fields.Many2one(
        "odoo.wp.sync",
        string="Order",
        required=True,
        ondelete="cascade",
        index=True,
    )
    sequence = fields.Integer(default=10)
    name = fields.Char(string="Producto", readonly=True)
    sku = fields.Char(string="SKU", readonly=True)
    quantity = fields.Float(string="Cantidad", digits=(16, 2), readonly=True)
    price = fields.Float(string="Precio Unit.", digits=(16, 4), readonly=True)
    subtotal = fields.Float(string="Subtotal", digits=(16, 2), readonly=True)
    total = fields.Float(string="Total", digits=(16, 2), readonly=True)
    total_tax = fields.Float(string="Impuesto", digits=(16, 2), readonly=True)

    currency_id = fields.Many2one(
        "res.currency",
        compute="_compute_currency_id",
        string="Moneda",
    )

    @api.depends("order_id.currency")
    def _compute_currency_id(self):
        Currency = self.env["res.currency"]
        for line in self:
            code = line.order_id.currency
            line.currency_id = (
                Currency.search([("name", "=", code)], limit=1) if code else False
            )
