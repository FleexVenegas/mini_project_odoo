from odoo import models, fields
import logging

_logger = logging.getLogger(__name__)

class IncentiveWarehouseRun(models.Model):
    _name = 'incentive.warehouse.run'
    _description = 'Incentive Warehouse Run'

    name = fields.Char(string='Name', required=True)
    date_from = fields.Date(string='Date From', required=True)
    date_to = fields.Date(string='Date To', required=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('done', 'Done'),
    ], string='State', default='draft')