from odoo import models, api, fields  # type: ignore
from odoo.exceptions import UserError  # type: ignore


class Equipment(models.Model):
    _name = "equipment.equipment"
    _description = "Equipment"

    folio = fields.Char(
        string="Folio",
        help="Unique identifier for the equipment assignment",
        readonly=True,
    )

    name = fields.Char(
        string="Equipment Name",
        help="Name of the equipment being assigned",
    )

    # Clasification of the equipment
    equipment_type = fields.Many2one(
        comodel_name="equipment.classification",
        string="Equipment Classification",
        help="Classification of the equipment being assigned",
        required=True,
    )

    equipment_code = fields.Char(
        string="Código de clasificación", related="equipment_type.code", store=True
    )

    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        help="Company to which the equipment assignment belongs",
        required=True,
        # default=lambda self: self.env.company,
    )

    serial_number = fields.Char(
        string="Serial Number",
        help="Unique serial number of the equipment",
        required=True,
    )

    brand = fields.Char(string="Brand", help="Brand of the equipment")

    model = fields.Char(string="Model", help="Model of the equipment")

    operating_system = fields.Char(
        string="Operating System", help="Operating system installed on the equipment"
    )

    unlock_password = fields.Char(
        string="Unlock Password",
        help="Password to unlock the equipment",
    )

    status_equipment = fields.Selection(
        [
            ("optima", "Optima"),
            ("in_repair", "In Repair"),
            ("degraded", "Degraded"),
            ("lost", "Lost"),
        ],
        string="Equipment Status",
        default="optima",
        help="Current status of the equipment",
        tracking=True,
    )

    assignment_state = fields.Selection(
        [
            ("available", "Available"),
            ("assigned", "Assigned"),
        ],
        string="Assignment Status",
        default="available",
        readonly=True,
        tracking=True,
    )

    processor = fields.Char(string="Processor", help="Processor type of the equipment")

    ram = fields.Char(string="RAM", help="Amount of RAM in the equipment")

    storage = fields.Char(string="Storage", help="Storage capacity of the equipment")

    antivirus_key = fields.Char(
        string="Antivirus Key",
        help="License key for the antivirus software installed on the equipment",
    )

    imei1 = fields.Char(
        string="IMEI 1", help="First IMEI number of the equipment (if applicable)"
    )

    imei2 = fields.Char(
        string="IMEI 2", help="Second IMEI number of the equipment (if applicable)"
    )

    has_charger = fields.Boolean(
        string="Has Charger", help="Indicates if the equipment comes with a charger"
    )

    charger_status = fields.Selection(
        [
            ("good", "Good"),
            ("damaged", "Damaged"),
            ("missing", "Missing"),
        ],
        string="Charger Status",
        default="good",
        help="Condition of the charger if it is included with the equipment",
    )

    # equipment_id = fields.Many2one(
    #     comodel_name="equipment.equipment", string="Equipment", required=True
    # )

    @api.model
    def create(self, vals):
        record = super(Equipment, self).create(vals)

        id_str = str(record.id).zfill(2)
        code_letter = (record.equipment_type.code or "xx").upper()[:1]
        company_initial = (record.company_id.name or "xx").strip().upper()[:1]

        serial = record.serial_number or ""
        serial_segment = ""

        # Extracción específica del cuarto segmento en UUIDs
        if (
            serial.count("-") >= 3
        ):  # Verificamos que tenga al menos 3 guiones (4 segmentos)
            serial_segment = serial.split("-")[3].upper()[:4]  # Tomamos el 4to segmento
        else:
            serial_segment = serial[-4:].upper() if len(serial) >= 4 else "0000"

        record.folio = f"{id_str}-{code_letter}{serial_segment}-{company_initial}"

        return record

    def write(self, vals):
        if any(
            field in vals for field in ["equipment_type", "company_id", "serial_number"]
        ):
            # Evitar múltiples llamadas a super() innecesarias
            res = super().write(vals)

            records_to_update = self.filtered(
                lambda r: r.equipment_type and r.company_id
            )
            for record in records_to_update:
                try:
                    id_str = str(record.id).zfill(2)
                    code_letter = (
                        record.equipment_type.code[:1].upper()
                        if record.equipment_type.code
                        else "X"
                    )
                    company_initial = (
                        record.company_id.name[:1].strip().upper()
                        if record.company_id.name
                        else "X"
                    )

                    serial = record.serial_number or ""
                    if "-" in serial:
                        parts = serial.split("-")
                        serial_segment = (
                            parts[3][:4].upper()
                            if len(parts) > 3
                            else serial[-4:].upper()
                        )
                    else:
                        serial_segment = (
                            serial[-4:].upper() if len(serial) >= 4 else "0000"
                        )

                    folio = f"{id_str}-{code_letter}{serial_segment}-{company_initial}"
                    if record.folio != folio:  # Solo actualizar si cambió
                        record.folio = folio
                except (AttributeError, IndexError) as e:
                    # _logger.error(
                    #     f"Error updating folio for record {record.id}: {str(e)}"
                    # )
                    continue
        else:
            res = super().write(vals)

        return res

    # @api.constrains("equipment_id")
    # def _check_equipment_availability(self):
    #     for record in self:
    #         # Check if equipment is already assigned
    #         assigned = self.env["equipment.assignment"].search_count(
    #             [
    #                 ("equipment_id", "=", record.equipment_id.id),
    #                 ("state", "=", "assigned"),
    #                 ("id", "!=", record.id),
    #             ]
    #         )
    #         if assigned:
    #             raise ValidationError(
    #                 "This equipment is already assigned to another employee."
    #             )
