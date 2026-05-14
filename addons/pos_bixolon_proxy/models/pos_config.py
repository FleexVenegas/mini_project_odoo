from odoo import fields, models


class PosConfig(models.Model):
    _inherit = "pos.config"

    use_bixolon_proxy = fields.Boolean(
        string="Impresora Bixolon",
        default=False,
    )
    bixolon_proxy_url = fields.Char(
        string="URL del proxy Bixolon",
        default="http://localhost:8000/",
    )
