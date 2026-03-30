from odoo import models, fields, api


class Receipts(models.Model):
    _name = "receipts"
    _description = "Payment Receipts"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _rec_name = "name"

    name = fields.Char(
        string="Folio", required=True, copy=False, readonly=True, default="New"
    )

    client_id = fields.Many2one(
        "res.partner",
        string="Customer",
        help="Select the customer for this receipt",
        tracking=True,
    )
    date = fields.Date(
        string="Date",
        default=fields.Date.context_today,
        help="Select the receipt date",
        tracking=True,
    )
    total_amount = fields.Float(
        string="Total Amount",
        help="Enter the total amount of the receipt",
        tracking=True,
    )
    amount_to_text = fields.Char(
        string="Amount in Words",
        compute="_compute_amount_to_text",
        store=True,
        help="Total amount in words",
    )
    concept = fields.Text(string="Concept", help="Describe the concept of the receipt")
    user_id = fields.Many2one(
        "res.users",
        string="Prepared by",
        default=lambda self: self.env.user,
        readonly=True,
        help="User who prepared the receipt",
    )
    department_id = fields.Many2one(
        "hr.department",
        string="Department",
        related="user_id.employee_id.department_id",
        store=True,
        readonly=True,
        help="Department to which the user who prepared the receipt belongs",
    )
    payment_method = fields.Selection(
        [
            ("cash", "Cash"),
            ("bank_transfer", "Bank Transfer"),
            ("check", "Check"),
            ("credit_card", "Credit Card"),
            ("debit_card", "Debit Card"),
            ("other", "Other"),
        ],
        string="Payment Method",
        help="Select the payment method",
        tracking=True,
    )
    status = fields.Selection(
        [
            ("draft", "Draft"),
            ("active", "Active"),
            ("cancelled", "Cancelled"),
        ],
        string="Status",
        default="draft",
        required=True,
        tracking=True,
        help="Receipt status",
    )

    @api.depends("total_amount")
    def _compute_amount_to_text(self):
        """Converts the total amount to words"""
        for record in self:
            if record.total_amount:
                record.amount_to_text = self._number_to_text(record.total_amount)
            else:
                record.amount_to_text = "Zero pesos 00/100 M.N."

    def _number_to_text(self, number):
        """Converts a number to text in Spanish"""
        units = [
            "",
            "UN",
            "DOS",
            "TRES",
            "CUATRO",
            "CINCO",
            "SEIS",
            "SIETE",
            "OCHO",
            "NUEVE",
        ]
        tens = [
            "",
            "DIEZ",
            "VEINTE",
            "TREINTA",
            "CUARENTA",
            "CINCUENTA",
            "SESENTA",
            "SETENTA",
            "OCHENTA",
            "NOVENTA",
        ]
        hundreds = [
            "",
            "CIENTO",
            "DOSCIENTOS",
            "TRESCIENTOS",
            "CUATROCIENTOS",
            "QUINIENTOS",
            "SEISCIENTOS",
            "SETECIENTOS",
            "OCHOCIENTOS",
            "NOVECIENTOS",
        ]
        special = {
            11: "ONCE",
            12: "DOCE",
            13: "TRECE",
            14: "CATORCE",
            15: "QUINCE",
            16: "DIECISEIS",
            17: "DIECISIETE",
            18: "DIECIOCHO",
            19: "DIECINUEVE",
            21: "VEINTIUN",
            22: "VEINTIDOS",
            23: "VEINTITRES",
            24: "VEINTICUATRO",
            25: "VEINTICINCO",
            26: "VEINTISEIS",
            27: "VEINTISIETE",
            28: "VEINTIOCHO",
            29: "VEINTINUEVE",
        }

        # Separar enteros y decimales
        integer_part = int(number)
        decimal_part = int(round((number - integer_part) * 100))

        if integer_part == 0:
            text = "CERO"
        elif integer_part == 1:
            text = "UN"
        elif integer_part < 10:
            text = units[integer_part]
        elif integer_part < 100:
            if integer_part in special:
                text = special[integer_part]
            else:
                ten = integer_part // 10
                unit = integer_part % 10
                if unit == 0:
                    text = tens[ten]
                elif ten == 2:
                    text = special.get(integer_part, f"VEINTI{units[unit]}")
                else:
                    text = f"{tens[ten]} Y {units[unit]}"
        elif integer_part < 1000:
            hundred = integer_part // 100
            rest = integer_part % 100
            if integer_part == 100:
                text = "CIEN"
            else:
                text = hundreds[hundred]
                if rest > 0:
                    text += " " + self._number_to_text(rest).split(" PESOS")[0]
        elif integer_part < 1000000:
            thousand = integer_part // 1000
            rest = integer_part % 1000
            if thousand == 1:
                text = "MIL"
            else:
                text = self._number_to_text(thousand).split(" PESOS")[0] + " MIL"
            if rest > 0:
                text += " " + self._number_to_text(rest).split(" PESOS")[0]
        elif integer_part < 1000000000:
            million = integer_part // 1000000
            rest = integer_part % 1000000
            if million == 1:
                text = "UN MILLON"
            else:
                text = self._number_to_text(million).split(" PESOS")[0] + " MILLONES"
            if rest > 0:
                text += " " + self._number_to_text(rest).split(" PESOS")[0]
        else:
            text = "CANTIDAD DEMASIADO GRANDE"

        return f"{text} PESOS {decimal_part:02d}/100 M.N."

    @api.model_create_multi
    def create(self, vals_list):
        """Automatically generates the consecutive folio when creating a receipt"""
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = (
                    self.env["ir.sequence"].next_by_code("receipts.folio") or "New"
                )
            # Automatically set status to active when saving
            if vals.get("status", "draft") == "draft":
                vals["status"] = "active"
        return super(Receipts, self).create(vals_list)
