from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import timedelta
import logging

_logger = logging.getLogger(__name__)

class IncentiveWarehouseRun(models.Model):
    _name = 'incentive.warehouse.run'
    _description = 'Ejecución de Incentivo de Almacén'

    name = fields.Char(string='Nombre', required=True)

    user_ids = fields.Many2many(
        'res.users',
        string='Colaboradores',
        required=True,
    )

    line_ids = fields.One2many('incentive.warehouse.run.line', 'run_id', string='Líneas')

    total_pieces = fields.Integer(
        string='Total Piezas',
        compute='_compute_totals',
        store=True,
        help='Número total de piezas procesadas por los usuarios seleccionados dentro del rango de fechas especificado.',
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='Moneda',
        default=lambda self: self.env.company.currency_id,
        required=True,
    )


    total_bonus = fields.Float(
        string='Total Bonus',
        compute='_compute_totals',
        store=True,
        help='Monto total de bonificación a pagar a todos los colaboradores en esta ejecución.',
    )

    rules_ids = fields.Many2many(
        'incentive.warehouse.rule',
        string='Reglas',
        required=True,
    )

    date_from = fields.Date(string='Fecha Desde', required=True)
    date_to = fields.Date(string='Fecha Hasta', required=True)
    generated_at = fields.Datetime(string='Generado En', readonly=True)

    state = fields.Selection([
        ('draft', 'Borrador'),
        ('pending', 'Pendiente'),
        ('completed', 'Completado'),
    ], string='Estado', default='draft')


    @api.constrains('rules_ids')
    def _check_single_rule(self):
        for run in self:
            if len(run.rules_ids) > 1:
                raise ValidationError('Solo se puede seleccionar una regla de incentivo por run.')

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)

        department = self.env['hr.department'].search([
            '|',
            ('name', '=', 'Almacen'),
            ('name', '=', 'Almacén'),
        ], limit=1)

        _logger.info('Default department: %s', department.name if department else 'None')

        if department:
            res['user_ids'] = [(
                6, 0,
                self.env['hr.employee'].search([
                    ('department_id', '=', department.id)
                ]).mapped('user_id').ids
            )]

        return res

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

    @api.depends('line_ids.total_pieces', 'line_ids.total_bonus')
    def _compute_totals(self):
        for run in self:
            run.total_pieces = sum(run.line_ids.mapped('total_pieces'))
            run.total_bonus = sum(run.line_ids.mapped('total_bonus'))

    def action_load_users(self):
        self.ensure_one()
        self.assorted_pieces()
        self.write({
            'state': 'pending',
        })

    def action_generate_incentives(self):
        self.ensure_one()
        self.write({
            'state': 'completed',
            'generated_at': fields.Datetime.now(),
        })

    def assorted_pieces(self):
        self.ensure_one()

        date_to_dt = fields.Date.to_date(self.date_to) + timedelta(days=1)

        _logger.info(f"Desde {self.date_from} hasta {date_to_dt}")

        _logger.info(f"USer: {self.user_ids.mapped('name')}")

        _logger.info(f"USer: {self.user_ids.mapped('id')}")


        moves = self.env['stock.move'].search([
            ('state', '=', 'done'),
            ('picking_id.picking_type_id.code', '=', 'outgoing'),
            ('picking_id.sale_id', '!=', False),
            ('date', '>=', self.date_from),
            ('date', '<', date_to_dt),
        ])


        existing_lines = {line.user_id.id: line for line in self.line_ids}
        lines_to_create = []

        for user in self.user_ids:
            total_pieces_month = sum(moves.mapped('quantity')) 

            if user.id in existing_lines:
                existing_lines[user.id].total_pieces = total_pieces_month
            else:
                lines_to_create.append({
                    'run_id': self.id,
                    'user_id': user.id,
                    'total_pieces': total_pieces_month,
                })

        if lines_to_create:
            self.env['incentive.warehouse.run.line'].create(lines_to_create)

        stale_lines = self.line_ids.filtered(lambda l: l.user_id.id not in self.user_ids.ids)
        stale_lines.unlink()