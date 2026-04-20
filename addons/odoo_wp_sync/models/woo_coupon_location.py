from odoo import models, fields


class WooCouponLocation(models.Model):
    _name = "woo.coupon.location"
    _description = "WooCommerce Coupon Availability Location"
    _order = "sequence"

    name = fields.Char(string="Name", required=True, translate=True)
    code = fields.Char(string="Code", required=True)
    sequence = fields.Integer(default=10)
