"""
WooCommerce Coupon model for Odoo WP Sync.

Stores coupons synced from WooCommerce instances.
"""

import logging
import json
from datetime import datetime

from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class WooCoupon(models.Model):
    _name = "woo.coupon"
    _description = "WooCommerce Coupon"
    _order = "code"
    _rec_name = "code"

    # ── WooCommerce Identity ──────────────────────────────────────────────────

    instance_id = fields.Many2one(
        "woo.instance",
        string="Instance",
        required=True,
        ondelete="cascade",
        index=True,
    )
    woo_id = fields.Integer(
        string="WooCommerce ID",
        index=True,
        default=0,
        help="Numeric ID of the coupon in WooCommerce (0 = not yet created in WC)",
    )

    # ── Coupon Basic Info ─────────────────────────────────────────────────────

    code = fields.Char(
        string="Coupon Code",
        required=True,
        index=True,
        help="The unique coupon code customers will enter",
    )
    description = fields.Text(
        string="Description",
        help="Coupon description for internal reference",
    )
    status = fields.Selection(
        [
            ("publish", "Published"),
            ("draft", "Draft"),
            ("pending", "Pending"),
            ("private", "Private"),
        ],
        string="Status",
        default="publish",
        required=True,
    )

    # ── Discount Configuration ────────────────────────────────────────────────

    discount_type = fields.Selection(
        [
            ("percent", "Percentage Discount"),
            ("fixed_cart", "Fixed Cart Discount"),
            ("fixed_product", "Fixed Product Discount"),
        ],
        string="Discount Type",
        default="fixed_cart",
        required=True,
    )
    amount = fields.Float(
        string="Amount",
        digits=(16, 2),
        help="The amount of discount. Should always be a positive number. "
        "For percentage discounts, enter a number without the % symbol.",
    )

    # ── Usage Restrictions ────────────────────────────────────────────────────

    individual_use = fields.Boolean(
        string="Individual Use Only",
        default=True,
        help="If true, this coupon cannot be used in conjunction with other coupons",
    )
    exclude_sale_items = fields.Boolean(
        string="Exclude Sale Items",
        default=False,
        help="If true, this coupon will not apply to items on sale",
    )
    minimum_amount = fields.Float(
        string="Minimum Spend",
        digits=(16, 2),
        help="Minimum order total required to use this coupon",
    )
    maximum_amount = fields.Float(
        string="Maximum Spend",
        digits=(16, 2),
        help="Maximum order total allowed to use this coupon",
    )

    # ── Product Restrictions ──────────────────────────────────────────────────

    product_ids = fields.Many2many(
        "woo.product",
        "woo_coupon_product_rel",
        "coupon_id",
        "product_id",
        string="Products",
        help="WooCommerce products this coupon applies to (leave empty = all products)",
    )
    excluded_product_ids = fields.Many2many(
        "woo.product",
        "woo_coupon_excluded_product_rel",
        "coupon_id",
        "product_id",
        string="Excluded Products",
        help="WooCommerce products excluded from this coupon",
    )
    product_category_ids = fields.Many2many(
        "woo.category",
        "woo_coupon_category_rel",
        "coupon_id",
        "category_id",
        string="Categories",
        help="WooCommerce categories this coupon applies to (leave empty = all categories)",
    )
    excluded_category_ids = fields.Many2many(
        "woo.category",
        "woo_coupon_excluded_category_rel",
        "coupon_id",
        "category_id",
        string="Excluded Categories",
        help="WooCommerce categories excluded from this coupon",
    )

    # ── Usage Limits ──────────────────────────────────────────────────────────

    usage_limit = fields.Integer(
        string="Usage Limit",
        default=0,
        help="How many times this coupon can be used in total (0 = unlimited)",
    )
    usage_limit_per_user = fields.Integer(
        string="Usage Limit Per User",
        default=0,
        help="How many times this coupon can be used by a single user (0 = unlimited)",
    )
    usage_count = fields.Integer(
        string="Usage Count",
        readonly=True,
        default=0,
        help="Number of times this coupon has been used",
    )

    # ── Dates ─────────────────────────────────────────────────────────────────

    date_expires = fields.Datetime(
        string="Expiry Date",
        help="The date the coupon expires. Leave empty for no expiry.",
    )
    date_start = fields.Date(
        string="Start Date",
        help="The date the coupon becomes active",
    )

    # ── Shipping ──────────────────────────────────────────────────────────────

    free_shipping = fields.Boolean(
        string="Free Shipping",
        default=False,
        help="If true, this coupon grants free shipping",
    )

    # ── Meta Data ─────────────────────────────────────────────────────────────

    meta_data_json = fields.Text(
        string="Meta Data (JSON)",
        default="[]",
        help="Additional WooCommerce meta data as JSON",
    )
    availability_ids = fields.Many2many(
        "woo.coupon.location",
        "woo_coupon_location_rel",
        "coupon_id",
        "location_id",
        string="Available At",
        help="Where customers can apply this coupon",
    )
    apply_before_tax = fields.Boolean(
        string="Apply Before Tax",
        default=True,
        help="Apply discount before tax calculation",
    )
    auto_coupon = fields.Boolean(
        string="Auto Apply Coupon",
        default=False,
        help="Automatically apply this coupon when conditions are met",
    )
    enable_category_restriction = fields.Boolean(
        string="Enable Category Restriction",
        default=False,
        help="Enable product category restriction for this coupon",
    )

    # ── Sync Info ─────────────────────────────────────────────────────────────

    last_sync_date = fields.Datetime(
        string="Last Sync",
        readonly=True,
        help="Last time this coupon was synced with WooCommerce",
    )
    pending_sync = fields.Boolean(
        string="Pending Sync",
        default=False,
        help="A change was made in Odoo and has not been synced to WooCommerce yet",
    )

    # ── Computed Fields ───────────────────────────────────────────────────────

    is_expired = fields.Boolean(
        string="Is Expired",
        compute="_compute_is_expired",
        store=True,
    )
    display_discount = fields.Char(
        string="Discount Display",
        compute="_compute_display_discount",
    )

    # ── SQL Constraints ───────────────────────────────────────────────────────

    _sql_constraints = [
        (
            "unique_code_per_instance",
            "UNIQUE(instance_id, code)",
            "Coupon code must be unique per instance!",
        ),
    ]

    # ── ORM Overrides ──────────────────────────────────────────────────────────

    # Fields that, when changed, should flag the coupon as pending sync
    _SYNC_TRACKED_FIELDS = {
        "code",
        "status",
        "discount_type",
        "amount",
        "description",
        "individual_use",
        "exclude_sale_items",
        "free_shipping",
        "minimum_amount",
        "maximum_amount",
        "usage_limit",
        "usage_limit_per_user",
        "date_expires",
        "date_start",
        "apply_before_tax",
        "auto_coupon",
        "enable_category_restriction",
        "availability_ids",
        "product_ids",
        "excluded_product_ids",
        "product_category_ids",
        "excluded_category_ids",
    }

    def write(self, vals):
        if not self.env.context.get("skip_pending_sync") and (
            self._SYNC_TRACKED_FIELDS & set(vals.keys())
        ):
            vals["pending_sync"] = True
        return super().write(vals)

    # ── Computed Methods ──────────────────────────────────────────────────────

    @api.depends("date_expires")
    def _compute_is_expired(self):
        now = fields.Datetime.now()
        for coupon in self:
            coupon.is_expired = coupon.date_expires and coupon.date_expires < now

    @api.depends("discount_type", "amount")
    def _compute_display_discount(self):
        for coupon in self:
            if coupon.discount_type == "percent":
                coupon.display_discount = f"{coupon.amount}%"
            else:
                coupon.display_discount = f"${coupon.amount:.2f}"

    # ── Helper Methods ─────────────────────────────────────────────────────────

    def _product_woo_ids(self, products):
        """Return list of WooCommerce IDs from a woo.product recordset."""
        return [p.woo_id for p in products if p.woo_id]

    def _category_woo_ids(self, categories):
        """Return list of WooCommerce IDs from a woo.category recordset."""
        return [c.woo_id for c in categories if c.woo_id]

    def get_meta_data(self):
        """Return meta data as a Python list."""
        self.ensure_one()
        try:
            return json.loads(self.meta_data_json or "[]")
        except json.JSONDecodeError:
            return []

    def set_meta_data(self, meta_list):
        """Set meta data from a Python list."""
        self.ensure_one()
        self.meta_data_json = json.dumps(meta_list)
        # Parse known meta keys
        for meta in meta_list:
            key = meta.get("key", "")
            value = meta.get("value", "")
            if key == "_wc_make_coupon_available":
                locations = [v.strip() for v in value.split(",") if v.strip()]
                location_records = self.env["woo.coupon.location"].search(
                    [("code", "in", locations)]
                )
                self.availability_ids = [(6, 0, location_records.ids)]
            elif key == "_wt_coupon_start_date":
                if value:
                    try:
                        self.date_start = datetime.strptime(value, "%Y-%m-%d").date()
                    except ValueError:
                        pass
            elif key == "wt_apply_discount_before_tax_calculation":
                self.apply_before_tax = value == "1"
            elif key == "_wt_make_auto_coupon":
                self.auto_coupon = bool(value)
            elif key == "_wt_enable_product_category_restriction":
                self.enable_category_restriction = value == "yes"

    # ── WooCommerce Sync Methods ──────────────────────────────────────────────

    def to_woo_data(self):
        """Convert record to WooCommerce API format."""
        self.ensure_one()
        data = {
            "code": self.code,
            "discount_type": self.discount_type,
            "amount": str(self.amount),
            "status": self.status,
            "description": self.description or "",
            "individual_use": self.individual_use,
            "exclude_sale_items": self.exclude_sale_items,
            "free_shipping": self.free_shipping,
        }

        if self.usage_limit:
            data["usage_limit"] = self.usage_limit
        if self.usage_limit_per_user:
            data["usage_limit_per_user"] = self.usage_limit_per_user
        if self.minimum_amount:
            data["minimum_amount"] = str(self.minimum_amount)
        if self.maximum_amount:
            data["maximum_amount"] = str(self.maximum_amount)
        if self.date_expires:
            data["date_expires"] = self.date_expires.isoformat()

        # Many2many → lista de woo_id para la API de WooCommerce
        data["product_ids"] = self._product_woo_ids(self.product_ids)
        data["excluded_product_ids"] = self._product_woo_ids(self.excluded_product_ids)
        data["product_categories"] = self._category_woo_ids(self.product_category_ids)
        data["excluded_product_categories"] = self._category_woo_ids(
            self.excluded_category_ids
        )

        # Meta data: construido desde los campos del modelo, no desde JSON
        meta_data = []
        locations = ",".join(loc.code for loc in self.availability_ids)
        meta_data.append(
            {
                "key": "_wc_make_coupon_available",
                "value": locations,
            }
        )
        if self.date_start:
            meta_data.append(
                {
                    "key": "_wt_coupon_start_date",
                    "value": str(self.date_start),
                }
            )
        meta_data.append(
            {
                "key": "wt_apply_discount_before_tax_calculation",
                "value": "1" if self.apply_before_tax else "0",
            }
        )
        meta_data.append(
            {
                "key": "_wt_make_auto_coupon",
                "value": "yes" if self.auto_coupon else "",
            }
        )
        meta_data.append(
            {
                "key": "_wt_enable_product_category_restriction",
                "value": "yes" if self.enable_category_restriction else "no",
            }
        )
        data["meta_data"] = meta_data

        return data

    @api.model
    def from_woo_data(self, instance, data):
        """Create or update coupon from WooCommerce API data."""
        woo_id = data.get("id")
        coupon = self.search(
            [
                ("instance_id", "=", instance.id),
                ("woo_id", "=", woo_id),
            ],
            limit=1,
        )

        vals = {
            "instance_id": instance.id,
            "woo_id": woo_id,
            "code": data.get("code", ""),
            "description": data.get("description", ""),
            "status": data.get("status", "publish"),
            "discount_type": data.get("discount_type", "fixed_cart"),
            "amount": float(data.get("amount", 0)),
            "individual_use": data.get("individual_use", False),
            "exclude_sale_items": data.get("exclude_sale_items", False),
            "free_shipping": data.get("free_shipping", False),
            "usage_limit": data.get("usage_limit") or 0,
            "usage_limit_per_user": data.get("usage_limit_per_user") or 0,
            "usage_count": data.get("usage_count", 0),
            "minimum_amount": float(data.get("minimum_amount", 0) or 0),
            "maximum_amount": float(data.get("maximum_amount", 0) or 0),
            "last_sync_date": fields.Datetime.now(),
        }

        # Relacionar productos incluidos por woo_id
        wc_product_ids = data.get("product_ids", [])
        if wc_product_ids:
            products = self.env["woo.product"].search(
                [
                    ("instance_id", "=", instance.id),
                    ("woo_id", "in", wc_product_ids),
                ]
            )
            vals["product_ids"] = [(6, 0, products.ids)]

        # Relacionar productos excluidos por woo_id
        wc_excluded_ids = data.get("excluded_product_ids", [])
        if wc_excluded_ids:
            excluded = self.env["woo.product"].search(
                [
                    ("instance_id", "=", instance.id),
                    ("woo_id", "in", wc_excluded_ids),
                ]
            )
            vals["excluded_product_ids"] = [(6, 0, excluded.ids)]

        # Relacionar categorías incluidas por woo_id
        wc_category_ids = data.get("product_categories", [])
        if wc_category_ids:
            categories = self.env["woo.category"].search(
                [
                    ("instance_id", "=", instance.id),
                    ("woo_id", "in", wc_category_ids),
                ]
            )
            vals["product_category_ids"] = [(6, 0, categories.ids)]

        # Relacionar categorías excluidas por woo_id
        wc_excluded_cats = data.get("excluded_product_categories", [])
        if wc_excluded_cats:
            excluded_cats = self.env["woo.category"].search(
                [
                    ("instance_id", "=", instance.id),
                    ("woo_id", "in", wc_excluded_cats),
                ]
            )
            vals["excluded_category_ids"] = [(6, 0, excluded_cats.ids)]

        # Date expires
        date_expires = data.get("date_expires")
        if date_expires:
            try:
                vals["date_expires"] = datetime.fromisoformat(
                    date_expires.replace("Z", "+00:00")
                )
            except ValueError:
                pass

        if coupon:
            coupon.write(vals)
        else:
            coupon = self.create(vals)

        # Process meta data
        meta_data = data.get("meta_data", [])
        if meta_data:
            coupon.set_meta_data(meta_data)

        return coupon

    def action_sync_to_woocommerce(self):
        """Push coupon to WooCommerce."""
        self.ensure_one()
        service = self.env["woo.service"]
        data = self.to_woo_data()

        # raise UserError(
        #     f"Payload {data} for coupon '{self.code}' (ID: {self.id}) is ready to be sent to WooCommerce. "
        # )
        if self.woo_id:

            result = service._request(
                f"coupons/{self.woo_id}",
                method="PUT",
                data=data,
                instance=self.instance_id,
            )
        else:
            result = service._request(
                "coupons", method="POST", data=data, instance=self.instance_id
            )
            if result.get("id"):
                self.woo_id = result["id"]

        self.with_context(skip_pending_sync=True).write(
            {
                "last_sync_date": fields.Datetime.now(),
                "pending_sync": False,
            }
        )
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Success"),
                "message": _("Coupon synced to WooCommerce"),
                "type": "success",
                "next": {"type": "ir.actions.client", "tag": "reload"},
            },
        }

    def action_confirm_delete_from_woocommerce(self):
        """Open confirmation wizard before deleting coupon from WooCommerce."""
        self.ensure_one()
        if not self.woo_id:
            raise UserError(_("This coupon has not been synced to WooCommerce yet."))
        return self.env["confirmation.wizard"].create_confirmation(
            model_name="woo.coupon",
            method_name="action_delete_from_woocommerce",
            title=_("Delete from WooCommerce"),
            description=_(
                "Are you sure you want to delete coupon <strong>%s</strong> from WooCommerce?<br/>"
                "This action cannot be undone. The coupon record in Odoo will be kept."
            )
            % self.code,
            record_id=self.id,
            dialog_size="small",
        )

    def action_delete_from_woocommerce(self):
        """Delete coupon from WooCommerce (called by confirmation wizard)."""
        self.ensure_one()
        if not self.woo_id:
            raise UserError(_("This coupon has not been synced to WooCommerce yet."))

        try:
            self.env["woo.service"]._request(
                f"coupons/{self.woo_id}",
                method="DELETE",
                data={"force": True},
                instance=self.instance_id,
            )
        except Exception as e:
            # WooCommerce may return 500 after a successful deletion or if the
            # coupon no longer exists there. We log the warning and continue.
            _logger.warning(
                "WooCommerce returned an error while deleting coupon %s (woo_id=%s): %s",
                self.code,
                self.woo_id,
                e,
            )

        self.with_context(skip_pending_sync=True).write(
            {"woo_id": False, "pending_sync": False}
        )
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Deleted"),
                "message": _("Coupon removed from WooCommerce"),
                "type": "success",
                "next": {"type": "ir.actions.client", "tag": "reload"},
            },
        }
