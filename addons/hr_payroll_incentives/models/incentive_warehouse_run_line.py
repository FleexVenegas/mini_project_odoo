from odoo import models, fields, api
from odoo.exceptions import ValidationError
import logging

class IncentiveWarehouseRunLine(models.Model):
    _name = 'incentive.warehouse.run.line'
    _description = 'Incentive Warehouse Run Line'

    run_id = fields.Many2one('incentive.warehouse.run', required=True, ondelete='cascade')
    user_id = fields.Many2one('res.users', string='User', required=True)
    total_pieces = fields.Integer(string='Total Pieces')