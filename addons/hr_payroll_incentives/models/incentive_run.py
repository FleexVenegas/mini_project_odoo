import logging
from odoo import models, fields, api

_logger = logging.getLogger(__name__)

class IncentiveRun(models.Model):
    _name = 'incentive.run'
    _description = 'Incentive Run'

    name = fields.Char(string='Name', required=True)
    date_from = fields.Date(string='Date From', required=True)
    date_to = fields.Date(string='Date To', required=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done'),
    ], string='Status', default='draft')