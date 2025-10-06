from odoo import models, _
from odoo.exceptions import UserError

import logging

_logger = logging.getLogger(__name__)


class ConfirmQuotes(models.Model):
    _inherit = "sale.order"
    _description = "Extend Sale Order to confirm multiple quotations"

    def action_confirm_multiple(self):
        """Confirm multiple selected quotations"""
        if not self:
            raise UserError(_("No quotations selected."))

        # Check permissions - allow both sales manager and sales user
        if not (
            self.env.user.has_group("sales_team.group_sale_salesman")
            or self.env.user.has_group("sales_team.group_sale_manager")
        ):
            raise UserError(_("You don't have permission to confirm quotations."))

        confirmed_count = 0
        error_count = 0
        errors = []

        for order in self:
            try:
                # Only confirm if in draft state
                if order.state == "draft":
                    order.action_confirm()
                    confirmed_count += 1
                    _logger.info(_("Quotation %s confirmed successfully") % order.name)
                else:
                    error_count += 1
                    state_translation = {
                        "draft": _("Quotation"),
                        "sent": _("Quotation Sent"),
                        "sale": _("Sales Order"),
                        "done": _("Done"),
                        "cancel": _("Cancelled"),
                    }
                    current_state = state_translation.get(order.state, order.state)
                    errors.append(
                        _(
                            "%s: Cannot confirm - current state is '%s' (must be 'Quotation')"
                        )
                        % (order.name, current_state)
                    )
            except Exception as e:
                error_count += 1
                errors.append(_("%s: Error - %s") % (order.name, str(e)))
                _logger.error(
                    _("Error confirming quotation %s: %s") % (order.name, str(e))
                )

        # Build main message
        if confirmed_count > 0 and error_count == 0:
            if confirmed_count == 1:
                main_message = _("✅ 1 quotation confirmed successfully")
            else:
                main_message = (
                    _("✅ %d quotations confirmed successfully") % confirmed_count
                )
            message_type = "success"

        elif confirmed_count > 0 and error_count > 0:
            if confirmed_count == 1:
                main_message = _("✅ 1 quotation confirmed")
            else:
                main_message = _("✅ %d quotations confirmed") % confirmed_count
            message_type = "warning"

        else:
            # All failed
            main_message = _("🔵 No quotations were confirmed")
            message_type = "info"

        # Add error summary if exists
        if error_count > 0:
            if error_count == 1:
                error_summary = _("🔵 1 quotation failed")
            else:
                error_summary = _("🔵 %d quotations failed") % error_count
        else:
            error_summary = ""

        # Add reload hint if there were successes
        reload_hint = (
            _("🔄 Please reload the page to see updated status")
            if confirmed_count >= 1
            else ""
        )

        # Build final message
        message_lines = [main_message]
        if error_summary:
            message_lines.append(error_summary)
        if reload_hint:
            message_lines.append(reload_hint)

        # Add error details (maximum 3 to avoid saturation)
        if errors and error_count <= 3:
            message_lines.append(_("\nDetails:"))
            message_lines.extend(errors[:3])
        elif errors and error_count > 3:
            message_lines.append(_("\nFirst %d errors of %d:") % (3, error_count))
            message_lines.extend(errors[:3])
            message_lines.append(_("... and %d more") % (error_count - 3))

        message = "\n".join(message_lines)

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Mass Quotation Confirmation"),
                "message": message,
                "type": message_type,
                "sticky": error_count > 0,  # Sticky only if there are errors
            },
        }
