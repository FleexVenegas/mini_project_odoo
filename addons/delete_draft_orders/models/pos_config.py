from odoo import _, models


class PosConfig(models.Model):
    _inherit = "pos.config"

    def action_delete_draft_orders(self):
        self.ensure_one()
        draft_orders = self.env["pos.order"].search(
            [
                ("config_id", "=", self.id),
                ("state", "=", "draft"),
            ]
        )
        count = len(draft_orders)
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
