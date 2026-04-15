"""
Mapping model between Odoo products and WooCommerce products.

One row = one WooCommerce product in a specific instance.
If product_tmpl_id is set → the product is linked to Odoo.
If product_tmpl_id is empty → the product exists in WC but not in Odoo.

product.template is not modified directly: this allows handling
multiple WooCommerce instances with the same Odoo catalog without
adding extra fields to the core product model.
"""

import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class WooProduct(models.Model):
    _name = "woo.product"
    _description = "WooCommerce Product Mapping"
    _order = "instance_id, woo_id"
    _rec_name = "woo_name"

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
        help="Numeric ID of the product in WooCommerce (0 = not yet created in WC)",
    )
    woo_name = fields.Char(string="Name in WC")
    woo_sku = fields.Char(string="SKU in WC", index=True)
    woo_status = fields.Selection(
        [
            ("draft", "Draft"),
            ("pending", "Pending"),
            ("publish", "Published"),
            ("private", "Private"),
        ],
        string="WC Status",
        default="draft",
    )
    woo_type = fields.Char(
        string="WC Type",
        default="simple",
        help="WooCommerce product type: simple, variable, grouped, external",
    )
    woo_price = fields.Float(string="WC Price", readonly=True, digits=(16, 4))

    # ── Fields for manual creation in WC ─────────────────────────────────────

    woo_price_input = fields.Float(
        string="Publish price",
        digits=(16, 4),
        help="Price to be sent to WooCommerce. If 0, the instance pricelist is used.",
    )
    pricelist_id = fields.Many2one(
        related="instance_id.pricelist_id",
        string="Pricelist (instance)",
        readonly=True,
    )
    pricelist_price = fields.Float(
        string="Price per list",
        compute="_compute_pricelist_price",
        digits=(16, 4),
    )
    woo_permalink = fields.Char(string="URL in WC", readonly=True)

    instance_manage_stock = fields.Boolean(
        related="instance_id.manage_stock",
        string="Active stock management",
        store=False,
    )

    woo_min_stock = fields.Float(
        string="Minimum stock",
        digits=(16, 0),
        help="Minimum stock quantity before marking as out of stock in WooCommerce.",
    )
    woo_max_stock = fields.Float(
        string="Maximum stock",
        digits=(16, 0),
        help="Maximum stock quantity allowed in WooCommerce.",
    )

    stock_status = fields.Selection(
        [
            ("instock", "In stock"),
            ("outofstock", "Out of stock"),
            ("onbackorder", "On backorder"),
        ],
        string="Stock status",
        help="Availability status shown in the WooCommerce store.",
    )

    stock_quantity = fields.Float(
        string="Quantity in stock", digits=(16, 0), help="Available stock quantity."
    )

    # ── Link with Odoo ───────────────────────────────────────────────────────

    product_tmpl_id = fields.Many2one(
        "product.template",
        string="Product in Odoo",
        ondelete="set null",
        index=True,
        help="Odoo product linked to this WooCommerce record. " "Empty = not linked.",
    )
    link_state = fields.Selection(
        [
            ("linked", "Linked"),
            ("unlinked", "Unlinked"),
        ],
        string="Link status",
        compute="_compute_link_state",
        store=True,
        index=True,
    )

    # ── Image ─────────────────────────────────────────────────────────────────

    woo_image = fields.Binary(
        string="Image",
        attachment=True,
        help="Product image. Legacy: no longer used for display or sync.",
    )
    woo_image_src = fields.Char(
        string="Image URL in WC",
        readonly=True,
        help="URL of the image currently published in WooCommerce.",
    )
    woo_image_id = fields.Integer(
        string="Image ID in WC",
        readonly=True,
        help="Media ID in the WordPress Media Library.",
    )
    woo_image_url_input = fields.Char(
        string="New image URL",
        help="Paste here the URL of the image you want to send to WooCommerce. "
        "WooCommerce will download it directly from that URL. "
        "No image is stored in Odoo.",
    )
    woo_image_preview = fields.Html(
        string="Current image",
        compute="_compute_woo_image_preview",
        sanitize=False,
        store=False,
    )

    # ── Categories and brands ───────────────────────────────────────────────

    woo_category_ids = fields.Many2many(
        "woo.category",
        string="WooCommerce Categories",
        domain="[('instance_id', '=', instance_id)]",
        help="WooCommerce product categories. "
        "Respects parent/child hierarchy. Only those from the instance are listed.",
    )
    woo_brand_ids = fields.Many2many(
        "woo.brand",
        string="Marcas WooCommerce",
        domain="[('instance_id', '=', instance_id)]",
        help="Marcas del producto en WooCommerce (requiere plugin de marcas en WC).",
    )

    # ── Audit ────────────────────────────────────────────────────────────────

    last_sync_date = fields.Datetime(string="Last sync", readonly=True)
    woo_pending_sync = fields.Boolean(
        string="Pending sync",
        default=False,
        help="Marked automatically when a bulk import changes synchronized fields "
        "(woo_status, stock_status, price) so they can be sent to WooCommerce "
        "later using the 'Sync to WooCommerce' action.",
    )

    _sql_constraints = (
        []
    )  # Uniqueness is validated in Python to allow provisional woo_id=0

    def init(self):
        """Removes the legacy SQL constraint to allow multiple pending records (woo_id=0)."""
        super().init()
        self._cr.execute(
            "ALTER TABLE woo_product DROP CONSTRAINT IF EXISTS woo_product_woo_id_instance_unique"
        )

    # ── Computed ────────────────────────────────────────────────────────────────

    @api.depends("product_tmpl_id")
    def _compute_link_state(self):
        for rec in self:
            rec.link_state = "linked" if rec.product_tmpl_id else "unlinked"

    @api.depends("woo_image_src")
    def _compute_woo_image_preview(self):
        for rec in self:
            if rec.woo_image_src:
                rec.woo_image_preview = (
                    f'<img src="{rec.woo_image_src}" '
                    f'style="max-width:160px;max-height:160px;object-fit:contain;border-radius:4px;"/>'
                )
            else:
                rec.woo_image_preview = ""

    @api.depends("instance_id.pricelist_id", "product_tmpl_id")
    def _compute_pricelist_price(self):
        for rec in self:
            if rec.instance_id.pricelist_id and rec.product_tmpl_id:
                product = rec.product_tmpl_id.product_variant_id
                rec.pricelist_price = (
                    rec.instance_id.pricelist_id._get_product_price(product, 1.0)
                    or rec.product_tmpl_id.list_price
                )
            elif rec.product_tmpl_id:
                rec.pricelist_price = rec.product_tmpl_id.list_price
            else:
                rec.pricelist_price = 0.0

    @api.constrains("instance_id")
    def _check_instance_connected(self):
        for rec in self:
            if rec.instance_id and rec.instance_id.state != "connected":
                raise ValidationError(
                    _(
                        "Instance '%s' is not connected. "
                        "Complete the configuration and verify the connection before creating products."
                    )
                    % rec.instance_id.name
                )

    @api.constrains("woo_id", "instance_id")
    def _check_woo_id_unique(self):
        for rec in self:
            if rec.woo_id:  # Solo validar cuando el producto ya existe en WC
                duplicate = self.search(
                    [
                        ("woo_id", "=", rec.woo_id),
                        ("instance_id", "=", rec.instance_id.id),
                        ("id", "!=", rec.id),
                    ],
                    limit=1,
                )
                if duplicate:
                    raise ValidationError(
                        _(
                            "WooCommerce product (ID=%s) already exists for instance '%s'."
                        )
                        % (rec.woo_id, rec.instance_id.name)
                    )

    @api.onchange("instance_id", "product_tmpl_id")
    def _onchange_prefill_from_template(self):
        """Auto-fills name, SKU and price when the Odoo product is selected."""
        if self.product_tmpl_id and not self.woo_id:
            if not self.woo_name:
                self.woo_name = self.product_tmpl_id.name
            if not self.woo_sku:
                self.woo_sku = self.product_tmpl_id.default_code or ""
            # Calcular precio desde la lista de la instancia
            if self.instance_id and self.instance_id.pricelist_id:
                product = self.product_tmpl_id.product_variant_id
                self.woo_price_input = (
                    self.instance_id.pricelist_id._get_product_price(product, 1.0)
                    or self.product_tmpl_id.list_price
                )
            else:
                self.woo_price_input = self.product_tmpl_id.list_price

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _build_categories_payload(self):
        """
        Returns the list of categories in the format expected by the WooCommerce API.

        WooCommerce expects: ``[{"id": 157}, {"id": 89}]``
        Only categories that already have a ``woo_id`` are included.
        """
        return [{"id": cat.woo_id} for cat in self.woo_category_ids if cat.woo_id]

    def _build_brands_payload(self):
        """
        Returns the list of brands in the format expected by the WooCommerce API.

        WooCommerce expects: ``[{"id": 121880}]``
        Only brands that already have a ``woo_id`` are included.
        """
        return [{"id": brand.woo_id} for brand in self.woo_brand_ids if brand.woo_id]

    def _upload_image_to_wp(self):
        """Uploads the binary image to the WordPress Media Library via woo.service.

        Returns:
            tuple(int|None, str): (media_id, src_url) or (None, '') if it fails.
        """
        self.ensure_one()
        if not self.woo_image:
            return None, ""
        return self.env["woo.service"].upload_image(
            self.instance_id,
            self.woo_image,
            product_ref=self.woo_id or "new",
        )

    # ── ORM overrides ─────────────────────────────────────────────────────────

    def write(self, vals):
        """
        Intercepts writes that change any of ``woo_status``, ``stock_status``
        or ``woo_price_input`` and pushes the updated fields to WooCommerce for
        every record that already exists there (woo_id != 0).

        During a bulk Excel import (context ``import_file=True`` set by Odoo's
        base_import module), the WC API call is SKIPPED and ``woo_pending_sync``
        is flagged instead. This avoids:
          - Hitting WooCommerce during test/dry-run imports (Odoo rolls back
            the DB but the API call would already have been made).
          - Browser connection timeouts caused by hundreds of sequential HTTP
            calls during a large import.
        After the import the user can select all pending records and use the
        "Sync to WooCommerce" server action to send the changes in one pass.

        Set ``skip_wc_sync=True`` in the context to bypass the WC push (used
        internally by methods that build their own payloads, like
        ``action_update_stock_wc``).
        """
        result = super().write(vals)

        _SYNC_FIELDS = {"woo_status", "stock_status", "woo_price_input"}
        if not (_SYNC_FIELDS & set(vals)):
            return result
        if self.env.context.get("skip_wc_sync"):
            return result

        # ── During imports: flag and skip ────────────────────────────────────
        if self.env.context.get("import_file"):
            # Only flag records that actually exist in WooCommerce
            to_flag = self.filtered(lambda r: r.woo_id and r.instance_id)
            if to_flag:
                to_flag.with_context(skip_wc_sync=True).write(
                    {"woo_pending_sync": True}
                )
            return result

        svc = self.env["woo.service"]

        for rec in self:
            if not rec.woo_id or not rec.instance_id:
                continue

            payload = {}

            if "woo_status" in vals:
                payload["status"] = vals["woo_status"]

            if "stock_status" in vals:
                payload["stock_status"] = vals["stock_status"]

            if "woo_price_input" in vals:
                price = vals["woo_price_input"]
                # Fallback to pricelist / list_price if value is 0
                if not price and rec.product_tmpl_id:
                    if rec.instance_id.pricelist_id:
                        product = rec.product_tmpl_id.product_variant_id
                        price = (
                            rec.instance_id.pricelist_id._get_product_price(
                                product, 1.0
                            )
                            or rec.product_tmpl_id.list_price
                        )
                    else:
                        price = rec.product_tmpl_id.list_price
                if price:
                    payload["regular_price"] = str(round(price, 4))

            if not payload:
                continue

            try:
                svc.update_product(rec.instance_id, rec.woo_id, payload)
                rec.with_context(skip_wc_sync=True).write(
                    {"last_sync_date": fields.Datetime.now(), "woo_pending_sync": False}
                )
                _logger.info(
                    "WC sync payload %s for product '%s' (woo_id=%s, instance='%s')",
                    list(payload.keys()),
                    rec.woo_name,
                    rec.woo_id,
                    rec.instance_id.name,
                )
            except Exception as exc:
                _logger.warning(
                    "Could not sync fields %s to WooCommerce for product '%s' (woo_id=%s): %s",
                    list(payload.keys()),
                    rec.woo_name,
                    rec.woo_id,
                    exc,
                )

        return result

    # ── Actions ────────────────────────────────────────────────────────────────

    def action_link_manually(self):
        """Opens wizard to manually link this record to an Odoo product."""
        self.ensure_one()
        wizard = self.env["woo.link.wizard"].create({"woo_product_id": self.id})
        return {
            "type": "ir.actions.act_window",
            "name": f"Link '{self.woo_name}' to Odoo product",
            "res_model": "woo.link.wizard",
            "res_id": wizard.id,
            "view_mode": "form",
            "target": "new",
        }

    def action_unlink(self):
        """Unlinks this record from its Odoo product."""
        self.product_tmpl_id = False
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Unlinked",
                "message": f"'{self.woo_name}' is no longer linked to any Odoo product.",
                "type": "warning",
                "sticky": False,
            },
        }

    def action_create_in_wc(self):
        """Creates the product in WooCommerce and saves the returned woo_id."""
        self.ensure_one()
        if self.woo_id:
            raise UserError(
                _("This product already exists in WooCommerce (ID: %s).") % self.woo_id
            )
        if not self.woo_name:
            raise UserError(_("You must enter the product name."))
        if not self.instance_id:
            raise UserError(_("You must select a WooCommerce instance."))

        svc = self.env["woo.service"]

        # Calculate price: manual > instance pricelist > list_price
        price = self.woo_price_input
        if not price and self.product_tmpl_id:
            if self.instance_id.pricelist_id:
                product = self.product_tmpl_id.product_variant_id
                price = (
                    self.instance_id.pricelist_id._get_product_price(product, 1.0)
                    or self.product_tmpl_id.list_price
                )
            else:
                price = self.product_tmpl_id.list_price

        description = ""
        if self.product_tmpl_id:
            description = self.product_tmpl_id.description_sale or ""

        payload = {
            "name": self.woo_name,
            "status": self.woo_status or "draft",
            "regular_price": str(round(price, 4)),
            "sku": self.woo_sku or "",
            "type": self.woo_type or "simple",
            "description": description,
        }

        # Send image by URL if provided (without saving binary in Odoo)
        image_vals = {}
        if self.woo_image_url_input:
            payload["images"] = [{"src": self.woo_image_url_input}]
        else:
            payload["images"] = []

        # Categories — respecting WooCommerce parent/child hierarchy
        categories_payload = self._build_categories_payload()
        if categories_payload:
            payload["categories"] = categories_payload

        # Brands — requires brands plugin in WooCommerce
        brands_payload = self._build_brands_payload()
        if brands_payload:
            payload["brands"] = brands_payload

        wc_response = svc.create_product(self.instance_id, payload)

        if not wc_response or not wc_response.get("id"):
            raise UserError(_("No valid response received from WooCommerce."))

        write_vals = {
            "woo_id": wc_response["id"],
            "woo_name": wc_response.get("name", self.woo_name),
            "woo_status": wc_response.get("status", self.woo_status),
            "woo_sku": wc_response.get("sku", self.woo_sku),
            "woo_type": wc_response.get("type", self.woo_type),
            "woo_price": price,
            "woo_permalink": wc_response.get("permalink", ""),
            "last_sync_date": fields.Datetime.now(),
        }

        # WooCommerce stock
        if self.instance_manage_stock:
            write_vals["stock_quantity"] = wc_response.get("stock_quantity") or 0
            write_vals["min_quantity"] = wc_response.get("woo_min_stock") or 0
            write_vals["max_quantity"] = wc_response.get("woo_max_stock") or 0

        # Capture image URL returned by WooCommerce (without saving binary)
        wc_images = wc_response.get("images", [])
        if wc_images:
            write_vals["woo_image_src"] = wc_images[0].get("src", "")
            write_vals["woo_image_id"] = wc_images[0].get("id", 0)
        # Clear input URL field after sending
        if self.woo_image_url_input:
            write_vals["woo_image_url_input"] = False
        write_vals.update(image_vals)
        self.with_context(skip_wc_sync=True).write(write_vals)
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Product created in WooCommerce"),
                "message": _("'%s' created with ID %s in '%s'.")
                % (self.woo_name, self.woo_id, self.instance_id.name),
                "type": "success",
                "sticky": False,
            },
        }

    def action_update_stock_wc(self):
        """Sends name, stock_status, publish status, price and image to WooCommerce."""
        self.ensure_one()
        svc = self.env["woo.service"]

        payload = {
            "name": self.woo_name,
            "stock_status": self.stock_status or "instock",
        }

        if (
            self.instance_manage_stock
            and self.stock_quantity is not False
            and self.stock_quantity >= 0
        ):
            payload["manage_stock"] = True
            payload["stock_quantity"] = int(self.stock_quantity)

        if self.instance_manage_stock and self.woo_min_stock:
            payload["min_quantity"] = int(self.woo_min_stock)
        if self.instance_manage_stock and self.woo_max_stock:
            payload["manage_stock"] = True
            payload["max_quantity"] = int(self.woo_max_stock)
        if self.instance_manage_stock and self.woo_status:
            payload["status"] = self.woo_status

        # Calculate and send price
        price = self.woo_price_input
        if not price and self.product_tmpl_id:
            if self.instance_id.pricelist_id:
                product = self.product_tmpl_id.product_variant_id
                price = (
                    self.instance_id.pricelist_id._get_product_price(product, 1.0)
                    or self.product_tmpl_id.list_price
                )
            else:
                price = self.product_tmpl_id.list_price
        if price:
            payload["regular_price"] = str(round(price, 4))

        # Send image by URL if provided (without saving binary in Odoo)
        image_vals = {}
        if self.woo_image_url_input:
            payload["images"] = [{"src": self.woo_image_url_input}]

        # Categories — respecting WooCommerce parent/child hierarchy
        categories_payload = self._build_categories_payload()
        if categories_payload:
            payload["categories"] = categories_payload

        # Brands — requires brands plugin in WooCommerce
        brands_payload = self._build_brands_payload()
        if brands_payload:
            payload["brands"] = brands_payload

        try:
            wc_response = svc.update_product(self.instance_id, self.woo_id, payload)
        except Exception as e:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Error updating in WooCommerce",
                    "message": str(e),
                    "type": "danger",
                    "sticky": True,
                },
            }

        vals = {"last_sync_date": fields.Datetime.now()}
        if price:
            vals["woo_price"] = price
        # Capture stock_quantity returned by WooCommerce
        if wc_response and isinstance(wc_response, dict):
            wc_qty = wc_response.get("stock_quantity")
            if wc_qty is not None:
                vals["stock_quantity"] = wc_qty
            wc_stock_status = wc_response.get("stock_status")
            if wc_stock_status:
                vals["stock_status"] = wc_stock_status
        vals.update(image_vals)
        # Capture image URL returned by WooCommerce
        if wc_response and self.woo_image_url_input:
            wc_images = (
                wc_response.get("images", []) if isinstance(wc_response, dict) else []
            )
            if wc_images:
                vals["woo_image_src"] = wc_images[0].get("src", "")
                vals["woo_image_id"] = wc_images[0].get("id", 0)
        # Clear input URL field after sending
        if self.woo_image_url_input:
            vals["woo_image_url_input"] = False
        self.with_context(skip_wc_sync=True).write(vals)
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Updated in WooCommerce",
                "message": f"'{self.woo_name}' updated successfully in '{self.instance_id.name}'.",
                "type": "success",
                "sticky": False,
                "next": {"type": "ir.actions.act_window_close"},
            },
        }

    def _bus_notify(self, msg_type, title, message, sticky=False):
        """Sends a real-time notification to the current user via Odoo bus.

        These notifications are delivered immediately (longpoll) regardless of
        whether the final HTTP response is ever sent back to the browser.
        That means the user sees progress even if the worker is killed by
        Odoo's memory/CPU limiter before the action returns.
        """
        try:
            self.env["bus.bus"]._sendone(
                self.env.user.partner_id,
                "simple_notification",
                {
                    "title": title,
                    "message": message,
                    "type": msg_type,
                    "sticky": sticky,
                },
            )
            self.env.cr.commit()
        except Exception:
            pass  # never break the sync loop over a notification failure

    def action_push_pending_to_wc(self):
        """
        Bulk-syncs the current recordset to WooCommerce.

        Called from the tree-view server action "Sync to WooCommerce".
        Sends each record's current woo_status, stock_status and price in a
        single PUT call per record. Records without a woo_id are skipped.

        Progress is committed to the DB after each successful product so that
        if the browser times out (Odoo worker keeps running), the records
        already synced are permanently marked woo_pending_sync=False.
        Records that fail keep woo_pending_sync=True and can be retried by
        running the action again.

        Real-time bus notifications are sent so the user receives feedback
        even if the connection drops before the action returns.
        """
        to_sync = self.filtered(lambda r: r.woo_id and r.instance_id)
        total = len(to_sync)

        if not total:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("WooCommerce sync"),
                    "message": _("No products with a WooCommerce ID were selected."),
                    "type": "warning",
                    "sticky": False,
                },
            }

        ok = 0
        failed = 0
        errors = []
        svc = self.env["woo.service"]

        # ── Start notification ────────────────────────────────────────────────
        self._bus_notify(
            "info",
            _("WooCommerce sync"),
            _("Starting sync of %d product(s)…") % total,
        )

        for rec in to_sync:
            payload = {
                "status": rec.woo_status or "draft",
                "stock_status": rec.stock_status or "instock",
            }

            # Price: manual > pricelist > list_price
            price = rec.woo_price_input
            if not price and rec.product_tmpl_id:
                if rec.instance_id.pricelist_id:
                    product = rec.product_tmpl_id.product_variant_id
                    price = (
                        rec.instance_id.pricelist_id._get_product_price(product, 1.0)
                        or rec.product_tmpl_id.list_price
                    )
                else:
                    price = rec.product_tmpl_id.list_price
            if price:
                payload["regular_price"] = str(round(price, 4))

            try:
                svc.update_product(rec.instance_id, rec.woo_id, payload)
                rec.with_context(skip_wc_sync=True).write(
                    {
                        "last_sync_date": fields.Datetime.now(),
                        "woo_pending_sync": False,
                    }
                )
                # Commit after each success: partial progress is persisted even
                # if the worker is killed by Odoo's resource limiter.
                self.env.cr.commit()
                ok += 1
                _logger.info(
                    "Bulk WC sync OK: '%s' (woo_id=%s)", rec.woo_name, rec.woo_id
                )

                # ── Progress notification every 10 products ───────────────────
                if ok % 10 == 0:
                    remaining = total - ok - failed
                    self._bus_notify(
                        "info",
                        _("WooCommerce sync in progress…"),
                        _("%(ok)d/%(total)d synced — %(remaining)d remaining.")
                        % {"ok": ok, "total": total, "remaining": remaining},
                    )

            except Exception as exc:
                # Rollback only the failed write; continue with the next record.
                self.env.cr.rollback()
                failed += 1
                errors.append(f"• {rec.woo_name}: {exc}")
                _logger.warning(
                    "Bulk WC sync error for '%s' (woo_id=%s): %s",
                    rec.woo_name,
                    rec.woo_id,
                    exc,
                )
                # Notify immediately on each error so the user is aware
                self._bus_notify(
                    "warning",
                    _("WooCommerce sync — error"),
                    _("'%s' could not be synced: %s") % (rec.woo_name, exc),
                    sticky=False,
                )

        # ── Final notification (delivered even if browser already disconnected)
        if failed:
            final_msg = _(
                "%(ok)d synced correctly, %(failed)d still pending.\n"
                "Use the 'Pending sync' filter and run 'Sync to WooCommerce' again to retry."
            ) % {"ok": ok, "failed": failed}
            self._bus_notify("warning", _("WooCommerce sync — incomplete"), final_msg, sticky=True)
            msg_type = "warning"
        else:
            final_msg = _("All %d product(s) synced to WooCommerce successfully.") % ok
            self._bus_notify("success", _("WooCommerce sync — done ✓"), final_msg, sticky=True)
            msg_type = "success"

        # display_notification is shown when the browser IS still connected
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("WooCommerce sync"),
                "message": final_msg,
                "type": msg_type,
                "sticky": bool(failed),
            },
        }

