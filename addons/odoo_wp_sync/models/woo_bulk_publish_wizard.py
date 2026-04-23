"""
Bulk publish wizard for Odoo products → WooCommerce.

Opened from the "Publish to WooCommerce" action in the product.template
tree view. Receives the selected IDs via active_ids in the context.
"""

import logging
from odoo import models, fields, api, _

_logger = logging.getLogger(__name__)


class WooBulkPublishWizardLine(models.TransientModel):
    """One row per product — shows the price that will be sent to WooCommerce."""

    _name = "woo.bulk.publish.wizard.line"
    _description = "Bulk Publish Wizard - Product Line"

    wizard_id = fields.Many2one(
        "woo.bulk.publish.wizard",
        required=True,
        ondelete="cascade",
    )
    product_tmpl_id = fields.Many2one(
        "product.template",
        string="Product",
        required=True,
        readonly=True,
    )
    name = fields.Char(
        related="product_tmpl_id.name",
        string="Product",
        readonly=True,
    )
    default_code = fields.Char(
        related="product_tmpl_id.default_code",
        string="SKU",
        readonly=True,
    )
    base_price = fields.Float(
        related="product_tmpl_id.list_price",
        string="Base Price",
        digits=(16, 2),
        readonly=True,
    )
    pricelist_price = fields.Float(
        string="List Price",
        digits=(16, 2),
        readonly=True,
    )
    woo_price = fields.Float(
        string="WC Price (incl. VAT)",
        digits=(16, 2),
        readonly=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        readonly=True,
    )


class WooBulkPublishWizard(models.TransientModel):
    _name = "woo.bulk.publish.wizard"
    _description = "Bulk publish to WooCommerce"

    # Hidden field to retain original product IDs across onchange calls
    product_tmpl_ids = fields.Many2many(
        "product.template",
        string="Selected products (hidden)",
        readonly=True,
    )
    line_ids = fields.One2many(
        "woo.bulk.publish.wizard.line",
        "wizard_id",
        string="Products",
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

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _compute_line_vals(self, tmpl, instance):
        """Return the dict of values for one wizard line given an instance."""
        currency = (
            instance.pricelist_id.currency_id
            if instance and instance.pricelist_id
            else self.env.company.currency_id
        )

        variant = tmpl.product_variant_id

        _logger.debug(f"Variant {variant.id}")

        # Pricelist price
        if instance and instance.pricelist_id and variant and variant.id:
            try:
                price = (
                    instance.pricelist_id._get_product_price(variant, 1.0)
                    or tmpl.list_price
                )
            except Exception:
                price = tmpl.list_price
        else:
            price = tmpl.list_price

        # Apply IVA on top of pricelist price
        if (
            instance
            and instance.include_taxes_wc_product_sync
            and instance.taxes_product
            and price
        ):
            try:
                taxes_res = instance.taxes_product.compute_all(
                    price,
                    currency=currency,
                    quantity=1.0,
                    product=variant if variant and variant.id else None,
                    partner=None,
                )
                woo_price = taxes_res["total_included"]
            except Exception:
                woo_price = price
        else:
            woo_price = price

        return {
            "product_tmpl_id": tmpl.id,
            "pricelist_price": price,
            "woo_price": woo_price,
            "currency_id": currency.id,
        }

    # ── Defaults ───────────────────────────────────────────────────────────────

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        active_ids = self.env.context.get("active_ids", [])
        if not active_ids:
            return res
        tmpls = self.env["product.template"].browse(active_ids)
        currency = self.env.company.currency_id
        # Store product_tmpl_ids so onchange can rebuild lines
        res["product_tmpl_ids"] = [fields.Command.set(active_ids)]
        # Initial lines use list_price (no instance selected yet)
        res["line_ids"] = [
            (
                0,
                0,
                {
                    "product_tmpl_id": tmpl.id,
                    "pricelist_price": tmpl.list_price,
                    "woo_price": tmpl.list_price,
                    "currency_id": currency.id,
                },
            )
            for tmpl in tmpls
        ]
        return res

    # ── Computed ───────────────────────────────────────────────────────────────

    @api.depends("line_ids")
    def _compute_product_count(self):
        for wiz in self:
            wiz.product_count = len(wiz.line_ids)

    # ── Onchange ──────────────────────────────────────────────────────────────

    @api.onchange("instance_id")
    def _onchange_instance_id(self):
        """Rebuild all lines with prices from the selected instance."""
        instance = self.instance_id
        new_lines = [fields.Command.clear()]
        for tmpl in self.product_tmpl_ids:
            vals = self._compute_line_vals(tmpl, instance)
            new_lines.append((0, 0, vals))
        self.line_ids = new_lines

    # ── Action ────────────────────────────────────────────────────────────────

    def action_bulk_publish(self):
        """Publishes all selected products to the chosen instance."""
        self.ensure_one()
        sync = self.env["woo.product.sync"]
        success_count = 0
        errors = []

        for line in self.line_ids:
            tmpl = line.product_tmpl_id
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
