from odoo import models, fields


class WooInstanceWarehouse(models.Model):
    _name = "woo.instance"
    _inherit = "woo.instance"
    _description = "WooCommerce Instance - Warehouse Settings"

    # ── Warehouse ──────────────────────────────────────────────────────────────────────────
    warehouse_id = fields.Many2one(
        "stock.warehouse",
        string="Warehouse",
        help="Default warehouse for stock movements from synced orders",
    )

    manage_stock = fields.Boolean(
        string="Manage product stock",
        default=False,
        help="If active, allows managing WooCommerce product stock quantities directly from Odoo.",
    )

    # update_stock = fields.Boolean(
    #     string="Update Stock",
    #     default=False,
    #     help="If active, stock will be updated in WooCommerce when syncing orders",
    # )

    update_order_status_wc = fields.Boolean(
        string="Update order status in WooCommerce",
        default=False,
        help="If active, the order status in WooCommerce will be updated during sync (e.g. to 'processing' or 'completed' based on status configuration)",
    )

    # min_stock_threshold = fields.Integer(
    #     string="Minimum stock threshold",
    #     default=0,
    #     help="Minimum stock quantity for a product. If available stock is equal to or below this threshold, it will be marked as 'out of stock' in WooCommerce (if 'Update Stock' is active).",
    # )

    # max_stock_threshold = fields.Integer(
    #     string="Maximum stock threshold",
    #     default=0,
    #     help="Maximum stock quantity for a product. If available stock is equal to or above this threshold, it will be marked as 'in stock' in WooCommerce (if 'Update Stock' is active).",
    # )

    picking_policy = fields.Selection(
        selection=[
            ("direct", "As soon as possible"),
            ("one", "When all products are ready"),
        ],
        default="one",
        help="Determines when the order should be marked as ready for delivery: 'As soon as possible' will create a delivery as soon as any product is available, while 'When all products are ready' will wait until all products in the order are available before creating the delivery.",
    )

    # We use this file for products
    allow_create_products = fields.Boolean(
        string="Allow product creation",
        default=False,
        help="If active, Odoo products can be created in WooCommerce",
    )

    who_can_publish = fields.Many2many(
        "res.users",
        string="Allow publishing",
        help="Users allowed to publish products in WooCommerce",
    )

    include_taxes_wc_product_sync = fields.Boolean(
        string="Include taxes when creating products",
        default=False,
        help="If active, taxes will be included when creating products in WooCommerce",
    )

    taxes_product = fields.Many2many(
        "account.tax",
        relation="woo_instance_taxes_product_rel",
        column1="instance_id",
        column2="tax_id",
        string="Product taxes",
        help="Taxes assigned to products created in WooCommerce (if 'Include taxes when creating products' is active)",
    )
