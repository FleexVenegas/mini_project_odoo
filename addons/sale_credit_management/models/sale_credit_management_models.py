from odoo import models, fields

class SaleCreditManagement(models.Model):
    _name = 'sale.credit.management'
    _description = 'Modelo generado automáticamente'

    name = fields.Char(string="Nombre")
