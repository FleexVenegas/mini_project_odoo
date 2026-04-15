"""
Bulk publish wizard for Odoo products → WooCommerce.

Opened from the "Publish to WooCommerce" action in the product.template
tree view. Receives the selected IDs via active_ids in the context.
"""

import logging
from odoo import models, fields, api, _

_logger = logging.getLogger(__name__)


class WooBulkPublishWizard(models.TransientModel):
    _name = "woo.bulk.publish.wizard"
    _description = "Bulk publish to WooCommerce"

    product_tmpl_ids = fields.Many2many(
        "product.template",
        string="Selected products",
        readonly=True,
    )
    product_count = fields.Integer(
        string="Total products",
        compute="_compute_product_count",
    )
    instance_id = fields.Many2one(
        "woo.instance",
        string="WooCommerce Instance",
        required=True,
        domain="[('allow_create_products', '=', True), ('who_can_publish', 'in', [uid])]",
        help="Only enabled instances where you have publishing permission.",
    )
    include_taxes_product = fields.Boolean(
        related="instance_id.include_taxes_wc_product_sync",
        string="Include taxes",
        readonly=True,
    )
    taxes_product = fields.Many2many(
        related="instance_id.taxes_product",
        string="Product taxes",
        readonly=True,
    )
    wc_status = fields.Selection(
        [
            ("draft", "Draft"),
            ("publish", "Published"),
        ],
        string="WooCommerce Status",
        default="draft",
        required=True,
        help="Status with which all products will be published in WooCommerce.",
    )

    # ── Defaults ───────────────────────────────────────────────────────────────

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        active_ids = self.env.context.get("active_ids", [])
        if active_ids and "product_tmpl_ids" in fields_list:
            res["product_tmpl_ids"] = [fields.Command.set(active_ids)]
        return res

    # ── Computed ───────────────────────────────────────────────────────────────

    @api.depends("product_tmpl_ids")
    def _compute_product_count(self):
        for wiz in self:
            wiz.product_count = len(wiz.product_tmpl_ids)

    # ── Action ────────────────────────────────────────────────────────────────

    def action_bulk_publish(self):
        """Publishes all selected products to the chosen instance."""
        self.ensure_one()
        sync = self.env["woo.product.sync"]
        success_count = 0
        errors = []

        for tmpl in self.product_tmpl_ids:
            try:
                sync.publish_to_wc(
                    product_tmpl=tmpl,
                    instance=self.instance_id,
                    wc_status=self.wc_status,
                )
                success_count += 1
                _logger.info(
                    "Bulk publish: '%s' → instance '%s'",
                    tmpl.name,
                    self.instance_id.name,
                )
            except Exception as e:
                errors.append(f"• {tmpl.name}: {e}")
                _logger.warning("Bulk publish error for '%s': %s", tmpl.name, e)

        title = _("Bulk publish completed")
        if errors:
            message = _(
                "%(ok)d published successfully in '%(instance)s'.\n"
                "%(fail)d with errors:\n%(errors)s"
            ) % {
                "ok": success_count,
                "instance": self.instance_id.name,
                "fail": len(errors),
                "errors": "\n".join(errors),
            }
            notif_type = "warning"
        else:
            message = _(
                "%(ok)d product(s) published successfully in '%(instance)s'."
            ) % {"ok": success_count, "instance": self.instance_id.name}
            notif_type = "success"

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": title,
                "message": message,
                "type": notif_type,
                "sticky": bool(errors),
            },
        }
