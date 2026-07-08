from odoo import models, fields
import logging

_logger = logging.getLogger(__name__)

class IncentiveRule(models.Model):
    _name = 'incentive.rule'
    _description = 'Regla de Incentivo'

    name = fields.Char(string='Nombre', required=True)
    code = fields.Char(string='Código', required=True)
    description = fields.Text(string='Descripción')
    incentive_type = fields.Selection([
        ('sales', 'Ventas'),
        ('warehouse', 'Almacén'),
        ('other', 'Otro'),
    ], string='Tipo de Incentivo', required=True)