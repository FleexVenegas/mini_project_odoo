from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)

class IncentiveSalesRuleGoalLine(models.Model):
    _name = 'incentive.sales.rule.goal.line'
    _description = 'Fixed amount per salesperson upon reaching the target.'


    name = fields.Char(compute='_compute_name', store=True)

    rule_id = fields.Many2one(
        'incentive.sales.rule',
        string='Rule',
        required=True,
        ondelete='cascade',
    )

    user_id = fields.Many2one(
        'res.users',
        string='Salesperson',
        required=True,
    )

    fixed_amount = fields.Float(string='Commission %', digits=(16, 6), required=True)

    _sql_constraints = [
        (
            'rule_user_unique',
            'unique(rule_id, user_id)',
            'This salesperson already has an amount assigned in this rule.'
        )
    ]


    @api.depends('rule_id', 'user_id')
    def _compute_name(self):
        for record in self:
            record.name = f"{record.rule_id.name} - {record.user_id.name}"