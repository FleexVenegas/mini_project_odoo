from odoo import models, fields
import logging

_logger = logging.getLogger(__name__)

class IncentiveRule(models.Model):
    _name = 'incentive.rule'
    _description = 'Incentive Rule'

    name = fields.Char(string='Name', required=True)
    code = fields.Char(string='Code', required=True)
    description = fields.Text(string='Description')
    incentive_type = fields.Selection([
        ('sales', 'Sales'),
        ('warehouse', 'Warehouse'),
        ('other', 'Other'),
    ], string='Incentive Type', required=True)