from odoo import models, api, fields  # type: ignore
from odoo.exceptions import UserError  # type: ignore
from unidecode import unidecode  # type: ignore


class EquipmentClassification(models.Model):
    _name = "equipment.classification"
    _description = "Equipment Classification"

    name = fields.Char(
        string="Classification Name",
        help="Name of the equipment classification",
        required=True,
    )

    code = fields.Char(
        string="Technical code",
        required=True,
        help="Technical code for the equipment classification",
    )

    description = fields.Text(
        string="Description",
        help="Detailed description of the equipment classification",
        required=True,
    )

    @api.model
    def create(self, vals):
        if "name" in vals:
            vals["code"] = unidecode(vals["name"]).lower().replace(" ", "_")
        return super().create(vals)

    def write(self, vals):
        if "name" in vals:
            vals["code"] = unidecode(vals["name"]).lower().replace(" ", "_")
        return super().write(vals)
