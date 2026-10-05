from odoo import _, models
from odoo.exceptions import AccessError


class PosConfig(models.Model):
    _inherit = "pos.config"

    def action_delete_draft_orders(self):
        self.ensure_one()
        if not self.env.user.has_group("delete_draft_orders.group_delete_draft_orders"):
            raise AccessError(_("No tienes permiso para eliminar órdenes en borrador."))

        draft_orders = self.env["pos.order"].search(
            [
                ("config_id", "=", self.id),
                ("state", "=", "draft"),
            ]
        )
        count = len(draft_orders)
        if not count:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Sin órdenes"),
                    "message": _("No hay órdenes en borrador que borrar."),
                    "type": "warning",
                    "sticky": False,
                },
            }

        draft_orders.unlink()
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Órdenes eliminadas"),
                "message": _("%s orden(es) en borrador eliminada(s).") % count,
                "type": "success",
                "sticky": False,
            },
        }
