from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    pos_use_bixolon_proxy = fields.Boolean(
        string="Impresora Bixolon",
        related="pos_config_id.use_bixolon_proxy",
        readonly=False,
    )
    pos_bixolon_proxy_url = fields.Char(
        string="URL del proxy Bixolon",
        related="pos_config_id.bixolon_proxy_url",
        readonly=False,
    )
