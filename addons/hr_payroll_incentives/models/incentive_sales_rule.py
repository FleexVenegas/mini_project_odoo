import logging
from odoo import models, fields, api
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

class IncentiveSalesRule(models.Model):
    _name = 'incentive.sales.rule'
    _description = 'Regla de Ventas Incentivadas'

    name = fields.Char(string='Nombre', required=True)
    team_id = fields.Many2one('crm.team', string='Equipo de Ventas', required=True)
    company_id = fields.Many2one(
        'res.company',
        string='Compañía',
        related='team_id.company_id',
        store=True,
        readonly=True,
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Moneda',
        related='company_id.currency_id',
        readonly=True,
    )
    active = fields.Boolean(string='Activo', default=True)

    commission_type = fields.Selection([
        ('pricelist', 'Lista de Precios'),
        ('collected', 'Recogido'),
        ('goal', 'Meta'),
        ('points', 'Puntos'),
    ])

    collected_line_ids = fields.One2many(
        'incentive.sales.rule.collected.line',
        'rule_id',
        string='Comisión por Vendedor',
    )

    pos_config_ids = fields.Many2many(
        'pos.config',
        string='Puntos de Venta',
    )

    sale_type = fields.Boolean(
        string="Eso es lo que se vendió", 
        default=True)
    
    pdv_type = fields.Boolean(
        string="Por punto de venta", 
        default=False)

    pricelist_line_ids = fields.One2many(
        'incentive.sales.rule.pricelist.line',
        'rule_id',
        string='Comisiones por Lista de Precios'
    )

    # --- Campos para tipo 'goal' ---
    goal_amount = fields.Monetary(
        string='Meta de Venta (Equipo)',
        currency_field='currency_id',
    )
    goal_line_ids = fields.One2many(
        'incentive.sales.rule.goal.line',
        'rule_id',
        string='Montos por Vendedor',
    )

    # --- Campos para tipo 'points' (pendiente de implementar cálculo) ---
    points_per_unit = fields.Float(string='Puntos por Unidad Vendida')
    points_value = fields.Float(string='Valor por Punto')


    # --- Por lo vendido
    commission_sale = fields.Float(
                string='Comisión por Venta (%)',
            digits=(16, 3),
    )


    _sql_constraints = [
        (
            'team_commission_type_unique',
            'unique(team_id, commission_type)',
            'Ya existe una regla de este tipo para este equipo.'
        )
    ]

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

    @api.constrains('goal_amount')
    def _check_goal_amount(self):
        for record in self:
            if record.goal_amount and record.goal_amount < 0:
                raise ValidationError('La meta de venta no puede ser negativa.')


