from odoo import models, fields, api

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    encryption_key = fields.Char(
        string='Encryption Key',
        help='Key used to encrypt/decrypt passwords.',
        config_parameter='password_manager.encryption_key'
    )
