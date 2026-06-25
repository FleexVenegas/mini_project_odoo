from odoo import models, fields
import logging

_logger = logging.getLogger(__name__)

class IncentiveSalesRunLine(models.Model):
    _name = 'incentive.sales.run.line'
    _description = 'Incentive Sales Run Line'

    run_id = fields.Many2one(
        'incentive.sales.run',
        string='Incentive Sales Run',
        required=True,
        ondelete='cascade'
    )

    rule_id = fields.Many2one(
        'incentive.sales.rule',
        string='Rule',
    )

    pricelist_id = fields.Many2one(
        'product.pricelist',
        string='Pricelist'
    )

    user_id = fields.Many2one('res.users', string='Seller')

    # Guarda el total de la ventas de la lista de precios en
    # el período de tiempo especificado por el Incentive Sales Run.
    amount_untaxed = fields.Monetary(
        string='Amount Untaxed',
        currency_id='currency_id',
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        related='run_id.company_id.currency_id',
        readonly=True,
    )

    commission_amount = fields.Monetary(
        string='Commission Amount',
        currency_id='currency_id',
    )

    commission_rate = fields.Float(
        string='Commission Rate',
    )