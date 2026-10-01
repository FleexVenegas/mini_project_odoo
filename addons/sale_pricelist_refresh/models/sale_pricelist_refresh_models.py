from odoo import models, fields

class SalePricelistRefresh(models.Model):
    _name = 'sale.pricelist.refresh'
    _description = 'Modelo generado automáticamente'

    name = fields.Char(string="Nombre")
