from odoo import models, fields, api


class WooParameters(models.Model):
    _name = "odoo.wp.sync.parameters"
    _description = "WooCommerce Sync Parameters"

    name = fields.Char(string="Parameter Name", required=True)
    value = fields.Char(string="Value")
