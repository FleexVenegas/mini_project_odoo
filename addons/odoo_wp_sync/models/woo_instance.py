from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import re
import logging

_logger = logging.getLogger(__name__)


class WooInstance(models.Model):
    _name = "woo.instance"
    _description = "WooCommerce Instance"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "sequence, name"
    _rec_name = "name"

    # Basic Information
    name = fields.Char(
        string="Instance Name",
        required=True,
        tracking=True,
        help="Unique name to identify this WooCommerce instance",
    )
    sequence = fields.Integer(
        string="Sequence", default=10, help="Used to order instances"
    )
    active = fields.Boolean(
        default=True, tracking=True, help="If unchecked, this instance will be hidden"
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        default=lambda self: self.env.company,
        required=True,
        tracking=True,
    )

    # Connection Settings
    wp_url = fields.Char(
        string="WordPress URL",
        required=True,
        tracking=True,
        help="Base URL of your WordPress site (e.g., https://mystore.com)",
    )
    consumer_key = fields.Char(
        string="Consumer Key", help="WooCommerce API Consumer Key"
    )
    consumer_secret = fields.Char(
        string="Consumer Secret", help="WooCommerce API Consumer Secret"
    )

    # Instance Status
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("connected", "Connected"),
            ("error", "Connection Error"),
        ],
        string="Status",
        default="draft",
        readonly=True,
        tracking=True,
        help="Connection status of this instance",
    )
    last_connection_test = fields.Datetime(string="Last Connection Test", readonly=True)
    connection_message = fields.Text(string="Connection Message", readonly=True)

    # Statistics
    order_count = fields.Integer(
        string="Orders",
        compute="_compute_statistics",
        help="Number of synced orders from this instance",
    )
    pending_order_count = fields.Integer(
        string="Pending Orders",
        compute="_compute_statistics",
        help="Number of pending orders from this instance",
    )
    completed_order_count = fields.Integer(
        string="Completed Orders",
        compute="_compute_statistics",
        help="Number of completed orders from this instance",
    )
    woo_product_count = fields.Integer(
        string="WC Products",
        compute="_compute_statistics",
        help="Number of products imported from this WooCommerce instance",
    )
    woo_product_linked_count = fields.Integer(
        string="Linked Products",
        compute="_compute_statistics",
        help="WooCommerce products linked to an Odoo product",
    )

    # Technical
    color = fields.Integer(string="Color Index", default=0)

    # Synchronization Parameters - Basic
    sync_order_limit = fields.Integer(
        string="Orders per Sync",
        default=100,
        help="Maximum number of orders to sync per execution",
    )
    sync_from_date = fields.Date(
        string="Sync From Date",
        help="Sync orders created from this date onwards. Leave empty to sync all orders.",
    )
    sync_order_status = fields.Selection(
        [
            ("all", "All Orders"),
            ("pending", "Pending Only"),
            ("processing", "Processing Only"),
            ("completed", "Completed Only"),
            ("custom", "Custom Selection"),
        ],
        string="Order Status Filter",
        default="all",
        help="Which order statuses to sync from WooCommerce",
    )
    sync_custom_statuses = fields.Char(
        string="Custom Statuses",
        help="Comma-separated list of statuses (e.g., pending, processing, completed, on-hold, cancelled, refunded, failed) to sync when 'Custom Selection' is chosen",
    )

    # Synchronization Parameters - Advanced
    sync_mode = fields.Selection(
        [
            ("incremental", "Incremental (Only changes)"),
            ("full", "Full (All orders)"),
        ],
        string="Sync Mode",
        default="incremental",
        help="Incremental: Only new/modified orders. Full: All orders within date range",
    )
    incremental_enabled = fields.Boolean(
        string="Enable Incremental Sync",
        default=True,
        help="Use modified_after to sync only changed orders since last sync",
    )
    full_sync_interval_days = fields.Integer(
        string="Full Sync Interval (Days)",
        default=7,
        help="Automatically do a full sync every X days (0 = never)",
    )
    sync_on_order_update = fields.Boolean(
        string="Sync on Order Update",
        default=True,
        help="Sync changes when orders are modified in WooCommerce",
    )

    # Automated Sync
    auto_sync = fields.Boolean(
        string="Auto Sync",
        default=False,
        help="Enable automatic synchronization via the scheduled cron job",
    )
    sync_interval = fields.Integer(
        string="Sync Interval (minutes)",
        default=60,
        help="Minimum minutes between automatic syncs for this instance",
    )
    next_auto_sync_date = fields.Datetime(
        string="Next Sync",
        compute="_compute_next_auto_sync_date",
        help="Estimated date/time of next automatic synchronization",
    )

    # Sync Statistics and Tracking
    last_sync_date = fields.Datetime(
        string="Last Sync Date",
        readonly=True,
        help="Date of last incremental synchronization",
    )
    last_full_sync_date = fields.Datetime(
        string="Last Full Sync Date",
        readonly=True,
        help="Date of last complete synchronization",
    )
    last_sync_order_count = fields.Integer(
        string="Last Sync Orders",
        readonly=True,
        help="Number of orders processed in last sync",
    )
    last_sync_created = fields.Integer(
        string="Last Sync Created",
        readonly=True,
        help="Orders created in last sync",
    )
    last_sync_updated = fields.Integer(
        string="Last Sync Updated",
        readonly=True,
        help="Orders updated in last sync",
    )
    sync_error_count = fields.Integer(
        string="Sync Error Count",
        readonly=True,
        help="Consecutive synchronization errors",
    )
    last_sync_error = fields.Text(
        string="Last Sync Error",
        readonly=True,
        help="Last synchronization error message",
    )
    sync_duration = fields.Float(
        string="Last Sync Duration (s)",
        readonly=True,
        help="Duration of last synchronization in seconds",
    )
    total_synced_orders = fields.Integer(
        string="Total Synced Orders",
        readonly=True,
        help="Total orders synchronized from this instance",
    )

    # Error Handling
    sync_retry_on_error = fields.Boolean(
        string="Retry on Error",
        default=True,
        help="Automatically retry synchronization after errors",
    )
    max_retry_attempts = fields.Integer(
        string="Max Retry Attempts",
        default=3,
        help="Maximum number of retry attempts before giving up",
    )

    # # Company
    # company_id = fields.Many2one(
    #     "res.company",
    #     string="Company",
    #     default=lambda self: self.env.company,
    #     help="Company this instance belongs to",
    # )

    # NOTE: Sales fields → woo_instance_sales.py
    # NOTE: Warehouse fields → woo_instance_warehouse.py

    # ── Coupon Sync Settings ─────────────────────────────────────────────────

    coupon_sync_status = fields.Selection(
        [
            ("any", "All Statuses"),
            ("publish", "Published"),
            ("draft", "Draft"),
            ("pending", "Pending Review"),
            ("private", "Private"),
        ],
        string="Coupon Status",
        default="any",
        help="Which coupon statuses to import from WooCommerce",
    )
    coupon_sync_expiry = fields.Selection(
        [
            ("all", "All Coupons"),
            ("active", "Active Only (not expired)"),
            ("expired", "Expired Only"),
        ],
        string="Coupon Expiry",
        default="all",
        help="Filter imported coupons by expiry date",
    )
    coupon_sync_mode = fields.Selection(
        [
            ("incremental", "Incremental (only new/changed)"),
            ("full", "Full (all coupons)"),
        ],
        string="Coupon Sync Mode",
        default="incremental",
        help="Incremental: only fetch coupons modified since the last sync.\n"
        "Full: fetch all coupons regardless of modification date.",
    )
    coupon_last_sync_date = fields.Datetime(
        string="Last Coupon Sync",
        readonly=True,
    )
    coupon_count = fields.Integer(
        string="Coupons",
        compute="_compute_statistics",
    )

    _sql_constraints = [
        (
            "name_unique",
            "unique(name, company_id)",
            "Instance name must be unique per company!",
        ),
    ]

    def _compute_statistics(self):
        """Compute statistics for each instance"""
        for record in self:
            domain_base = [("instance_id", "=", record.id)]
            record.order_count = self.env["odoo.wp.sync"].search_count(domain_base)
            record.pending_order_count = self.env["odoo.wp.sync"].search_count(
                domain_base + [("status", "=", "pending")]
            )
            record.completed_order_count = self.env["odoo.wp.sync"].search_count(
                domain_base + [("status", "=", "completed")]
            )
            record.woo_product_count = self.env["woo.product"].search_count(domain_base)
            record.woo_product_linked_count = self.env["woo.product"].search_count(
                domain_base + [("link_state", "=", "linked")]
            )
            record.coupon_count = self.env["woo.coupon"].search_count(domain_base)

    @api.constrains("wp_url")
    def _check_wp_url(self):
        """Validate WordPress URL format"""
        for record in self:
            if record.wp_url:
                # Basic URL validation
                if not record.wp_url.startswith(("http://", "https://")):
                    raise ValidationError(
                        _("WordPress URL must start with http:// or https://")
                    )

    @api.model_create_multi
    def create(self, vals_list):
        """Normalize URLs before creating records"""
        for vals in vals_list:
            if vals.get("wp_url"):
                vals["wp_url"] = vals["wp_url"].rstrip("/")
        return super().create(vals_list)

    def write(self, vals):
        """Normalize URLs before updating records"""
        if vals.get("wp_url"):
            vals["wp_url"] = vals["wp_url"].rstrip("/")
        return super().write(vals)

    def action_test_connection(self):
        """Test connection to WooCommerce API"""
        self.ensure_one()

        result = self.env["woo.service"].test_connection(self)

        if result.get("success"):
            self.write(
                {
                    "state": "connected",
                    "last_connection_test": fields.Datetime.now(),
                    "connection_message": "Connection successful",
                }
            )
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Connection Successful"),
                    "message": _("Successfully connected to %s") % self.name,
                    "type": "success",
                    "sticky": False,
                },
            }

        error_type = result.get("error")

        if error_type == "timeout":
            error_msg = _("Server timeout - took too long to respond")
            self._handle_connection_error(error_msg)
            return self._notification_error(_("Connection Timeout"), error_msg)

        if error_type == "connection":
            error_msg = _("Could not connect to server - check URL and network")
            self._handle_connection_error(error_msg)
            return self._notification_error(_("Connection Error"), error_msg)

        if error_type == "unexpected":
            error_msg = result.get("message", "Unknown error")
            self._handle_connection_error(error_msg)
            return self._notification_error(_("Unexpected Error"), error_msg)

        # HTTP response received but not 200
        response = result.get("response")
        error_msg = self._parse_error_response(response)
        self.write(
            {
                "state": "error",
                "last_connection_test": fields.Datetime.now(),
                "connection_message": error_msg,
            }
        )
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Connection Error"),
                "message": error_msg,
                "type": "danger",
                "sticky": True,
            },
        }

    def _parse_error_response(self, response):
        """Parse error message from API response"""
        status_messages = {
            400: "Bad Request - Invalid API parameters",
            401: "Authentication Failed - Invalid Consumer Key or Secret",
            403: "Access Denied - Check API permissions",
            404: "Not Found - Verify WooCommerce URL and REST API is enabled",
            500: "Server Error - WooCommerce server issue",
            502: "Bad Gateway - Server temporarily unavailable",
            503: "Service Unavailable - Server is down",
        }

        # Get friendly message based on status code
        if response.status_code in status_messages:
            return status_messages[response.status_code]

        # Try to parse JSON error
        try:
            error_data = response.json()
            message = error_data.get("message", "")
            # Clean HTML tags and entities
            message = re.sub("<[^<]+?>", "", message)
            message = re.sub("&[a-z]+;", "", message)
            message = message.strip()

            if message:
                return f"{message[:100]}..."
            else:
                return f"HTTP Error {response.status_code}"
        except Exception:
            # Clean response text from HTML
            text = re.sub("<[^<]+?>", "", response.text)
            text = text.strip()[:100]
            return (
                f"HTTP {response.status_code}: {text}..."
                if text
                else f"HTTP Error {response.status_code}"
            )

    def _handle_connection_error(self, message):
        """Handle connection error"""
        self.write(
            {
                "state": "error",
                "last_connection_test": fields.Datetime.now(),
                "connection_message": message,
            }
        )

    def _notification_error(self, title, message):
        """Return error notification action"""
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": title,
                "message": message,
                "type": "danger",
                "sticky": True,
            },
        }

    def action_view_orders(self):
        """Open orders related to this instance"""
        self.ensure_one()

        return {
            "type": "ir.actions.act_window",
            "name": _("Orders - %s") % self.name,
            "res_model": "odoo.wp.sync",
            "view_mode": "tree,form",
            "domain": [("instance_id", "=", self.id)],
            "context": {"default_instance_id": self.id},
        }

    def action_view_coupons(self):
        """Open coupons related to this instance"""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Coupons - %s") % self.name,
            "res_model": "woo.coupon",
            "view_mode": "kanban,tree,form",
            "domain": [("instance_id", "=", self.id)],
            "context": {"default_instance_id": self.id},
        }

    def action_view_pending_orders(self):
        """Open pending orders for this instance"""
        self.ensure_one()

        return {
            "type": "ir.actions.act_window",
            "name": _("Pending Orders - %s") % self.name,
            "res_model": "odoo.wp.sync",
            "view_mode": "tree,form",
            "domain": [("instance_id", "=", self.id), ("status", "=", "pending")],
            "context": {"default_instance_id": self.id},
        }

    def action_view_completed_orders(self):
        """Open completed orders for this instance"""
        self.ensure_one()

        return {
            "type": "ir.actions.act_window",
            "name": _("Completed Orders - %s") % self.name,
            "res_model": "odoo.wp.sync",
            "view_mode": "tree,form",
            "domain": [("instance_id", "=", self.id), ("status", "=", "completed")],
            "context": {"default_instance_id": self.id},
        }

    def action_sync_orders(self):
        """Opens the confirmation wizard before syncing orders."""

        self.ensure_one()

        if self.state != "connected":
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Not connected"),
                    "message": _("Instance '%s' is not connected.") % self.name,
                    "type": "warning",
                    "sticky": False,
                },
            }

        return self.env["confirmation.wizard"].create_confirmation(
            model_name="woo.instance",
            method_name="_do_sync_orders",
            title=_("Sync orders from WooCommerce?"),
            description=(
                f"This action will sync orders from <b>{self.name}</b> "
                "from WooCommerce into Odoo. Orders will be created/updated "
                "according to the sync configuration."
            ),
            record_id=self.id,
        )

    def _do_sync_orders(self):
        """Sync orders for this specific instance"""
        self.ensure_one()

        if self.state != "connected":
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Cannot Sync"),
                    "message": _(
                        "Instance %s is not connected. Please test connection first."
                    )
                    % self.name,
                    "type": "warning",
                    "sticky": True,
                },
            }

        result = (
            self.env["odoo.wp.sync"]
            .with_context(default_instance_id=self.id)
            .action_sync()
        )

        # Inject redirect to this instance's orders after the notification
        if result and result.get("type") == "ir.actions.client":
            result.setdefault("params", {})["next"] = {
                "type": "ir.actions.act_window",
                "name": _("WooCommerce Orders — %s") % self.name,
                "res_model": "odoo.wp.sync",
                "view_mode": "tree,form",
                "views": [[False, "tree"], [False, "form"]],
                "domain": [("instance_id", "=", self.id)],
                "context": {"default_instance_id": self.id},
                "target": "current",
            }

        return result

    def action_sync_coupons(self):
        """Opens the confirmation wizard before importing coupons from WooCommerce."""
        self.ensure_one()
        if self.state != "connected":
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Not connected"),
                    "message": _("Instance '%s' is not connected.") % self.name,
                    "type": "warning",
                    "sticky": False,
                },
            }

        status_label = dict(self._fields["coupon_sync_status"].selection).get(
            self.coupon_sync_status, self.coupon_sync_status
        )
        expiry_label = dict(self._fields["coupon_sync_expiry"].selection).get(
            self.coupon_sync_expiry, self.coupon_sync_expiry
        )
        mode_label = dict(self._fields["coupon_sync_mode"].selection).get(
            self.coupon_sync_mode, self.coupon_sync_mode
        )

        # Build incremental range description
        if self.coupon_sync_mode == "incremental" and self.coupon_last_sync_date:
            since_str = self.coupon_last_sync_date.strftime("%Y-%m-%d %H:%M")
            mode_detail = f"{mode_label} &mdash; changes since <b>{since_str}</b>"
        elif self.coupon_sync_mode == "incremental":
            mode_detail = (
                f"{mode_label} &mdash; <i>no previous sync, will fetch all</i>"
            )
        else:
            mode_detail = mode_label

        return self.env["confirmation.wizard"].create_confirmation(
            model_name="woo.instance",
            method_name="_do_sync_coupons",
            title=_("Import Coupons from WooCommerce?"),
            description=_(
                "This will import coupons from <b>%(instance)s</b>.<br/>"
                "<br/>"
                "<b>Mode:</b> %(mode)s<br/>"
                "<b>Status filter:</b> %(status)s<br/>"
                "<b>Expiry filter:</b> %(expiry)s<br/>"
                "<br/>"
                "Existing coupons (matched by WooCommerce ID) will be updated."
            )
            % {
                "instance": self.name,
                "mode": mode_detail,
                "status": status_label,
                "expiry": expiry_label,
            },
            record_id=self.id,
            dialog_size="small",
        )

    def _do_sync_coupons(self):
        """Import coupons from WooCommerce into Odoo."""
        from datetime import datetime, timezone

        self.ensure_one()

        if self.state != "connected":
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Cannot Sync"),
                    "message": _("Instance %s is not connected.") % self.name,
                    "type": "warning",
                    "sticky": False,
                },
            }

        # Build modified_after for incremental sync
        modified_after = None
        if self.coupon_sync_mode == "incremental" and self.coupon_last_sync_date:
            # WC expects ISO-8601 UTC — format: 2025-01-15T10:30:00
            modified_after = self.coupon_last_sync_date.strftime("%Y-%m-%dT%H:%M:%S")

        wc_coupons = self.env["woo.service"].fetch_coupons(
            self, status=self.coupon_sync_status, modified_after=modified_after
        )

        # Apply expiry filter (WC API has no native filter for this)
        now = datetime.now(timezone.utc)

        def _parse_wc_dt(exp_str):
            """Parse a WC GMT datetime string to a timezone-aware UTC datetime."""
            if not exp_str:
                return None
            exp_str = exp_str.strip()
            # Replace "Z" with "+00:00" so fromisoformat handles it
            if exp_str.endswith("Z"):
                exp_str = exp_str[:-1] + "+00:00"
            dt = datetime.fromisoformat(exp_str)
            # If WC returned a naive datetime, treat it as UTC
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt

        if self.coupon_sync_expiry == "active":

            def _is_active(c):
                exp_dt = _parse_wc_dt(c.get("date_expires_gmt"))
                if exp_dt is None:
                    return True
                try:
                    return exp_dt > now
                except TypeError:
                    return True

            wc_coupons = [c for c in wc_coupons if _is_active(c)]

        elif self.coupon_sync_expiry == "expired":

            def _is_expired(c):
                exp_dt = _parse_wc_dt(c.get("date_expires_gmt"))
                if exp_dt is None:
                    return False
                try:
                    return exp_dt < now
                except TypeError:
                    return False

            wc_coupons = [c for c in wc_coupons if _is_expired(c)]

        created = updated = 0
        WooCoupon = self.env["woo.coupon"]

        for wc in wc_coupons:
            existing = WooCoupon.search(
                [("instance_id", "=", self.id), ("woo_id", "=", wc.get("id"))],
                limit=1,
            )
            WooCoupon.from_woo_data(self, wc)
            if existing:
                updated += 1
            else:
                created += 1

        self.write({"coupon_last_sync_date": fields.Datetime.now()})

        total = created + updated
        _logger.info(
            "Coupon sync complete for '%s': %d total (%d created, %d updated)",
            self.name,
            total,
            created,
            updated,
        )

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Coupons Imported"),
                "message": _(
                    "%(total)d coupons imported from %(instance)s "
                    "(%(created)d new, %(updated)d updated)."
                )
                % {
                    "total": total,
                    "instance": self.name,
                    "created": created,
                    "updated": updated,
                },
                "type": "success",
                "sticky": False,
                "next": {
                    "type": "ir.actions.act_window",
                    "name": _("WooCommerce Coupons — %s") % self.name,
                    "res_model": "woo.coupon",
                    "view_mode": "kanban,tree,form",
                    "views": [[False, "kanban"], [False, "tree"], [False, "form"]],
                    "domain": [("instance_id", "=", self.id)],
                    "context": {"default_instance_id": self.id},
                    "target": "current",
                },
            },
        }

    def get_api_credentials(self):
        """Return API credentials for this instance"""
        self.ensure_one()
        return {
            "url": self.wp_url,
            "consumer_key": self.consumer_key,
            "consumer_secret": self.consumer_secret,
        }

    @api.model
    def get_default_instance(self):
        """Get default instance (first active instance)"""
        return self.search([("active", "=", True)], limit=1)

    def action_open_instance(self):
        """
        Open instance and redirect to orders if connected,
        otherwise show the configuration form
        """
        self.ensure_one()

        # Store as the active instance for the current user
        self.env.user.sudo().woo_active_instance_id = self

        # If instance is connected, redirect to orders
        if self.state == "connected":
            return {
                "type": "ir.actions.act_window",
                "name": _("Orders - %s") % self.name,
                "res_model": "odoo.wp.sync",
                "view_mode": "tree,form",
                "domain": [("instance_id", "=", self.id)],
                "context": {"default_instance_id": self.id},
            }

        # Otherwise, show the configuration form
        return {
            "type": "ir.actions.act_window",
            "res_model": "woo.instance",
            "view_mode": "form",
            "res_id": self.id,
            "target": "current",
        }

    def _should_do_full_sync(self):
        """
        Determine if a full synchronization should be performed

        :return: bool - True if full sync is needed
        """
        self.ensure_one()

        # If incremental is disabled, always do full sync
        if not self.incremental_enabled:
            return True

        # If never synced before, do full sync
        if not self.last_sync_date:
            return True

        # If full_sync_interval_days is set and time has passed
        if self.full_sync_interval_days > 0:
            from datetime import datetime, timedelta

            if self.last_full_sync_date:
                days_since_full = (datetime.now() - self.last_full_sync_date).days
                if days_since_full >= self.full_sync_interval_days:
                    _logger.info(
                        f"Full sync triggered for {self.name}: {days_since_full} days since last full sync"
                    )
                    return True
            else:
                # Never had a full sync
                return True

        # If forced full sync mode
        if self.sync_mode == "full":
            return True

        return False

    def _update_sync_statistics(
        self, created, updated, total, duration, error=None, sync_type=None
    ):
        """
        Update synchronization statistics

        :param created: Number of orders created
        :param updated: Number of orders updated
        :param total: Total orders processed
        :param duration: Duration in seconds
        :param error: Error message if any
        :param sync_type: 'full' or 'incremental' (determines if last_full_sync_date is updated)
        """
        self.ensure_one()

        now = fields.Datetime.now()
        vals = {
            "last_sync_date": now,
            "last_sync_order_count": total,
            "last_sync_created": created,
            "last_sync_updated": updated,
            "sync_duration": duration,
        }

        if error:
            vals.update(
                {
                    "sync_error_count": self.sync_error_count + 1,
                    "last_sync_error": error,
                }
            )
        else:
            # Success - reset error counter
            vals.update(
                {
                    "sync_error_count": 0,
                    "last_sync_error": False,
                }
            )

            # Update total synced orders (only on success)
            vals["total_synced_orders"] = self.order_count

        # Update last_full_sync_date when this was a full sync.
        # Check both the explicit sync_type parameter AND the legacy context flag
        # so that action_full_sync() (which sets context) also works correctly.
        is_full_sync = sync_type == "full" or self._context.get("full_sync")
        if is_full_sync and not error:
            vals["last_full_sync_date"] = now

        self.write(vals)

        # Log sync statistics
        if error:
            _logger.error(
                f"Sync error for {self.name}: {error}. "
                f"Consecutive errors: {self.sync_error_count + 1}"
            )
        else:
            _logger.info(
                f"Sync completed for {self.name}: "
                f"Created={created}, Updated={updated}, Total={total}, "
                f"Duration={duration:.2f}s"
            )

    def _reset_sync_errors(self):
        """Reset synchronization error counter"""
        self.ensure_one()
        self.write(
            {
                "sync_error_count": 0,
                "last_sync_error": False,
            }
        )

    def action_full_sync(self):
        """Force a full synchronization of all orders"""
        self.ensure_one()

        if self.state != "connected":
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Cannot Sync"),
                    "message": _(
                        "Instance %s is not connected. Please test connection first."
                    )
                    % self.name,
                    "type": "warning",
                    "sticky": True,
                },
            }

        # Call sync with full_sync flag in context
        return (
            self.env["odoo.wp.sync"]
            .with_context(default_instance_id=self.id, full_sync=True)
            .action_sync()
        )

    def action_reset_sync_stats(self):
        """Reset synchronization statistics"""
        self.ensure_one()
        self.write(
            {
                "last_sync_date": False,
                "last_full_sync_date": False,
                "last_sync_order_count": 0,
                "last_sync_created": 0,
                "last_sync_updated": 0,
                "sync_error_count": 0,
                "last_sync_error": False,
                "sync_duration": 0,
            }
        )

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Statistics Reset"),
                "message": _("Synchronization statistics have been reset"),
                "type": "success",
                "sticky": False,
            },
        }

    # ── Auto Sync ──────────────────────────────────────────────────────────────

    @api.depends("auto_sync", "last_sync_date", "sync_interval")
    def _compute_next_auto_sync_date(self):
        from datetime import timedelta

        for record in self:
            if not record.auto_sync or not record.last_sync_date:
                record.next_auto_sync_date = False
            else:
                interval = timedelta(minutes=record.sync_interval or 60)
                record.next_auto_sync_date = record.last_sync_date + interval

    def _is_sync_due(self):
        """Return True if this instance is due for an automatic sync."""
        self.ensure_one()
        if not self.auto_sync or self.state != "connected":
            return False
        if not self.last_sync_date:
            return True
        from datetime import timedelta

        interval = timedelta(minutes=self.sync_interval or 60)
        return (self.last_sync_date + interval) <= fields.Datetime.now()

    @api.model
    def _run_scheduled_sync(self):
        """
        Entry point for the cron job.
        Iterates all active, connected instances that have auto_sync=True
        and whose sync interval has elapsed, then triggers a sync for each.

        Each instance runs inside its own savepoint to prevent one failure
        from rolling back statistics already written for other instances.
        """
        instances = self.search(
            [
                ("active", "=", True),
                ("auto_sync", "=", True),
                ("state", "=", "connected"),
            ]
        )

        for instance in instances:
            if not instance._is_sync_due():
                _logger.debug(
                    "Auto sync skipped for instance '%s': interval not elapsed yet.",
                    instance.name,
                )
                continue

            # Skip instances that have hit the error ceiling and retry is disabled
            if (
                not instance.sync_retry_on_error
                and instance.max_retry_attempts > 0
                and instance.sync_error_count >= instance.max_retry_attempts
            ):
                _logger.warning(
                    "Auto sync SKIPPED for instance '%s': %d consecutive errors "
                    "(max_retry_attempts=%d, retry_on_error=False). "
                    "Reset the instance statistics to re-enable automatic sync.",
                    instance.name,
                    instance.sync_error_count,
                    instance.max_retry_attempts,
                )
                continue

            # Determine now whether this run should be a full sync so we can pass
            # the correct context to action_sync — _update_sync_statistics uses
            # that context flag to update last_full_sync_date.
            needs_full = instance._should_do_full_sync()
            ctx = {
                "default_instance_id": instance.id,
                "full_sync": needs_full,
            }

            try:
                # Use a savepoint so that a low-level DB error in this instance
                # does not roll back statistics already committed for previous ones.
                with self.env.cr.savepoint():
                    _logger.info(
                        "Auto sync starting for instance '%s' (type=%s).",
                        instance.name,
                        "full" if needs_full else "incremental",
                    )
                    self.env["odoo.wp.sync"].with_context(**ctx).action_sync()
                    _logger.info(
                        "Auto sync completed for instance '%s'.", instance.name
                    )
            except Exception:
                _logger.exception(
                    "Auto sync raised an unhandled exception for instance '%s'.",
                    instance.name,
                )

    def action_sync_products(self):
        """Opens the confirmation wizard before importing products."""
        self.ensure_one()

        if self.state != "connected":
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("No conectado"),
                    "message": _("Instance '%s' is not connected.") % self.name,
                    "type": "warning",
                    "sticky": False,
                },
            }

        return self.env["confirmation.wizard"].create_confirmation(
            model_name="woo.instance",
            method_name="_do_sync_products",
            title=_("Sync products from WooCommerce?"),
            description=(
                f"This action will download all products from <b>{self.name}</b> "
                "from WooCommerce and automatically link them to Odoo products "
                "that match by SKU.<br/><br/>"
                "Products already linked manually will not be overwritten."
            ),
            record_id=self.id,
            dialog_size="medium",
        )

    def _do_sync_products(self):
        """Runs the actual product import (called by the confirmation wizard)."""
        self.ensure_one()

        try:
            stats = self.env["woo.product.sync"].import_and_link(self)
        except Exception as e:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Error importing products"),
                    "message": str(e),
                    "type": "danger",
                    "sticky": True,
                },
            }

        message = (
            f"✅ Creados: {stats['created']} | "
            f"🔄 Actualizados: {stats['updated']} | "
            f"🔗 Vinculados: {stats['linked']} | "
            f"⚠️ Sin vincular: {stats['unlinked']}"
        )
        if stats["errors"]:
            message += f"\n❌ Errores: {stats['errors']}"

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Import completed"),
                "message": message,
                "type": "success" if not stats["errors"] else "warning",
                "sticky": True,
                "next": {
                    "type": "ir.actions.act_window",
                    "name": _("WooCommerce Products — %s") % self.name,
                    "res_model": "woo.product",
                    "view_mode": "tree,form",
                    "views": [[False, "tree"], [False, "form"]],
                    "domain": [("instance_id", "=", self.id)],
                    "context": {"default_instance_id": self.id},
                    "target": "current",
                },
            },
        }

    def action_view_woo_products(self):
        """Abre los productos WooCommerce de esta instancia."""
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "odoo_wp_sync.action_woo_product"
        )
        action["name"] = _("Productos WooCommerce — %s") % self.name
        action["domain"] = [("instance_id", "=", self.id)]
        action["context"] = {"default_instance_id": self.id}
        return action

    def action_view_woo_coupons(self):
        """Abre los cupones WooCommerce de esta instancia."""
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "odoo_wp_sync.action_woo_coupon"
        )
        action["name"] = _("Cupones WooCommerce — %s") % self.name
        action["domain"] = [("instance_id", "=", self.id)]
        action["context"] = {"default_instance_id": self.id}
        return action
