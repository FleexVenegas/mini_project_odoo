"""
Modelo de usuario extendido para WooCommerce, con un campo Many2one 
que apunta a la instancia activa (woo.instance) seleccionada por el usuario.
"""


from odoo import models, fields


class ResUsers(models.Model):
    _inherit = "res.users"

    woo_active_instance_id = fields.Many2one(
        "woo.instance",
        string="Active WooCommerce Instance",
        help="Last WooCommerce instance selected by this user",
    )
