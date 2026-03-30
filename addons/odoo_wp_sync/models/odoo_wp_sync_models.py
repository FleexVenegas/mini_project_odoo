from odoo import models, fields

class OdooWpSync(models.Model):
    _name = 'odoo.wp.sync'
    _description = 'Modelo generado automáticamente'

    name = fields.Char(string="Nombre")
