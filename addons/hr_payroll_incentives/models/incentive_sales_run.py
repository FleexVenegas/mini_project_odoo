from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)

class IncentiveSalesRun(models.Model):
    _name = 'incentive.sales.run'
    _description = 'Incentive Sales Run'

    name = fields.Char(string='Name', required=True)

    team_id = fields.Many2one('crm.team', string='Sales Team', required=True)

    date_from = fields.Date(string='Date From', required=True)

    date_to = fields.Date(string='Date To', required=True)

    generated_at = fields.Datetime(string='Generated At')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('done', 'Done'),
    ], string='State', default='draft')

    line_ids = fields.One2many(
        'incentive.sales.run.line',
        'run_id'
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name'):
                vals['name'] = vals['name'].upper()

        return super().create(vals_list)
    
    def write(self, vals):
        if 'name' in vals and vals['name']:
            vals['name'] = vals['name'].upper()

        return super().write(vals)


    def compute_commissions(self):
        for run in self:
            run.line_ids.unlink()  # Eliminar líneas existentes

            # Buscar órdenes de venta confirmadas dentro del rango de fechas y del equipo de ventas
            orders = self.env['sale.order'].search([
                ('team_id', '=', run.team_id.id),
                ('date_order', '>=', run.date_from),
                ('date_order', '<=', run.date_to),
                ('state', 'in', ['sale', 'done'])
            ])

            lines = []
            for order in orders:
                _logger.info(f'Processing order {order.name} for salesperson {order.user_id.name} with amount {order.amount_untaxed}')

            #     lines.append((0, 0, {
            #         'run_id': run.id,
            #         'sale_order_id': order.id,
            #         'user_id': order.user_id.id,
            #         'amount_untaxed': order.amount_untaxed,
            #         'currency_id': order.currency_id.id,
            #     }))

            # run.write({'line_ids': lines})
