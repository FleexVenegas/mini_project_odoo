import logging
from odoo import models, fields, api

_logger = logging.getLogger(__name__)

class IncentiveRun(models.Model):
    _name = 'incentive.run'
    _description = 'Ejecución de Incentivos'

    name = fields.Char(string='Nombre', required=True)
    date_from = fields.Date(string='Fecha Desde', required=True)
    date_to = fields.Date(string='Fecha Hasta', required=True)
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('done', 'Hecho'),
    ], string='Estado', default='draft')