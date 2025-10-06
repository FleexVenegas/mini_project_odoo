from odoo import models, api, fields  # type: ignore
from odoo.exceptions import UserError, ValidationError  # type: ignore
from datetime import date


class EquipmentAssignment(models.Model):
    _name = "equipment.assignment"
    _description = "Equipment Assignment"

    name = fields.Many2one(
        comodel_name="hr.employee",
        string="Employee",
        help="Employee to whom the equipment is assigned",
        required=True,
    )

    department_id = fields.Many2one(
        comodel_name="hr.department",
        string="Department",
        help="Department of the employee",
        required=True,
    )

    location_id = fields.Many2one(
        comodel_name="stock.location",
        string="Location",
        help="Location where the equipment is assigned",
        required=True,
    )

    delivery_date = fields.Date(
        string="Delivery Date",
        help="Date when the equipment was delivered to the employee",
        required=True,
        default=fields.Date.context_today,
    )

    return_date = fields.Date(
        string="Return Date",
        help="Date when the equipment was returned",
    )

    days_since_delivery = fields.Integer(
        string="Days Since Delivery",
        help="Number of days since the equipment was delivered",
        compute="_compute_days_since_delivery",
        store=True,
    )

    observation = fields.Text(
        string="Observations",
        help="Any additional notes or observations regarding the equipment assignment",
    )

    delivery_manager = fields.Many2one(
        comodel_name="hr.employee",
        string="Delivery Manager",
        help="Manager who delivered the equipment to the employee",
        required=True,
    )

    equipment_id = fields.Many2one(
        comodel_name="equipment.equipment",
        string="Equipment",
        help="Equipment being assigned to the employee",
        required=True,
    )

    assignment_state = fields.Selection(
        related="equipment_id.assignment_state",
        store=True,
        readonly=True,
    )

    @api.model
    def create(self, vals):
        equipment_id = vals.get("equipment_id")
        if equipment_id:
            assigned = self.env["equipment.assignment"].search(
                [
                    ("equipment_id", "=", equipment_id),
                    ("return_date", "=", False),
                ]
            )
            if assigned:
                raise ValidationError(
                    "This equipment is already assigned to another employee."
                )
        record = super().create(vals)
        if record.equipment_id:
            record.equipment_id.assignment_state = "assigned"
        return record

    def write(self, vals):
        res = super().write(vals)
        for rec in self:
            # Si se marca fecha de devolución, libera el equipo
            if rec.return_date:
                rec.equipment_id.assignment_state = "available"
            else:
                # Si no hay fecha de devolución, asegura que esté asignado
                rec.equipment_id.assignment_state = "assigned"
        return res

    # @api.model
    # def _group_expand_state(self, states, domain, order):
    #     # Devuelve todos los posibles valores de 'state' como columnas
    #     return [key for key, _ in self._fields["state"].selection]

    @api.depends("delivery_date", "return_date")
    def _compute_days_since_delivery(self):
        for record in self:
            if record.delivery_date:
                end_date = record.return_date or fields.Date.today()
                record.days_since_delivery = (end_date - record.delivery_date).days
            else:
                record.days_since_delivery = 0

    @api.constrains("equipment_id", "assignment_state")
    def _check_equipment_unique_assignment(self):
        for record in self:
            if record.assignment_state == "assigned":
                existing = self.env["equipment.assignment"].search(
                    [
                        ("equipment_id", "=", record.equipment_id.id),
                        ("assignment_state", "=", "assigned"),
                        ("id", "!=", record.id),
                    ]
                )
                if existing:
                    raise ValidationError(
                        "This equipment is already assigned to another employee."
                    )
