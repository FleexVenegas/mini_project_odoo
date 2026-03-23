# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ResConfigSettings(models.TransientModel):
    """
    Configuración de umbrales para clasificación de proveedores por Fill Rate.
    """

    _inherit = "res.config.settings"

    fill_rate_threshold_a = fields.Float(
        string="Umbral Excelente (A)",
        default=95.0,
        config_parameter="fill_rate.threshold_a",
        help="Porcentaje mínimo para clasificar un proveedor como Excelente (A). Ejemplo: 95.0 = 95%",
    )

    fill_rate_threshold_b = fields.Float(
        string="Umbral Bueno (B)",
        default=85.0,
        config_parameter="fill_rate.threshold_b",
        help="Porcentaje mínimo para clasificar un proveedor como Bueno (B). Ejemplo: 85.0 = 85%",
    )

    @api.constrains("fill_rate_threshold_a", "fill_rate_threshold_b")
    def _check_thresholds(self):
        """Validar que el umbral A sea mayor que B."""
        for record in self:
            if record.fill_rate_threshold_a <= record.fill_rate_threshold_b:
                raise models.ValidationError(
                    "El umbral Excelente (A) debe ser mayor que el umbral Bueno (B)"
                )
            if record.fill_rate_threshold_a < 0 or record.fill_rate_threshold_a > 100:
                raise models.ValidationError(
                    "El umbral Excelente (A) debe estar entre 0 y 100"
                )
            if record.fill_rate_threshold_b < 0 or record.fill_rate_threshold_b > 100:
                raise models.ValidationError(
                    "El umbral Bueno (B) debe estar entre 0 y 100"
                )
