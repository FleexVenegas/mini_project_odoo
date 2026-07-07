import logging
from odoo import models, fields, api
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class IncentiveSalesRulePricelistLine(models.Model):
    _name = 'incentive.sales.rule.pricelist.line'
    _description = 'Sales Rule Pricelist Line'

    name = fields.Char(compute='_compute_name', store=True)

    rule_id = fields.Many2one(
        'incentive.sales.rule',
        required=True,
        ondelete='cascade'
    )

    pricelist_id = fields.Many2one(
        'product.pricelist',
        string='Pricelist',
        required=True
    )

    commission = fields.Float(
        string='Commission %',
        digits=(16, 3),
        required=True
    )

    _sql_constraints = [
    (
        'rule_pricelist_unique',
        'unique(rule_id, pricelist_id)',
        'This pricelist is already configured in this rule.'
    )
]
    


    @api.depends('rule_id', 'pricelist_id')
    def _compute_name(self):
        for record in self:
            record.name = f"{record.rule_id.name} - {record.pricelist_id.name}"

    @api.constrains('commission')
    def _check_commission(self):
        for record in self:
            if record.commission < 0 or record.commission > 100:
                raise ValidationError('El porcentaje de comisión debe estar entre 0 y 100.')