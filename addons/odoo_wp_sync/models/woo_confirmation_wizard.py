# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class ConfirmationWizard(models.TransientModel):
    """Generic confirmation wizard that can execute any method"""

    _name = "confirmation.wizard"
    _description = "Generic Confirmation Wizard"

    title = fields.Char(string="Title", default="Confirmation")

    description = fields.Html(
        string="Description",
        default="Are you sure you want to continue with this action?",
    )

    description_text = fields.Char(
        string="Description Text",
        help="Plain text that will be automatically converted to HTML",
    )

    model_name = fields.Char(string="Model", help="Technical name of the model")

    method_name = fields.Char(string="Method", help="Name of the method to execute")

    record_id = fields.Integer(
        string="Record ID",
        help="ID of the record on which to execute the method (optional)",
    )

    record_ids = fields.Char(
        string="Record IDs",
        help="IDs of multiple records separated by commas (optional)",
    )

    context_data = fields.Text(
        string="Additional context", help="Context data in JSON format (optional)"
    )

    @staticmethod
    def _format_description(text):
        """
        Converts plain text to HTML with basic formatting.
        Detects line breaks and converts them to <br/>.
        """
        if not text:
            return "Are you sure you want to continue with this action?"

        # If it is already HTML (contains tags), return as-is
        if "<" in text and ">" in text:
            return text

        # Convert line breaks to <br/>
        text = text.replace("\n", "<br/>")

        return text

    @api.model
    def create_confirmation(
        self,
        model_name,
        method_name,
        title=None,
        description=None,
        record_id=None,
        record_ids=None,
        context_data=None,
        dialog_size="medium",
    ):
        """
        Helper method to easily create a confirmation wizard.

        :param model_name: Model name (e.g. 'odoo.wp.sync')
        :param method_name: Method name to execute (e.g. 'action_sync')
        :param title: Wizard title (optional)
        :param description: Plain text that will be converted to HTML (optional)
        :param record_id: ID of the specific record (optional, for a single record)
        :param record_ids: List of record IDs (optional, for multiple records)
        :param context_data: Additional context data (optional)
        :param dialog_size: Wizard size: 'small', 'medium', 'large', 'extra-large' (default: 'medium')
        :return: Action to open the wizard
        """
        # Convert plain text to formatted HTML
        description_html = self._format_description(
            description or "Are you sure you want to continue with this action?"
        )

        vals = {
            "title": title or "Confirmation",
            "description": description_html,
            "model_name": model_name,
            "method_name": method_name,
            "context_data": context_data,
        }

        # Add record_id or record_ids as appropriate
        if record_ids:
            # Convert list to comma-separated string
            if isinstance(record_ids, list):
                vals["record_ids"] = ",".join(map(str, record_ids))
            else:
                vals["record_ids"] = str(record_ids)
        elif record_id:
            vals["record_id"] = record_id

        wizard = self.create(vals)

        # Size mapping
        size_classes = {
            "small": "modal-sm",  # ~300px
            "medium": "modal-md",  # ~500px (default)
            "large": "modal-lg",  # ~800px
            "extra-large": "modal-xl",  # ~1140px
        }

        return {
            "name": title or "Confirmation",
            "type": "ir.actions.act_window",
            "res_model": "confirmation.wizard",
            "view_mode": "form",
            "res_id": wizard.id,
            "target": "new",
            "context": {"dialog_size": size_classes.get(dialog_size, "modal-md")},
        }

    def action_confirm(self):
        """Executes the specified method when the user confirms."""
        self.ensure_one()

        if not self.model_name or not self.method_name:
            raise UserError(_("No model or method has been specified."))

        try:
            # Get the model
            model = self.env[self.model_name]

            # Determine if there are specific records
            if self.record_ids:
                # Multiple records
                ids = [
                    int(id_str)
                    for id_str in self.record_ids.split(",")
                    if id_str.strip()
                ]
                record = model.browse(ids)
                if not record:
                    raise UserError(_("The specified records do not exist."))
            elif self.record_id:
                # Single record
                record = model.browse(self.record_id)
                if not record.exists():
                    raise UserError(_("The specified record does not exist."))
            else:
                # No specific record (model method)
                record = model

            # Verify the method exists
            if not hasattr(record, self.method_name):
                raise UserError(
                    _('Method "%s" does not exist in model "%s".')
                    % (self.method_name, self.model_name)
                )

            # Prepare additional context if it exists
            context = dict(self.env.context)
            if self.context_data:
                import json

                try:
                    extra_context = json.loads(self.context_data)
                    context.update(extra_context)
                except:
                    pass

            # Execute the method
            _logger.info(
                f"Executing method {self.method_name} on model {self.model_name} with {len(record) if hasattr(record, '__len__') else 1} record(s)..."
            )
            method = getattr(record, self.method_name)
            result = method()

            # If the method returns an action, return it
            if isinstance(result, dict) and result.get("type"):
                return result

            # Otherwise, close the wizard
            return {"type": "ir.actions.act_window_close"}

        except Exception as e:
            _logger.error(f"Error during execution: {str(e)}")
            raise UserError(_("Error during execution: %s") % str(e))

    def action_cancel(self):
        """Cancels the wizard without making changes."""
        return {"type": "ir.actions.act_window_close"}
