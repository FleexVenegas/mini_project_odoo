from odoo import models, fields, api
from odoo.exceptions import ValidationError
import logging
from collections import defaultdict

_logger = logging.getLogger(__name__)


class IncentiveSalesRun(models.Model):
    _name = 'incentive.sales.run'
    _description = 'Ejecución de Ventas Incentivadas'

    name = fields.Char(string='Nombre', required=True)

    rule_ids = fields.Many2many(
        'incentive.sales.rule',
        string='Reglas',
    )

    team_id = fields.Many2one(
        'crm.team',
        string='Equipo de Ventas',
        compute='_compute_team_id',
        store=True,
        readonly=True,
    )

    date_from = fields.Date(string='Fecha Desde', required=True)
    date_to = fields.Date(string='Fecha Hasta', required=True)
    generated_at = fields.Datetime(string='Generado En')

    state = fields.Selection([
        ('draft', 'Borrador'),
        ('pending', 'Pendiente'),
        ('completed', 'Completado'),
    ], string='Estado', default='draft')

    company_id = fields.Many2one(
        'res.company',
        string='Compañía',
        required=True,
        default=lambda self: self.env.company,
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='Moneda',
        related='company_id.currency_id',
        readonly=True,
    )

    line_ids = fields.One2many(
        'incentive.sales.run.line',
        'run_id'
    )

    total_commission_amount = fields.Monetary(
        string='Total Monto de Comisión',
        currency_field='currency_id',
        compute='_compute_total_commission_amount',
        store=True,
    )

    @api.depends('rule_ids')
    def _compute_team_id(self):
        for run in self:
            teams = run.rule_ids.mapped('team_id')
            run.team_id = teams[0] if teams else False

    @api.constrains('rule_ids')
    def _check_rule_ids_same_team(self):
        for run in self:
            teams = run.rule_ids.mapped('team_id')
            if len(set(teams.ids)) > 1:
                raise ValidationError(
                    'Todas las reglas seleccionadas deben pertenecer al mismo equipo de ventas.'
                )

    @api.depends('line_ids.commission_amount')
    def _compute_total_commission_amount(self):
        for run in self:
            run.total_commission_amount = sum(run.line_ids.mapped('commission_amount'))

    @api.constrains('date_from', 'date_to')
    def _check_date_range(self):
        for run in self:
            if run.date_from and run.date_to and run.date_from > run.date_to:
                raise ValidationError('La fecha inicial no puede ser mayor a la fecha final.')

    def _rate_to_ratio(self, rate_value):
        self.ensure_one()
        # Compatibilidad: permite ingresar la comisión como ratio (0.024 = 2.4%)
        # o como porcentaje (2.4 = 2.4%).
        rate = rate_value or 0.0
        if rate < 1:
            return rate
        return rate / 100.0

    def _period_datetime_bounds(self):
        self.ensure_one()
        start_dt = fields.Datetime.to_datetime(self.date_from)
        end_exclusive = fields.Date.add(self.date_to, days=1)
        end_dt = fields.Datetime.to_datetime(end_exclusive)
        return start_dt, end_dt

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
            run.write({'state': 'pending'})
            run.line_ids.unlink()

            if not run.rule_ids:
                _logger.warning(f'No rules defined for run {run.name}. Skipping commission computation.')
                continue

            if not run.team_id:
                _logger.warning(f'No team resolved for run {run.name}. Skipping commission computation.')
                continue

            needs_sale_orders = any(run.rule_ids.mapped('sale_type'))
            orders = self.env['sale.order']
            period_start, period_end = run._period_datetime_bounds()
            if needs_sale_orders:
                orders = self.env['sale.order'].search([
                    ('team_id', '=', run.team_id.id),
                    ('date_order', '>=', period_start),
                    ('date_order', '<', period_end),
                    ('state', 'in', ['sale', 'done'])
                ])


            lines = []
            for rule in run.rule_ids:

                pos_orders = self.env['pos.order']
                if rule.pdv_type:
                    if not rule.pos_config_ids:
                        _logger.warning(
                            f'Regla {rule.name} tiene pdv_type activo pero sin pos_config_ids configurados. Se omite PDV.'
                        )
                    else:
                        pos_orders = self.env['pos.order'].search([
                            ('config_id', 'in', rule.pos_config_ids.ids),
                            ('date_order', '>=', period_start),
                            ('date_order', '<', period_end),
                            ('state', 'in', ['paid', 'done', 'invoiced']),
                        ])

                rule_orders = orders if rule.sale_type else self.env['sale.order']

                if rule.commission_type == 'pricelist':
                    computed = run._compute_pricelist_commissions(rule_orders, pos_orders, rule)
                elif rule.commission_type == 'goal':
                    computed = run._compute_goal_commissions(rule_orders, pos_orders, rule)
                elif rule.commission_type == 'collected':
                    computed = run._compute_collected_commissions(rule_orders, pos_orders, rule)
                else:
                    _logger.info(
                        f'Tipo de comisión "{rule.commission_type}" pendiente de implementar. Se omite regla {rule.name}.'
                    )
                    continue

                lines += computed
                

            run.write({'line_ids': lines})
            run.write({'state': 'completed', 'generated_at': fields.Datetime.now()})

    def _compute_pricelist_commissions(self, orders, pos_orders, rule):
        """Calcula comisión por lista de precios, combinando sale.order y pos.order."""
        self.ensure_one()

        totals_by_pricelist_id = defaultdict(float)

        for order in orders:
            pricelist_id = order.pricelist_id.id
            totals_by_pricelist_id[pricelist_id] += order.amount_untaxed or 0.0

        for pos_order in pos_orders:
            pricelist_id = pos_order.pricelist_id.id
            untaxed = (pos_order.amount_total or 0.0) - (pos_order.amount_tax or 0.0)
            totals_by_pricelist_id[pricelist_id] += untaxed

        rate_by_pricelist = {
            line.pricelist_id.id: line.commission
            for line in rule.pricelist_line_ids
        }

        lines = []
        for pricelist_id, total in totals_by_pricelist_id.items():
            rate = rate_by_pricelist.get(pricelist_id)
            if rate is None:
                continue

            commission_amount = total * self._rate_to_ratio(rate)

            lines.append((0, 0, {
                'run_id': self.id,
                'rule_id': rule.id,
                'pricelist_id': pricelist_id or False,
                'amount_untaxed': total,
                'commission_rate': rate,
                'commission_amount': commission_amount,
            }))

        return lines

    def _compute_goal_commissions(self, orders, pos_orders, rule):
        """Si el equipo llega a la meta colectiva, cada vendedor en goal_line_ids
        cobra su % personal multiplicado por el TOTAL vendido (sale + pos)."""
        self.ensure_one()

        total_sold = sum(orders.mapped('amount_untaxed'))
        total_sold += sum((po.amount_total - po.amount_tax) for po in pos_orders)

        objective_achieved = total_sold >= rule.goal_amount

        lines = []
        for goal_line in rule.goal_line_ids:

            if objective_achieved:
                commission = goal_line.fixed_amount
            else:
                commission = goal_line.commission_wth_goal

            commission_amount = total_sold * self._rate_to_ratio(commission)

            lines.append((0, 0, {
                'run_id': self.id,
                'rule_id': rule.id,
                'user_id': goal_line.user_id.id,
                'pricelist_id': False,
                'amount_untaxed': total_sold,
                'commission_rate': commission,
                'commission_amount': commission_amount,
            }))

        return lines

    def _compute_collected_commissions(self, orders, pos_orders, rule):
        """% fijo por vendedor sobre el total vendido del team (sale + pos), sin condición de meta."""
        self.ensure_one()

        total_sold = sum(orders.mapped('amount_untaxed'))


        for po in pos_orders:
            _logger.info(f'POS Order: {po.name}, Total: {po.amount_total}, Tax: {po.amount_tax}, Untaxed: {po.amount_total - po.amount_tax}')


        total_sold += sum((po.amount_total - po.amount_tax) for po in pos_orders)

        lines = []
        for collected_line in rule.collected_line_ids:
            commission_amount = total_sold * self._rate_to_ratio(collected_line.commission)

            lines.append((0, 0, {
                'run_id': self.id,
                'rule_id': rule.id,
                'user_id': collected_line.user_id.id,
                'pricelist_id': False,
                'amount_untaxed': total_sold,
                'commission_rate': collected_line.commission,
                'commission_amount': commission_amount,
            }))

        return lines