from odoo import models, fields, api
import logging
from collections import defaultdict

_logger = logging.getLogger(__name__)

class IncentiveSalesRun(models.Model):
    _name = 'incentive.sales.run'
    _description = 'Incentive Sales Run'

    name = fields.Char(string='Name', required=True)

    team_id = fields.Many2one('crm.team', string='Sales Team', required=True)

    date_from = fields.Date(string='Date From', required=True)

    date_to = fields.Date(string='Date To', required=True)

    generated_at = fields.Datetime(string='Generated At')

    rule_id = fields.Many2one(
        'incentive.sales.rule',
        string='Rule'
    )

    state = fields.Selection([
        ('draft', 'Draft'),
        ('pending', 'Pending'),
        ('completed', 'Completed'),
    ], string='State', default='draft')

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        related='company_id.currency_id',
        readonly=True,
    )

    line_ids = fields.One2many(
        'incentive.sales.run.line',
        'run_id'
    )

    total_commission_amount = fields.Monetary(
        string='Total Commission',
        currency_id='currency_id',
        compute='_compute_total_commission_amount',
        store=True,
    )

    @api.depends('line_ids.commission_amount')
    def _compute_total_commission_amount(self):
        for run in self:
            run.total_commission_amount = sum(run.line_ids.mapped('commission_amount'))

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
            run.line_ids.unlink()

            sale_type = run.rule_id.sale_type
            pdv_type = run.rule_id.pdv_type

            _logger.info(f'Computing commissions for run {run.name} (sale_type={sale_type}, pdv_type={pdv_type}).')



            orders = self.env['sale.order'].search([
                ('team_id', '=', run.team_id.id),
                ('date_order', '>=', run.date_from),
                ('date_order', '<=', run.date_to),
                ('state', 'in', ['sale', 'done'])
            ])

            lines = []
            lines += run._compute_pricelist_commissions(orders)

            _logger.info(f'Computed {len(lines)} commission lines for run {run.name} (pricelist type).')

            lines += run._compute_goal_commissions(orders)

            _logger.info(f'Computed {len(lines)} commission lines for run {run.name} (goal type).')

            run.write({'line_ids': lines})
            self.env.cr.commit()
            run.write({'state': 'completed', 'generated_at': fields.Datetime.now()})

    def _compute_pricelist_commissions(self, orders):
        """Calcula comisión por lista de precios usando las líneas configuradas en la regla del team."""
        self.ensure_one()

        totals_by_pricelist_id = defaultdict(float)
        for order in orders:
            pricelist_id = order.pricelist_id.id
            totals_by_pricelist_id[pricelist_id] += order.amount_untaxed or 0.0

        rule = self.env['incentive.sales.rule'].search([
            ('team_id', '=', self.team_id.id),
            ('commission_type', '=', 'pricelist'),
        ], limit=1)

        if not rule:
            return []

        rate_by_pricelist = {
            line.pricelist_id.id: line.commission
            for line in rule.pricelist_line_ids
        }

        lines = []
        for pricelist_id, total in totals_by_pricelist_id.items():
            rate = rate_by_pricelist.get(pricelist_id)
            if rate is None:
                continue  # sin línea configurada para esta pricelist, se excluye

            _logger.info(f"Comisión para pricelist {pricelist_id}: total={total}, rate={rate}")

            commission_amount = total * rate

            lines.append((0, 0, {
                'run_id': self.id,
                'rule_id': rule.id,
                'pricelist_id': pricelist_id or False,
                'amount_untaxed': total,
                'commission_rate': rate,
                'commission_amount': commission_amount,
            }))

        return lines

    def _compute_goal_commissions(self, orders):
        """Si el equipo llega a la meta colectiva, cada vendedor en goal_line_ids
        cobra su % personal multiplicado por el TOTAL vendido por todo el equipo."""
        self.ensure_one()

        total_sold = sum(orders.mapped('amount_untaxed'))

        rules = self.env['incentive.sales.rule'].search([
            ('team_id', '=', self.team_id.id),
            ('commission_type', '=', 'goal'),
        ])

        lines = []
        for rule in rules:
            if total_sold < rule.goal_amount:
                _logger.info(
                    f'Meta no alcanzada - Regla: {rule.name} - Vendido: {total_sold} - Meta: {rule.goal_amount}'
                )
                continue

            _logger.info(
                f'Meta alcanzada - Regla: {rule.name} - Vendido: {total_sold} - Meta: {rule.goal_amount} comisión por vendedor: {rule.goal_line_ids.mapped("fixed_amount")}'
            )

            for goal_line in rule.goal_line_ids:

                _logger.info(
                    f'Calculando comisión para vendedor {goal_line.user_id.name} - Monto fijo: {goal_line.fixed_amount}%'
                )

                commission_amount = total_sold * goal_line.fixed_amount 

                lines.append((0, 0, {
                    'run_id': self.id,
                    'rule_id': rule.id,
                    'user_id': goal_line.user_id.id,
                    'pricelist_id': False,
                    'amount_untaxed': total_sold,
                    'commission_rate': goal_line.fixed_amount,
                    'commission_amount': commission_amount,
                }))

        return lines