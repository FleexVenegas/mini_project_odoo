from odoo import models, fields, api
from datetime import timedelta
import logging

_logger = logging.getLogger(__name__)

class IncentiveWarehouseRun(models.Model):
    _name = 'incentive.warehouse.run'
    _description = 'Incentive Warehouse Run'

    name = fields.Char(string='Name', required=True)

    user_ids = fields.Many2many(
        'res.users',
        # 'hr.employee',
        string='Colaborators',
        required=True,
    )

    line_ids = fields.One2many('incentive.warehouse.run.line', 'run_id', string='Lines')

    total_pieces = fields.Integer(
        string='Total Pieces',
        compute='_compute_total_pieces',
        store=True,
        help='Total number of pieces processed by the selected users within the specified date range.',
    )

    rules_ids = fields.Many2many(
        'incentive.warehouse.rule',
        string='Rules',
        required=True
    )

    date_from = fields.Date(string='Date From', required=True)
    date_to = fields.Date(string='Date To', required=True)
    generated_at = fields.Datetime(string='Generated At', readonly=True)
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('pending', 'Pending'),
        ('completed', 'Completed'),
    ], string='State', default='draft')


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
    

    def generate_incentives(self):
        self.ensure_one()

        self.assorted_pieces()
    

    @api.depends('line_ids.total_pieces')
    def _compute_total_pieces(self):
        for run in self:
            run.total_pieces = sum(run.line_ids.mapped('total_pieces'))


    def assorted_pieces(self):
        self.ensure_one()

        date_to_dt = fields.Date.to_date(self.date_to) + timedelta(days=1)

        moves = self.env['stock.move'].search([
            ('state', '=', 'done'),
            ('picking_id.picking_type_id.code', '=', 'outgoing'),
            ('picking_id.user_id', 'in', self.user_ids.ids),
            ('date', '>=', self.date_from),
            ('date', '<', date_to_dt),
        ])

        self.line_ids.unlink()

        lines_vals = []
        for user in self.user_ids:
            user_moves = moves.filtered(lambda m: m.picking_id.user_id == user)
            lines_vals.append({
                'run_id': self.id,
                'user_id': user.id,
                'total_pieces': int(sum(user_moves.mapped('quantity'))),
            })

        self.env['incentive.warehouse.run.line'].create(lines_vals)
