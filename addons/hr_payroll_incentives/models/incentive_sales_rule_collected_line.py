import logging
from odoo import models, fields, api
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

class IncentiveSalesRuleCollectedLine(models.Model):
    _name = 'incentive.sales.rule.collected.line'
    _description = 'Comisión por vendedor sobre el total vendido (sin meta)'

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

    commission = fields.Float(
        string='Porcentaje de Comisión',
        digits=(16, 3),
        required=True,
    )

    _sql_constraints = [
        (
            'rule_user_unique',
            'unique(rule_id, user_id)',
            'Este vendedor ya tiene una comisión asignada en esta regla.'
        )
    ]

    @api.constrains('commission')
    def _check_commission(self):
        for record in self:
            if record.commission < 0 or record.commission > 100:
                raise ValidationError('El porcentaje de comisión debe estar entre 0 y 100.')