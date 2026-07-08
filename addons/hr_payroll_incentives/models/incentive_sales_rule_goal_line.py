from odoo import models, fields, api
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)

class IncentiveSalesRuleGoalLine(models.Model):
    _name = 'incentive.sales.rule.goal.line'
    _description = 'Monto fijo por vendedor al alcanzar la meta.'


    name = fields.Char(compute='_compute_name', store=True)

    rule_id = fields.Many2one(
        'incentive.sales.rule',
        string='Regla',
        required=True,
        ondelete='cascade',
    )

    user_id = fields.Many2one(
        'res.users',
        string='Vendedor',
        required=True,
    )

    fixed_amount = fields.Float(
        string='Monto Fijo',  required=True)


    commission_wth_goal = fields.Float(
        string='Comisión sin Meta',
        # currency_field='currency_id',
        digits=(16, 3),
    )


    _sql_constraints = [
        (
            'rule_user_unique',
            'unique(rule_id, user_id)',
            'Este vendedor ya tiene un monto asignado en esta regla.'
        )
    ]


    @api.depends('rule_id', 'user_id')
    def _compute_name(self):
        for record in self:
            record.name = f"{record.rule_id.name} - {record.user_id.name}"

    @api.constrains('fixed_amount')
    def _check_fixed_amount(self):
        for record in self:
            if record.fixed_amount < 0 or record.fixed_amount > 100:
                raise ValidationError('El porcentaje de comisión debe estar entre 0 y 100.')