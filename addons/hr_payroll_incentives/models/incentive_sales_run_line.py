from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)

class IncentiveSalesRunLine(models.Model):
    _name = 'incentive.sales.run.line'
    _description = 'Incentive Sales Run Line'

    run_id = fields.Many2one(
        'incentive.sales.run',
        string='Ejecución de Ventas Incentivadas',
        required=True,
        ondelete='cascade'
    )

    rule_id = fields.Many2one(
        'incentive.sales.rule',
        string='Regla',
    )

    pricelist_id = fields.Many2one(
        'product.pricelist',
        string='Lista de Precios',
    )

    user_id = fields.Many2one('res.users', string='Vendedor')

    # Guarda el total de la ventas de la lista de precios en
    # el período de tiempo especificado por el Incentive Sales Run.
    amount_untaxed = fields.Monetary(
        string='Monto sin Impuestos',
        currency_field='currency_id',
    )

   

    currency_id = fields.Many2one(
        'res.currency',
        string='Moneda',
        related='run_id.company_id.currency_id',
        readonly=True,
    )

    commission_amount = fields.Monetary(
        string='Monto de Comisión',
        currency_field='currency_id',
    )

    commission_rate = fields.Float(
        string='Tasa de Comisión',
        digits=(16, 3),
    )

  