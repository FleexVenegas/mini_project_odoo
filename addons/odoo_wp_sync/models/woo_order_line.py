"""
Order line model for WooCommerce, linked to odoo.wp.sync (order) and
with WooCommerce-specific fields such as SKU, quantity, price, taxes, etc.
Ordered by sequence to preserve the original order line order.
The currency_id field is computed from the parent order's currency.

You can find it when you open a synced order (odoo.wp.sync) and
go to the lines tab
"""

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
    name = fields.Char(string="Product", readonly=True)
    sku = fields.Char(string="SKU", readonly=True)
    quantity = fields.Float(string="Quantity", digits=(16, 2), readonly=True)
    price = fields.Float(string="Unit Price", digits=(16, 4), readonly=True)
    subtotal = fields.Float(string="Subtotal", digits=(16, 2), readonly=True)
    total = fields.Float(string="Total", digits=(16, 2), readonly=True)
    total_tax = fields.Float(string="Tax", digits=(16, 2), readonly=True)

    currency_id = fields.Many2one(
        "res.currency",
        compute="_compute_currency_id",
        string="Currency",
    )

    @api.depends("order_id.currency")
    def _compute_currency_id(self):
        Currency = self.env["res.currency"]
        for line in self:
            code = line.order_id.currency
            line.currency_id = (
                Currency.search([("name", "=", code)], limit=1) if code else False
            )
