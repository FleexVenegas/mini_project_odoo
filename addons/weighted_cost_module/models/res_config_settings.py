# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    # Campos de configuración para costo ponderado
    weighted_cost_enabled = fields.Boolean(
        string="Habilitar Costo Ponderado",
        config_parameter="weighted_cost_module.weighted_cost_enabled",
        help="Activa el cálculo de costo ponderado para productos",
    )

    weighted_cost_auto_calculate = fields.Boolean(
        string="Cálculo Automático",
        config_parameter="weighted_cost_module.weighted_cost_auto_calculate",
        help="Calcula automáticamente el costo ponderado al registrar movimientos de stock",
    )

    weighted_cost_decimal_precision = fields.Integer(
        string="Precisión Decimal",
        config_parameter="weighted_cost_module.weighted_cost_decimal_precision",
        default=2,
        help="Número de decimales para el cálculo del costo ponderado",
    )
