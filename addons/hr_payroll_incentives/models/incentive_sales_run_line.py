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

    user_id = fields.Many2one(
        'res.users', 
        string='Salesperson', 
        required=True
    )

    sale_order_id = fields.Many2one(
        'sale.order', 
        string='Sale Order', 
        required=True
    )

    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id
    )

    amount_untaxed = fields.Monetary(
        currency_field='currency_id'
    )
