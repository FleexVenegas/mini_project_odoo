from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import requests
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

    # Technical
    color = fields.Integer(string="Color Index", default=0)

    # Synchronization Parameters - Basic
    sync_order_limit = fields.Integer(
        string="Orders per Sync",
        default=100,
        help="Maximum number of orders to sync per execution",
    )
    sync_days_back = fields.Integer(
        string="Days to Sync Back",
        default=30,
        help="Number of days back to sync orders from (0 = all orders)",
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
        help="Comma-separated list of statuses (e.g., pending,processing,completed)",
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
        help="Enable automatic synchronization (requires scheduled action)",
    )
    sync_interval = fields.Integer(
        string="Sync Interval (minutes)",
        default=60,
        help="Interval in minutes for automatic synchronization",
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

    # NOTE: Sales fields → woo_instance_sales.py
    # NOTE: Warehouse fields → woo_instance_warehouse.py

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

        try:
            response = requests.get(
                f"{self.wp_url}/wp-json/wc/v3/system_status",
                auth=(self.consumer_key, self.consumer_secret),
                timeout=10,
            )

            if response.status_code == 200:
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
            else:
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

        except requests.exceptions.Timeout:
            error_msg = _("Server timeout - took too long to respond")
            self._handle_connection_error(error_msg)
            return self._notification_error(_("Connection Timeout"), error_msg)

        except requests.exceptions.ConnectionError:
            error_msg = _("Could not connect to server - check URL and network")
            self._handle_connection_error(error_msg)
            return self._notification_error(_("Connection Error"), error_msg)

        except Exception as e:
            error_msg = str(e)
            self._handle_connection_error(error_msg)
            return self._notification_error(_("Unexpected Error"), error_msg)

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

        # Call the sync action from odoo.wp.sync model with instance context
        return (
            self.env["odoo.wp.sync"]
            .with_context(default_instance_id=self.id)
            .action_sync()
        )

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

    def _update_sync_statistics(self, created, updated, total, duration, error=None):
        """
        Update synchronization statistics

        :param created: Number of orders created
        :param updated: Number of orders updated
        :param total: Total orders processed
        :param duration: Duration in seconds
        :param error: Error message if any
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

        # Update last_full_sync_date if this was a full sync
        if self._context.get("full_sync"):
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
