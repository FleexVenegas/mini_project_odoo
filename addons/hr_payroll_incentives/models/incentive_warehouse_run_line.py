from odoo import models, fields, api
from odoo.exceptions import ValidationError
import logging
from collections import defaultdict

_logger = logging.getLogger(__name__)

class IncentiveWarehouseRunLine(models.Model):
    _name = 'incentive.warehouse.run.line'
    _description = 'Incentive Warehouse Run Line'

    run_id = fields.Many2one('incentive.warehouse.run', required=True, ondelete='cascade')
    user_id = fields.Many2one('res.users', string='User', required=True)

    # Entrada automática
    total_pieces = fields.Integer(string='Total Pieces')

    # Banderas manuales (el gerente marca si hubo incidencia -> anula esa bolsa)
    has_assortment_errors = fields.Boolean(string='Errores de Surtido')
    has_punctuality_issue = fields.Boolean(string='Falta de Puntualidad')
    has_absenteeism = fields.Boolean(string='Ausentismo')
    has_cleanliness_issue = fields.Boolean(string='Falta de Limpieza y Acomodo')

    # Montos por bolsa (calculados, cero si aplica la bandera correspondiente)
    pieces_bonus = fields.Monetary(string='Bono Piezas', compute='_compute_bonuses', store=True, currency_field='currency_id')
    
    errors_bonus = fields.Monetary(string='Bono Errores', compute='_compute_bonuses', store=True, currency_field='currency_id')
    punctuality_bonus = fields.Monetary(string='Bono Puntualidad', compute='_compute_bonuses', store=True, currency_field='currency_id')
    absenteeism_bonus = fields.Monetary(string='Bono Ausentismo', compute='_compute_bonuses', store=True, currency_field='currency_id')
    cleanliness_bonus = fields.Monetary(string='Bono Limpieza', compute='_compute_bonuses', store=True, currency_field='currency_id')

    total_bonus = fields.Monetary(string='Total Bono', compute='_compute_bonuses', store=True, currency_field='currency_id')

    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id,
        required=True,
    )
    
    @api.depends(
        'total_pieces', 'run_id.rules_ids', 'run_id.user_ids',
        'has_assortment_errors', 'has_punctuality_issue',
        'has_absenteeism', 'has_cleanliness_issue',
    )
    def _compute_bonuses(self):
        for line in self:
            rule = line.run_id.rules_ids[:1]
            pieces = line.total_pieces
            user_count = len(line.run_id.user_ids) or 1

            if not rule:
                line.pieces_bonus = 0.0
                line.errors_bonus = 0.0
                line.punctuality_bonus = 0.0
                line.absenteeism_bonus = 0.0
                line.cleanliness_bonus = 0.0
                line.total_bonus = 0.0
                continue

            line.pieces_bonus = pieces * rule.assorted_pieces / user_count
            line.errors_bonus = 0.0 if line.has_assortment_errors else pieces * rule.assortment_errors
            line.punctuality_bonus = 0.0 if line.has_punctuality_issue else pieces * rule.individual_punctuality
            line.absenteeism_bonus = 0.0 if line.has_absenteeism else pieces * rule.absenteeism
            line.cleanliness_bonus = 0.0 if line.has_cleanliness_issue else pieces * rule.cleanliness_order

            line.total_bonus = (
                line.pieces_bonus + line.errors_bonus + line.punctuality_bonus
                + line.absenteeism_bonus + line.cleanliness_bonus
            )