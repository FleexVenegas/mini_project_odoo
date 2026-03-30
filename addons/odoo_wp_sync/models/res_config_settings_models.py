from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    wp_url = fields.Char(
        string="WordPress API URL", config_parameter="odoo_wp_sync.wp_url"
    )
    wp_ck = fields.Char(string="Consumer Key", config_parameter="odoo_wp_sync.wp_ck")
    wp_cs = fields.Char(string="Consumer Secret", config_parameter="odoo_wp_sync.wp_cs")
