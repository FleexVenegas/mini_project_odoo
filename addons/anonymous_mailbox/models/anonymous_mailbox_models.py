from odoo import models, fields, api
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class AnonymousMailbox(models.Model):
    _name = "anonymous.mailbox"
    _description = "Anonymous Mailbox"
    _rec_name = "name"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(
        string="Reference",
        required=True,
        copy=False,
        readonly=True,
        default="/",
    )

    subject = fields.Char(
        string="Subject", help="Subject of the anonymous mailbox entry", required=True
    )

    type = fields.Selection(
        [
            ("suggestion", "Suggestion"),
            ("complaint", "Complaint"),
            ("inquiry", "Inquiry"),
            ("other", "Other"),
        ],
        string="Type",
        help="Type of request for the anonymous mailbox entry",
        required=True,
    )

    priority = fields.Selection(
        [
            ("low", "Low"),
            ("medium", "Medium"),
            ("high", "High"),
            ("urgent", "Urgent"),
        ],
        string="Priority",
        help="Priority level of the anonymous mailbox entry",
        default="low",
    )

    contact = fields.Text(
        string="Contact",
        help="Contact information provided in the anonymous mailbox entry",
    )

    created_at = fields.Datetime(
        string="Created At",
        readonly=True,
        help="Date and time when the anonymous mailbox entry was created",
        default=fields.Datetime.now,
    )

    description = fields.Text(
        string="Description",
        help="Detailed description of the anonymous mailbox entry",
        required=True,
    )

    duration_tracking = fields.Float(
        string="Duration Tracking (hours)",
        help="Total duration spent on handling the anonymous mailbox entry",
        default=0.0,
    )

    internal_notes = fields.Text(
        string="Internal Notes",
        help="Internal notes for the anonymous mailbox entry",
    )

    attachment_ids = fields.Many2many(
        "ir.attachment",
        string="Attachment",
        help="File attachment related to the anonymous mailbox entry",
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if "name" not in vals or vals.get("name") in [None, False, "/"]:
                # Genera el folio consecutivo usando secuencia
                vals["name"] = (
                    self.env["ir.sequence"].next_by_code("anonymous.mailbox")
                    or "MA0001"
                )
        return super(AnonymousMailbox, self).create(vals_list)

    @api.constrains("attachment_ids")
    def _check_attachment_limit(self):
        for rec in self:
            max_files = 3  # Cambia a 3 si quieres
            if len(rec.attachment_ids) > max_files:
                raise ValidationError(
                    f"Solo se permiten {max_files} archivos como máximo."
                )
