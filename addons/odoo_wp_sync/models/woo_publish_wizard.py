"""
Wizard to selectively publish an Odoo product to a WooCommerce instance.

The user chooses:
  - The target WooCommerce instance.
  - The initial status (draft / published).
  - Optionally overrides the price.
"""

from odoo import models, fields, api
from odoo.exceptions import UserError


class WooPublishWizard(models.TransientModel):
    _name = "woo.publish.wizard"
    _description = "Publish product to WooCommerce"

    product_tmpl_id = fields.Many2one(
        "product.template",
        string="Product",
        required=True,
        readonly=True,
    )
    product_name = fields.Char(
        related="product_tmpl_id.name",
        string="Product name",
        readonly=True,
    )
    product_sku = fields.Char(
        related="product_tmpl_id.default_code",
        string="Internal reference (SKU)",
        readonly=True,
    )
    product_price = fields.Float(
        related="product_tmpl_id.list_price",
        string="List price",
        readonly=True,
    )
    instance_id = fields.Many2one(
        "woo.instance",
        string="WooCommerce Instance",
        required=True,
        domain="[('allow_create_products', '=', True), ('who_can_publish', 'in', [uid])]",
        help="Only enabled instances where you have publishing permission.",
    )
    wc_status = fields.Selection(
        [
            ("draft", "Draft"),
            ("publish", "Published"),
        ],
        string="WooCommerce Status",
        default="draft",
        required=True,
        help="'Draft' creates the product in WC without publishing it in the store.",
    )
    price_override = fields.Float(
        string="Override price",
        digits=(16, 4),
        help="Leave at 0 to use the price from the pricelist configured in the instance (or the list price if no pricelist is configured).",
    )
    pricelist_id = fields.Many2one(
        related="instance_id.pricelist_id",
        string="Pricelist (Instance)",
        readonly=True,
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
    pricelist_price = fields.Float(
        string="Price per list",
        compute="_compute_pricelist_price",
        digits=(16, 4),
        readonly=True,
    )

    @api.depends("instance_id", "product_tmpl_id")
    def _compute_pricelist_price(self):
        for wiz in self:
            if wiz.instance_id.pricelist_id and wiz.product_tmpl_id:
                product = wiz.product_tmpl_id.product_variant_id
                wiz.pricelist_price = (
                    wiz.instance_id.pricelist_id._get_product_price(product, 1.0)
                    or wiz.product_tmpl_id.list_price
                )
            else:
                wiz.pricelist_price = (
                    wiz.product_tmpl_id.list_price if wiz.product_tmpl_id else 0.0
                )

    description = fields.Text(
        string="Description",
        # related="product_tmpl_id.description_sale",
        # readonly=True,
    )

    def action_publish(self):
        """Sends the product to WooCommerce and closes the wizard."""
        self.ensure_one()

        self.env["woo.product.sync"].publish_to_wc(
            product_tmpl=self.product_tmpl_id,
            instance=self.instance_id,
            wc_status=self.wc_status,
            price_override=self.price_override,
            description=self.description,
        )
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Published to WooCommerce",
                "message": (
                    f"'{self.product_tmpl_id.name}' was sent to "
                    f"'{self.instance_id.name}' as '{self.wc_status}'."
                ),
                "type": "success",
                "sticky": False,
                "next": {"type": "ir.actions.act_window_close"},
            },
        }
