from odoo import _, models, fields, api
import json
import logging
from datetime import datetime
from odoo.exceptions import UserError, ValidationError


_logger = logging.getLogger(__name__)


class OdooWpSync(models.Model):
    _name = "odoo.wp.sync"
    _description = "WooCommerce Orders Sync"
    _order = "date_created desc"

    # Display name
    name = fields.Char(string="Name", compute="_compute_name", store=True)

    # Instance (Multi-Instance Support)
    instance_id = fields.Many2one(
        "woo.instance",
        string="WooCommerce Instance",
        required=True,
        ondelete="restrict",
        index=True,
        default=lambda self: self.env["woo.instance"].get_default_instance(),
        help="WooCommerce instance from which this order was imported",
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        related="instance_id.company_id",
        store=True,
        readonly=True,
    )

    # WooCommerce Order Info
    wc_order_id = fields.Integer(
        string="WooCommerce Order ID", required=True, index=True
    )
    order_number = fields.Char(string="Order Number", readonly=True)

    # Customer Info
    customer_name = fields.Char(string="Customer Name")
    customer_email = fields.Char(string="Customer Email")
    customer_phone = fields.Char(string="Phone")

    # Order Details
    status = fields.Selection(
        [
            ("pending", "Pending Payment"),
            ("processing", "Processing"),
            ("on-hold", "On Hold"),
            ("completed", "Completed"),
            ("cancelled", "Cancelled"),
            ("refunded", "Refunded"),
            ("failed", "Failed"),
        ],
        string="Status",
        default="pending",
    )

    date_created = fields.Datetime(string="Date Created")
    total = fields.Float(string="Total Amount")
    shipping_total = fields.Float(string="Shipping Total")
    discount_total = fields.Float(string="Discount Total")
    currency = fields.Char(string="Currency", default="USD")

    # Items and Details
    items_info = fields.Text(string="Order Items")
    shipping_address = fields.Text(string="Shipping Address JSON", readonly=True)
    shipping_address_formatted = fields.Text(string="Shipping Address")
    payment_method = fields.Char(string="Payment Method")
    created_via = fields.Char(
        string="Origin", help="Order source (checkout, admin, etc.)"
    )

    # Raw Data
    raw_data = fields.Text(string="Raw JSON Data", readonly=True)
    order_lines = fields.Text(string="Order Lines JSON", readonly=True)

    line_ids = fields.One2many(
        "woo.order.line",
        "order_id",
        string="Order Lines",
        readonly=True,
    )

    sale_order_id = fields.Many2one("sale.order")

    # Sync Info
    synced_date = fields.Datetime(string="Last Synced", default=fields.Datetime.now)

    _sql_constraints = [
        (
            "wc_order_id_instance_unique",
            "unique(wc_order_id, instance_id)",
            "WooCommerce Order ID must be unique per instance!",
        )
    ]

    @api.depends("order_number", "customer_name")
    def _compute_name(self):
        """Compute display name combining order number and customer name"""
        for record in self:
            if record.order_number and record.customer_name:
                record.name = f"{record.order_number} - {record.customer_name}"
            elif record.order_number:
                record.name = record.order_number
            else:
                record.name = f"Order #{record.wc_order_id}"

    def action_open_sync_wizard(self):
        """Opens the confirmation wizard to sync with WooCommerce"""
        confirmation_wizard = self.env["confirmation.wizard"]

        description = _(
            "This action will download all recent orders from WooCommerce and import them into Odoo. This process may take a few minutes depending on the number of orders."
        )

        return confirmation_wizard.create_confirmation(
            model_name="odoo.wp.sync",
            method_name="action_sync",
            title=_("Sync with WooCommerce?"),
            description=description,
            dialog_size="medium",  # Opciones: 'small', 'medium', 'large', 'extra-large'
        )

    def _build_sync_params(self, instance, force_full=False):
        """
        Build WooCommerce API query parameters based on instance settings.

        Full sync   → returns (params_dict, "full")
        Incremental → returns ([params_new, params_modified], "incremental")
          - params_new      uses ``after``          (date_created_gmt, all WC versions)
          - params_modified uses ``modified_after`` (date_modified_gmt, WC 5.5+)
        The caller deduplicates the two result sets.
        """
        from datetime import timedelta

        base = {
            "per_page": instance.sync_order_limit or 100,
            "orderby": "modified",
            "order": "desc",
        }

        # Build status filter once and apply to every request
        status_filter = {}
        if instance.sync_order_status and instance.sync_order_status != "all":
            if instance.sync_order_status == "custom":
                if instance.sync_custom_statuses:
                    statuses = [
                        s.strip() for s in instance.sync_custom_statuses.split(",")
                    ]
                    status_filter["status"] = ",".join(statuses)
            else:
                status_filter["status"] = instance.sync_order_status

        should_do_full = force_full or instance._should_do_full_sync()

        if should_do_full or not instance.last_sync_date:
            # Full sync — single request
            params = {**base, **status_filter}
            if instance.sync_from_date:
                params["after"] = f"{instance.sync_from_date}T00:00:00Z"
            return params, "full"

        # Incremental sync — two requests to cover all WooCommerce versions:
        #   A) ``after``          → NEW orders   (universally supported since WC REST v1)
        #   B) ``modified_after`` → UPDATED orders (WC 5.5+; returns [] gracefully on older)
        last_sync_with_buffer = instance.last_sync_date - timedelta(minutes=1)
        ts = last_sync_with_buffer.strftime("%Y-%m-%dT%H:%M:%S") + "Z"

        _logger.info(
            "Incremental sync for '%s': fetching orders after %s UTC",
            instance.name,
            ts,
        )

        params_new = {**base, **status_filter, "after": ts}
        params_modified = {**base, **status_filter, "modified_after": ts}

        return [params_new, params_modified], "incremental"

    def action_sync(self):
        """
        Synchronize orders from WooCommerce using instance configuration parameters
        Implements intelligent incremental/full sync with statistics tracking
        """
        import time

        start_time = time.time()

        instance = None
        created_count = 0
        updated_count = 0
        all_orders = []
        sync_type = (
            None  # set by _build_sync_params; used to update last_full_sync_date
        )

        try:
            # Get instance from context or use default
            instance_id = self.env.context.get("default_instance_id")
            force_full = self.env.context.get("full_sync", False)

            if not instance_id:
                instance = self.env["woo.instance"].get_default_instance()
                if not instance:
                    return {
                        "type": "ir.actions.client",
                        "tag": "display_notification",
                        "params": {
                            "title": "No Instance",
                            "message": "Please create a WooCommerce instance first",
                            "type": "warning",
                            "sticky": True,
                        },
                    }
                instance_id = instance.id
            else:
                instance = self.env["woo.instance"].browse(instance_id)

            # Validate instance is connected
            if instance.state != "connected":
                return {
                    "type": "ir.actions.client",
                    "tag": "display_notification",
                    "params": {
                        "title": "Instance Not Connected",
                        "message": f"Instance '{instance.name}' is not connected. Please test connection first.",
                        "type": "warning",
                        "sticky": True,
                    },
                }

            svc = self.env["woo.service"]

            # Build query parameters from instance settings
            params_result, sync_type = self._build_sync_params(
                instance, force_full=force_full
            )

            _logger.info("Starting %s sync for %s", sync_type, instance.name)

            # Fetch orders — incremental uses two requests (new + modified) for
            # compatibility with all WooCommerce versions.
            if sync_type == "incremental" and isinstance(params_result, list):
                params_new, params_modified = params_result

                # A: orders created after last sync (all WC versions)
                new_orders = svc.fetch_orders(instance, params_new)
                _logger.info(
                    "Incremental A (after/new): %d orders from '%s'",
                    len(new_orders),
                    instance.name,
                )

                # B: orders modified after last sync (WC 5.5+; returns [] on older)
                modified_orders = svc.fetch_orders(instance, params_modified)
                _logger.info(
                    "Incremental B (modified_after): %d orders from '%s'",
                    len(modified_orders),
                    instance.name,
                )

                # Deduplicate: B overwrites A so the most up-to-date data wins
                merged = {o["id"]: o for o in new_orders}
                merged.update({o["id"]: o for o in modified_orders})
                all_orders = list(merged.values())
            else:
                all_orders = svc.fetch_orders(instance, params_result)

            _logger.info(
                "Fetched %d total orders from '%s'", len(all_orders), instance.name
            )

            # Process all fetched orders
            # Collect woo.order records that are candidates for auto sale order creation.
            auto_create_candidates = []

            for order_data in all_orders:
                order_id = order_data.get("id")

                # Check if order already exists for this instance
                existing_order = self.search(
                    [("wc_order_id", "=", order_id), ("instance_id", "=", instance_id)],
                    limit=1,
                )

                # Prepare order values
                vals = self._prepare_order_vals(order_data)
                vals["instance_id"] = instance_id

                if existing_order:
                    existing_order.write(vals)
                    updated_count += 1
                    woo_record = existing_order
                else:
                    woo_record = self.create(vals)
                    created_count += 1

                # Queue for auto sale order creation if applicable
                if instance.auto_create_sale_order and not woo_record.sale_order_id:
                    auto_create_candidates.append(woo_record)

            # Auto-create sale orders for qualifying WooCommerce orders
            auto_create_stats = {"created": 0, "skipped": 0, "errors": 0}
            if instance.auto_create_sale_order:
                # Also pick up any existing records that were synced before
                # auto-create was enabled and still don't have a sale order.
                existing_without_so = self.search(
                    [
                        ("instance_id", "=", instance_id),
                        ("sale_order_id", "=", False),
                    ]
                )
                # Merge: use a dict keyed by id to avoid duplicates
                candidates_map = {r.id: r for r in auto_create_candidates}
                for r in existing_without_so:
                    candidates_map.setdefault(r.id, r)
                all_candidates = list(candidates_map.values())

                if all_candidates:
                    auto_create_stats = self._auto_create_sale_orders(
                        instance, all_candidates
                    )
                _logger.info(
                    "Auto-create enabled: %d candidates (sync: %d, backlog: %d), "
                    "%d created, %d skipped, %d errors",
                    len(all_candidates),
                    len(auto_create_candidates),
                    len(existing_without_so),
                    auto_create_stats["created"],
                    auto_create_stats["skipped"],
                    auto_create_stats["errors"],
                )
            else:
                _logger.info(
                    "Auto-create sale orders is DISABLED for instance '%s'",
                    instance.name,
                )

            # Calculate sync duration
            duration = time.time() - start_time

            # Update instance statistics
            instance._update_sync_statistics(
                created=created_count,
                updated=updated_count,
                total=len(all_orders),
                duration=duration,
                error=None,
                sync_type=sync_type,
            )

            # Build success message with details
            sync_type_label = (
                "🔄 Incremental" if sync_type == "incremental" else "📦 Full"
            )
            filter_info = [sync_type_label]

            if sync_type == "incremental" and instance.last_sync_date:
                time_diff = datetime.now() - instance.last_sync_date
                if time_diff.days > 0:
                    filter_info.append(f"{time_diff.days}d ago")
                else:
                    hours = time_diff.seconds // 3600
                    filter_info.append(f"{hours}h ago")
            elif instance.sync_from_date and sync_type == "full":
                filter_info.append(f"from {instance.sync_from_date}")

            if instance.sync_order_status and instance.sync_order_status != "all":
                status_label = dict(
                    instance._fields["sync_order_status"].selection
                ).get(instance.sync_order_status, instance.sync_order_status)
                filter_info.append(f"status: {status_label}")

            filter_msg = f" ({', '.join(filter_info)})"

            # Prepare message
            sale_order_line = ""
            if instance.auto_create_sale_order:
                sale_order_line = (
                    f"\n🛒 Auto-created orders: {auto_create_stats['created']} | "
                    f"Skipped: {auto_create_stats['skipped']} | "
                    f"Errors: {auto_create_stats['errors']} "
                    f"({len(all_candidates)} candidates)"
                )
            else:
                sale_order_line = (
                    "\n⚠️ Auto-order creation: DISABLED (enable it in instance settings)"
                )

            message = (
                f"✅ Created: {created_count} | ✏️ Updated: {updated_count} | "
                f"📊 Total: {len(all_orders)} orders\n"
                f"⏱️ Duration: {duration:.2f}s{filter_msg}"
                f"{sale_order_line}"
            )

            # Show result to user
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": f"Sync successful - {instance.name}",
                    "message": message,
                    "type": "success",
                    "sticky": False,
                },
            }

        except Exception as e:
            error_msg = str(e)
            duration = time.time() - start_time

            # Update instance with error statistics
            if instance:
                instance._update_sync_statistics(
                    created=created_count,
                    updated=updated_count,
                    total=len(all_orders),
                    duration=duration,
                    error=error_msg,
                    sync_type=sync_type,
                )

            _logger.error(f"Sync error: {error_msg}", exc_info=True)

            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Synchronization Error",
                    "message": f"{error_msg}\n\nConsecutive errors: {instance.sync_error_count if instance else 0}",
                    "type": "danger",
                    "sticky": True,
                },
            }

    def _auto_create_sale_orders(self, instance, woo_records):
        """
        Create sale orders automatically for WooCommerce orders whose status
        matches the configured ``auto_create_sale_order_statuses`` list.

        Called from ``action_sync`` after importing/updating records.

        :param instance: woo.instance record
        :param woo_records: list of odoo.wp.sync records (no sale_order_id yet)
        :returns: dict with keys ``created``, ``skipped``, ``errors``
        """
        # Parse the configured status list (comma-separated, strip whitespace)
        raw_statuses = instance.auto_create_sale_order_statuses or "processing"
        trigger_statuses = {s.strip() for s in raw_statuses.split(",") if s.strip()}

        _logger.info(
            "_auto_create_sale_orders: %d candidates, trigger statuses=%s",
            len(woo_records),
            trigger_statuses,
        )

        sale_order_helper = self.env["woo.sale.order.helper"]
        created = skipped = errors = 0

        for woo_record in woo_records:
            _logger.info(
                "  Order #%s status='%s' — in trigger_statuses: %s",
                woo_record.order_number,
                woo_record.status,
                woo_record.status in trigger_statuses,
            )
            if woo_record.status not in trigger_statuses:
                skipped += 1
                continue

            try:
                result = sale_order_helper.create_sale_order_from_woo(woo_record)
                if result.get("created"):
                    created += 1
                    _logger.info(
                        "Auto-created sale order %s for WooCommerce order #%s",
                        result["order"].name,
                        woo_record.order_number,
                    )
                elif result.get("skipped"):
                    skipped += 1
                else:
                    skipped += 1
                    _logger.debug(
                        "Sale order already existed (%s) for WooCommerce order #%s — skipped.",
                        result["order"].name if result.get("order") else "N/A",
                        woo_record.order_number,
                    )
            except Exception:
                errors += 1
                _logger.exception(
                    "Auto sale order creation failed for WooCommerce order #%s",
                    woo_record.order_number,
                )

        return {"created": created, "skipped": skipped, "errors": errors}

    def _prepare_order_vals(self, order_data):
        """Prepare order values from WooCommerce data"""
        # Customer info
        billing = order_data.get("billing", {})
        customer_name = (
            f"{billing.get('first_name', '')} {billing.get('last_name', '')}".strip()
        )

        # Shipping address
        shipping = order_data.get("shipping", {})
        shipping_address_formatted = ""
        if shipping:
            shipping_address_formatted = (
                f"{shipping.get('address_1', '')} {shipping.get('address_2', '')}\n"
                f"{shipping.get('city', '')}, {shipping.get('state', '')} {shipping.get('postcode', '')}\n"
                f"{shipping.get('country', '')}"
            )

        # Order items
        order_lines = []
        line_ids_commands = [(5, 0, 0)]  # Clear existing lines on update

        for item in order_data.get("line_items", []):
            line_data = {
                "sku": item.get("sku"),
                "name": item.get("name"),
                "quantity": item.get("quantity", 0),
                "total": float(item.get("total", 0)),
                "price": float(item.get("price", 0)),
                "subtotal": float(item.get("subtotal", 0)),
                "total_tax": float(item.get("total_tax", 0)),
                "taxes": item.get("taxes", []),
            }
            order_lines.append(line_data)
            line_ids_commands.append(
                (
                    0,
                    0,
                    {
                        "line_type": "product",
                        "sku": line_data["sku"],
                        "name": line_data["name"],
                        "quantity": line_data["quantity"],
                        "price": line_data["price"],
                        "subtotal": line_data["subtotal"],
                        "total": line_data["total"],
                        "total_tax": line_data["total_tax"],
                    },
                )
            )

        # Add a shipping line if there is a shipping total
        shipping_total = float(order_data.get("shipping_total", 0))
        shipping_tax = float(order_data.get("shipping_tax", 0))
        if shipping_total:
            shipping_lines = order_data.get("shipping_lines", [])
            shipping_method = (
                shipping_lines[0].get("method_title", "Shipping")
                if shipping_lines
                else "Shipping"
            )
            line_ids_commands.append(
                (
                    0,
                    0,
                    {
                        "line_type": "shipping",
                        "name": shipping_method,
                        "sku": "",
                        "quantity": 1,
                        "price": shipping_total,
                        "subtotal": shipping_total,
                        "total": shipping_total,
                        "total_tax": shipping_tax,
                        "sequence": 9999,
                    },
                )
            )

        # Convert WooCommerce date format to Odoo format
        date_created = order_data.get("date_created")
        if date_created:
            # WooCommerce format: "2026-03-29T19:57:05"
            # Odoo format: "2026-03-29 19:57:05"
            date_created = date_created.replace("T", " ").split(".")[
                0
            ]  # Remove milliseconds if present

        return {
            "wc_order_id": order_data.get("id"),
            "order_number": order_data.get("number"),
            "customer_name": customer_name or "Guest",
            "customer_email": billing.get("email", ""),
            "customer_phone": billing.get("phone", ""),
            "status": order_data.get("status", "pending"),
            "date_created": date_created,
            "shipping_total": float(order_data.get("shipping_total", 0)),
            "discount_total": float(order_data.get("discount_total", 0)),
            "total": float(order_data.get("total", 0)),
            "currency": order_data.get("currency", "USD"),
            "shipping_address_formatted": shipping_address_formatted.strip(),
            "payment_method": order_data.get("payment_method_title", ""),
            "created_via": order_data.get("created_via", ""),
            "order_lines": json.dumps(order_lines),
            "line_ids": line_ids_commands,
            "raw_data": json.dumps(order_data, indent=2),
            "synced_date": fields.Datetime.now(),
            "shipping_address": json.dumps(order_data.get("shipping", {}), indent=2),
        }

    BLOCKED_STATUSES = {"failed", "refunded", "cancelled"}

    def action_open_create_sale_order_wizard(self):
        """Opens the confirmation wizard to create orders in Odoo (supports multiple records)"""
        confirmation_wizard = self.env["confirmation.wizard"]

        # Block orders in terminal/invalid states
        blocked_orders = self.filtered(lambda o: o.status in self.BLOCKED_STATUSES)
        if blocked_orders:
            blocked_numbers = ", ".join(blocked_orders.mapped("order_number"))
            blocked_label = ", ".join(sorted(self.BLOCKED_STATUSES))
            raise UserError(
                _(
                    "The following order(s) cannot be processed because their status is %s:\n%s\n\nOnly orders that are not failed, refunded, or cancelled can be converted to Odoo orders."
                )
                % (blocked_label, blocked_numbers)
            )

        # Validate that all involved instances are properly connected
        instances = self.mapped("instance_id")
        not_connected = instances.filtered(lambda i: i.state != "connected")
        if not_connected:
            names = ", ".join(not_connected.mapped("name"))
            raise UserError(
                _(
                    "The following instance(s) are not properly connected: %s.\nPlease test the connection from the instance settings before continuing."
                )
                % names
            )

        # Filter only orders that do NOT have a sale order linked
        orders_to_create = self.filtered(lambda o: not o.sale_order_id)
        orders_already_exist = self.filtered(lambda o: o.sale_order_id)

        if not orders_to_create:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("No orders to create"),
                    "message": _(
                        "All selected orders (%d) already have sale orders linked."
                    )
                    % len(self),
                    "type": "warning",
                    "sticky": False,
                },
            }

        # Prepare description based on quantity
        if len(orders_to_create) == 1:
            order = orders_to_create
            description = _(
                "A sale order will be created in Odoo for order #%s from %s totaling %s %s"
            ) % (order.order_number, order.customer_name, order.currency, order.total)
        else:
            total_amount = sum(orders_to_create.mapped("total"))
            currency = orders_to_create[0].currency if orders_to_create else "USD"

            description = _(
                "%d sale orders will be created in Odoo for a total of %s %.2f"
            ) % (len(orders_to_create), currency, total_amount)

            if orders_already_exist:
                description += _(
                    "\n\nNote: %d orders already have sale orders linked and will be skipped."
                ) % len(orders_already_exist)

        # Pasar los IDs de los registros a procesar
        return confirmation_wizard.create_confirmation(
            model_name="odoo.wp.sync",
            method_name="action_create_sale_order",
            record_ids=orders_to_create.ids,
            title=_("Create Sale Order(s) in Odoo?"),
            description=description,
            dialog_size="medium",
        )

    def action_create_sale_order(self):
        """
        Creates sale orders in Odoo from WooCommerce data.
        Supports multiple record processing.
        Delegates logic to the woo.sale.order.helper.
        """
        helper = self.env["woo.sale.order.helper"]

        # Summary counters
        created_count = 0
        linked_count = 0
        skipped_count = 0
        error_count = 0
        errors = []

        created_orders = self.env["sale.order"]

        for woo_order in self:
            # Skip if already has a linked sale order
            if woo_order.sale_order_id:
                skipped_count += 1
                continue

            # Block creation for terminal/invalid statuses
            if woo_order.status in self.BLOCKED_STATUSES:
                error_count += 1
                errors.append(
                    f"Order #{woo_order.order_number}: cannot create sale order "
                    f"because the WooCommerce status is '{woo_order.status}'."
                )
                continue

            try:
                result = helper.create_sale_order_from_woo(woo_order)
                order = result["order"]
                was_created = result["created"]

                # Save the sale order link
                woo_order.sale_order_id = order.id

                if was_created:
                    created_count += 1
                    created_orders |= order
                else:
                    linked_count += 1

            except Exception as e:
                error_count += 1
                errors.append(f"Order #{woo_order.order_number}: {str(e)}")
                _logger.error(
                    f"Error creating sale order for Woo Order ID {woo_order.wc_order_id}: {str(e)}",
                    exc_info=True,
                )

        # Preparar mensaje de resumen
        total_processed = len(self)
        message_parts = []

        if created_count > 0:
            message_parts.append(f"✅ {created_count} order(s) created")
        if linked_count > 0:
            message_parts.append(f"🔗 {linked_count} order(s) linked (already existed)")
        if skipped_count > 0:
            message_parts.append(f"⏭️ {skipped_count} skipped (already had orders)")
        if error_count > 0:
            message_parts.append(f"❌ {error_count} error(s)")

        message = "\n".join(message_parts)

        # Add error details if any
        if errors:
            message += "\n\nErrors:\n" + "\n".join(errors[:3])  # Show maximum 3 errors
            if len(errors) > 3:
                message += f"\n... and {len(errors) - 3} more error(s)"

        # Determine notification type
        if error_count == total_processed:
            notification_type = "danger"
            title = "Errors creating orders"
        elif error_count > 0:
            notification_type = "warning"
            title = "Orders created with errors"
        else:
            notification_type = "success"
            title = "Orders processed successfully"

        # If only one order was created, open it automatically
        if created_count == 1 and len(created_orders) == 1:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": title,
                    "message": message,
                    "type": notification_type,
                    "sticky": False,
                    "next": {
                        "type": "ir.actions.act_window",
                        "res_model": "sale.order",
                        "res_id": created_orders.id,
                        "views": [[False, "form"]],
                        "target": "current",
                    },
                },
            }

        # If multiple orders were created, show a list
        if created_count > 1:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": title,
                    "message": message,
                    "type": notification_type,
                    "sticky": False,
                    "next": {
                        "type": "ir.actions.act_window",
                        "res_model": "sale.order",
                        "domain": [("id", "in", created_orders.ids)],
                        "views": [[False, "tree"], [False, "form"]],
                        "target": "current",
                        "name": "Created Orders",
                    },
                },
            }

        # Show notification only
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": title,
                "message": message,
                "type": notification_type,
                "sticky": error_count > 0,
            },
        }

    @api.constrains("instance_id")
    def _check_instance_connected(self):
        for rec in self:
            if rec.instance_id and rec.instance_id.state != "connected":
                raise ValidationError(
                    "Instance '%s' is not connected. "
                    "Complete the setup and verify the connection before creating orders."
                    % rec.instance_id.name
                )

    def action_open_sale_order(self):
        """Abre el pedido de venta asociado"""
        self.ensure_one()

        if not self.sale_order_id:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Sin pedido asociado",
                    "message": "Esta orden no tiene un pedido de venta asociado.",
                    "type": "warning",
                    "sticky": False,
                },
            }

        return {
            "type": "ir.actions.act_window",
            "res_model": "sale.order",
            "res_id": self.sale_order_id.id,
            "views": [[False, "form"]],
            "target": "current",
        }
