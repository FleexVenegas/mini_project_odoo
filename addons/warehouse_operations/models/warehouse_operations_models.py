from odoo import models, fields

class WarehouseOperations(models.Model):
    _name = 'warehouse.operations'
    _description = 'Modelo generado automáticamente'

    name = fields.Char(string="Nombre")
