from odoo import models, fields
import logging

_logger = logging.getLogger(__name__)

class IncentiveBonusRule(models.Model):
    _name = 'incentive.bonus.rule'
    _description = 'Incentive Bonus Rule'

    name = fields.Char(string='Regla', required=True)
    code = fields.Char(string='Código', required=True)
    description = fields.Text(string='Descripción')
    incentive_rule_id = fields.Many2one('incentive.rule', string='Regla de Incentivo', required=True)
    bonus_amount = fields.Float(string='Monto del Bono', required=True)