"""
Centralized HTTP service for WooCommerce integration.

All HTTP communication with the WooCommerce API (REST v3) and the
WordPress API (wp/v2/media) goes through this service. Business models
(woo.product, odoo.wp.sync, etc.) NEVER import or use the ``requests``
library directly.
"""

import base64
import logging

import requests

from odoo import models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

_WC_PAGE_SIZE = 100  # maximum allowed by the WooCommerce API


class WooService(models.AbstractModel):
    _name = "woo.service"
    _description = "WooCommerce HTTP Integration Service"

    # ── Configuration ────────────────────────────────────────────────────────────

    def _get_config(self, instance=None):
        """
        Gets the WooCommerce connection credentials.

        Priority:
          1. Explicit instance (recommended for multi-instance).
          2. Default instance.
          3. Legacy ir.config_parameter parameters.
        """
        if instance:
            return instance.get_api_credentials()

        default_instance = self.env["woo.instance"].get_default_instance()
        if default_instance:
            return default_instance.get_api_credentials()

        # Fallback: legacy parameters (compatibility)
        params = self.env["ir.config_parameter"].sudo()
        url = params.get_param("odoo_wp_sync.wp_url")
        ck = params.get_param("odoo_wp_sync.wp_ck")
        cs = params.get_param("odoo_wp_sync.wp_cs")

        if url and ck and cs:
            return {
                "url": url,
                "consumer_key": ck,
                "consumer_secret": cs,
            }

        raise UserError(
            _(
                "No WooCommerce instance is configured. "
                "Create one in Settings → WooCommerce Instances."
            )
        )

    # ── Generic HTTP (WooCommerce REST v3) ────────────────────────────────────────

    def _request(self, endpoint, method="GET", data=None, instance=None, timeout=15):
        """
        Executes an HTTP request against the WC REST API v3.

        Args:
            endpoint: relative path (e.g. ``orders``, ``products/123``)
            method: GET | POST | PUT | DELETE
            data: payload dict (for POST/PUT)
            instance: ``woo.instance`` record (uses default if not provided)
            timeout: timeout in seconds (default 15)

        Returns:
            dict | list: response JSON

        Raises:
            Exception: API or connection errors
        """
        config = self._get_config(instance)
        url = f"{config['url']}/wp-json/wc/v3/{endpoint}"

        try:
            response = requests.request(
                method,
                url,
                auth=(config["consumer_key"], config["consumer_secret"]),
                json=data,
                timeout=timeout,
            )

            if response.status_code in (200, 201):
                return response.json()

            # Parsear error
            try:
                error = response.json()
                message = error.get("message", "Unknown error")
            except Exception:
                message = response.text

            raise Exception(f"[{response.status_code}] {message}")

        except requests.exceptions.RequestException as e:
            raise Exception(f"Connection error: {str(e)}")

    # ── Connection ───────────────────────────────────────────────────────────────

    def test_connection(self, instance):
        """
        Tests the connection with the WooCommerce API.

        Returns:
            dict with keys:
              - ``success``: bool
              - ``status_code``: int (only if there was an HTTP response)
              - ``response``: requests.Response (only if there was an HTTP response)
              - ``error``: str error type (``timeout``, ``connection``, ``unexpected``)
              - ``message``: str error detail
        """
        try:
            response = requests.get(
                f"{instance.wp_url}/wp-json/wc/v3/system_status",
                auth=(instance.consumer_key, instance.consumer_secret),
                timeout=10,
            )
            return {
                "success": response.status_code == 200,
                "status_code": response.status_code,
                "response": response,
            }
        except requests.exceptions.Timeout:
            return {"success": False, "error": "timeout"}
        except requests.exceptions.ConnectionError:
            return {"success": False, "error": "connection"}
        except Exception as e:
            return {"success": False, "error": "unexpected", "message": str(e)}

    # ── Media (WordPress REST v2) ────────────────────────────────────────────

    def upload_image(self, instance, image_b64, product_ref="new"):
        """
        Uploads a binary image (base64) to the WordPress Media Library.

        Args:
            instance: ``woo.instance`` record
            image_b64: image content encoded in base64
            product_ref: reference for the filename (woo_id or ``new``)

        Returns:
            tuple(int|None, str): ``(media_id, src_url)`` or ``(None, '')`` on failure
        """
        if not image_b64:
            return None, ""

        image_data = base64.b64decode(image_b64)

        # Detectar MIME por magic bytes
        if image_data[:4] == b"\x89PNG":
            mime, ext = "image/png", "png"
        elif image_data[:2] == b"\xff\xd8":
            mime, ext = "image/jpeg", "jpg"
        elif image_data[:4] == b"GIF8":
            mime, ext = "image/gif", "gif"
        elif image_data[:4] == b"RIFF" and image_data[8:12] == b"WEBP":
            mime, ext = "image/webp", "webp"
        else:
            mime, ext = "image/jpeg", "jpg"

        filename = f"woo_product_{product_ref}.{ext}"
        config = self._get_config(instance)
        url = f"{config['url']}/wp-json/wp/v2/media"

        try:
            response = requests.post(
                url,
                auth=(config["consumer_key"], config["consumer_secret"]),
                headers={
                    "Content-Disposition": f'attachment; filename="{filename}"',
                    "Content-Type": mime,
                },
                data=image_data,
                timeout=30,
            )
            if response.status_code in (200, 201):
                media = response.json()
                return media.get("id"), media.get("source_url", "")
            _logger.warning(
                "WP Media upload returned %s: %s",
                response.status_code,
                response.text[:300],
            )
        except Exception as exc:
            _logger.warning("Error uploading image to WordPress: %s", str(exc))

        return None, ""

    # ── Productos ────────────────────────────────────────────────────────────

    def create_product(self, instance, payload):
        """Creates a product in WooCommerce (POST ``products``)."""
        return self._request(
            endpoint="products",
            method="POST",
            data=payload,
            instance=instance,
        )

    def update_product(self, instance, woo_id, payload):
        """Updates a product in WooCommerce (PUT ``products/{id}``)."""
        return self._request(
            endpoint=f"products/{woo_id}",
            method="PUT",
            data=payload,
            instance=instance,
        )

    def fetch_products(self, instance):
        """
        Fetches all WooCommerce products with automatic pagination.

        Returns:
            list[dict]: complete list of WooCommerce products
        """
        all_products = []
        page = 1

        while True:
            endpoint = (
                f"products?per_page={_WC_PAGE_SIZE}&page={page}"
                f"&orderby=id&order=asc&status=any"
            )
            batch = self._request(endpoint=endpoint, instance=instance)
            if not batch:
                break
            all_products.extend(batch)
            if len(batch) < _WC_PAGE_SIZE:
                break
            page += 1

        _logger.info(
            "Fetched %d products from WooCommerce instance '%s'",
            len(all_products),
            instance.name,
        )
        return all_products

    # ── Orders ────────────────────────────────────────────────────────────────

    def fetch_orders(self, instance, params):
        """
        Fetches WooCommerce orders with automatic pagination.

        Args:
            instance: ``woo.instance`` record
            params: dict with query parameters (``per_page``, ``status``, …)

        Returns:
            list[dict]: list of WooCommerce orders
        """
        param_string = "&".join([f"{k}={v}" for k, v in params.items()])
        base_endpoint = f"orders?{param_string}"
        all_orders = []
        page = 1
        max_pages = 100

        while page <= max_pages:
            endpoint = f"{base_endpoint}&page={page}"
            orders = self._request(endpoint=endpoint, instance=instance)
            if not orders:
                break
            all_orders.extend(orders)
            if len(orders) < params.get("per_page", 50):
                break
            page += 1

        _logger.info(
            "Fetched %d orders from instance '%s' in %d page(s)",
            len(all_orders),
            instance.name,
            page,
        )
        return all_orders

    def update_order_status(self, instance, wc_order_id, new_status):
        """
        Updates the status of an order in WooCommerce.

        Args:
            instance: ``woo.instance`` record
            wc_order_id: WooCommerce order ID
            new_status: new status (``pending``, ``processing``, ``completed``, …)

        Returns:
            dict: WooCommerce JSON response
        """
        return self._request(
            endpoint=f"orders/{wc_order_id}",
            method="PUT",
            data={"status": new_status},
            instance=instance,
        )

    # ── Categories ───────────────────────────────────────────────────────────────

    def fetch_categories(self, instance):
        """
        Fetches all WooCommerce categories with automatic pagination.

        Returns:
            list[dict]: complete list of WooCommerce categories.
              Each item has: id, name, slug, parent (parent id, 0 if root)
        """
        all_categories = []
        page = 1

        while True:
            batch = self._request(
                endpoint=f"products/categories?per_page={_WC_PAGE_SIZE}&page={page}&orderby=id&order=asc",
                instance=instance,
            )
            if not batch:
                break
            all_categories.extend(batch)
            if len(batch) < _WC_PAGE_SIZE:
                break
            page += 1

        _logger.info(
            "Fetched %d categories from WooCommerce instance '%s'",
            len(all_categories),
            instance.name,
        )
        return all_categories

    # ── Brands ────────────────────────────────────────────────────────────────

    def fetch_brands(self, instance):
        """
        Fetches all WooCommerce brands with automatic pagination.

        Compatible with the most common endpoints:
          - ``/wc/v3/products/brands`` (Perfect WooCommerce Brands)
          - ``/wc/v3/brands`` (official WooCommerce Brands)

        Returns:
            list[dict] | []: list of brands, or empty list if the plugin is not active.
        """
        all_brands = []
        page = 1

        # Try the most common endpoint (Perfect WooCommerce Brands / official)
        try:
            while True:
                batch = self._request(
                    endpoint=f"products/brands?per_page={_WC_PAGE_SIZE}&page={page}",
                    instance=instance,
                )
                if not batch:
                    break
                all_brands.extend(batch)
                if len(batch) < _WC_PAGE_SIZE:
                    break
                page += 1
        except Exception:
            # The brands plugin is not installed or uses a different endpoint
            _logger.info(
                "No brand plugin found for instance '%s' (endpoint products/brands not available).",
                instance.name,
            )

        _logger.info(
            "Fetched %d brands from WooCommerce instance '%s'",
            len(all_brands),
            instance.name,
        )
        return all_brands
