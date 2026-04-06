"""
Wizard de publicación masiva de productos Odoo → WooCommerce.

Se abre desde la acción "Publicar en WooCommerce" en la vista árbol de
product.template. Recibe los IDs seleccionados via active_ids en el contexto.
"""

import logging
from odoo import models, fields, api, _

_logger = logging.getLogger(__name__)


class WooBulkPublishWizard(models.TransientModel):
    _name = "woo.bulk.publish.wizard"
    _description = "Publicación masiva en WooCommerce"

    product_tmpl_ids = fields.Many2many(
        "product.template",
        string="Productos seleccionados",
        readonly=True,
    )
    product_count = fields.Integer(
        string="Total de productos",
        compute="_compute_product_count",
    )
    instance_id = fields.Many2one(
        "woo.instance",
        string="Instancia WooCommerce",
        required=True,
        domain="[('allow_create_products', '=', True), ('who_can_publish', 'in', [uid])]",
        help="Solo instancias habilitadas y en las que tienes permiso de publicación.",
    )
    wc_status = fields.Selection(
        [
            ("draft", "Borrador"),
            ("publish", "Publicado"),
        ],
        string="Estado en WooCommerce",
        default="draft",
        required=True,
        help="Estado con el que se publicarán todos los productos en WooCommerce.",
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

    # ── Acción ─────────────────────────────────────────────────────────────────

    def action_bulk_publish(self):
        """Publica todos los productos seleccionados en la instancia elegida."""
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

        title = _("Publicación masiva completada")
        if errors:
            message = _(
                "%(ok)d publicados correctamente en '%(instance)s'.\n"
                "%(fail)d con errores:\n%(errors)s"
            ) % {
                "ok": success_count,
                "instance": self.instance_id.name,
                "fail": len(errors),
                "errors": "\n".join(errors),
            }
            notif_type = "warning"
        else:
            message = _(
                "%(ok)d producto(s) publicados correctamente en '%(instance)s'."
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
