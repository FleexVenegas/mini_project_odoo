from odoo import models, fields

class Sh(models.Model):
    _name = 'sh'
    _description = 'Modelo generado automáticamente'

    name = fields.Char(string="Nombre")
