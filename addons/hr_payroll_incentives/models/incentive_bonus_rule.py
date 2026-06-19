from odoo import models, fields
import logging

_logger = logging.getLogger(__name__)

class IncentiveBonusRule(models.Model):
    _name = 'incentive.bonus.rule'
    _description = 'Incentive Bonus Rule'

    name = fields.Char(string='Name', required=True)
    code = fields.Char(string='Code', required=True)
    description = fields.Text(string='Description')
    incentive_rule_id = fields.Many2one('incentive.rule', string='Incentive Rule', required=True)
    bonus_amount = fields.Float(string='Bonus Amount', required=True)