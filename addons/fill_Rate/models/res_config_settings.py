# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class ResConfigSettings(models.TransientModel):
    """
    Configuration of thresholds for supplier classification by Fill Rate.
    """

    _inherit = "res.config.settings"

    fill_rate_threshold_a = fields.Float(
        string="Excellent Threshold (A)",
        default=95.0,
        config_parameter="fill_rate.threshold_a",
        help="Minimum percentage to classify a supplier as Excellent (A). Example: 95.0 = 95%",
    )

    fill_rate_threshold_b = fields.Float(
        string="Good Threshold (B)",
        default=85.0,
        config_parameter="fill_rate.threshold_b",
        help="Minimum percentage to classify a supplier as Good (B). Example: 85.0 = 85%",
    )

    @api.constrains("fill_rate_threshold_a", "fill_rate_threshold_b")
    def _check_thresholds(self):
        """Validate that Threshold A is greater than Threshold B."""
        for record in self:
            if record.fill_rate_threshold_a <= record.fill_rate_threshold_b:
                raise ValidationError(
                    "The Excellent Threshold (A) must be greater than the Good Threshold (B)"
                )
            if record.fill_rate_threshold_a < 0 or record.fill_rate_threshold_a > 100:
                raise ValidationError(
                    "The Excellent Threshold (A) must be between 0 and 100"
                )
            if record.fill_rate_threshold_b < 0 or record.fill_rate_threshold_b > 100:
                raise ValidationError(
                    "The Good Threshold (B) must be between 0 and 100"
                )
