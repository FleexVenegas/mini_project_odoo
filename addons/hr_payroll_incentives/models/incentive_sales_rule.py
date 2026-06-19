import logging
from odoo import models, fields, api

_logger = logging.getLogger(__name__)

class IncentiveSalesRule(models.Model):
    _name = 'incentive.sales.rule'
    _description = 'Incentive Sales Rule'

    name = fields.Char(string='Name', required=True)

    team_id = fields.Many2one('crm.team', string='Sales Team', required=True)

    pricelist_id = fields.Many2one('product.pricelist', string='Pricelist', required=True)

    commission = fields.Float(string='Commission', required=True)

    active = fields.Boolean(string='Active', default=True)

    _sql_constraints = [
        (
            'team_pricelist_unique',
            'unique(team_id, pricelist_id)',
            'A rule already exists for this sales team and pricelist.'
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


