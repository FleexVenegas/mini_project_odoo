"""
Extended user model for WooCommerce, with a Many2one field
that points to the active instance (woo.instance) selected by the user.
"""

from odoo import models, fields


class ResUsers(models.Model):
    _inherit = "res.users"

    woo_active_instance_id = fields.Many2one(
        "woo.instance",
        string="Active WooCommerce Instance",
        help="Last WooCommerce instance selected by this user",
    )
