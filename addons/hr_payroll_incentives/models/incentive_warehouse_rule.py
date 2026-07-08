from odoo import models, fields, api
from odoo.exceptions import ValidationError
import logging
from collections import defaultdict

_logger = logging.getLogger(__name__)

class IncentiveWarehouseRule(models.Model):
    _name = 'incentive.warehouse.rule'
    _description = 'Regla de Incentivo de Almacén'

    name = fields.Char(string='Nombre', required=True)


    assorted_pieces = fields.Float(
        string='Piezas Surtidas',
        digits=(16, 3),
        required=True

    )

    assortment_errors = fields.Float(
        string='Errores de Surtido',
        digits=(16, 3),
    )

    individual_punctuality = fields.Float(
        string='Puntualidad Individual',
        digits=(16, 3),
    )

    absenteeism = fields.Float(
        string='Ausentismo',
        digits=(16, 3),
    )

    cleanliness_order = fields.Float(
        string='Limpieza y Orden',
        digits=(16, 3),
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