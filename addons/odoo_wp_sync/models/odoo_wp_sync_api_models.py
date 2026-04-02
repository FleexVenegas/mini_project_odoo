import requests
from odoo import models
from odoo.exceptions import UserError


class OdooWpSyncWCApi(models.AbstractModel):
    _name = "odoo.wp.sync.wc.api"
    _description = "WooCommerce API Service"

    def _get_wp_config(self, instance=None):
        """
        Get WooCommerce configuration.
        Priority:
        1. Instance parameter (preferred for multi-instance)
        2. Default instance
        3. Legacy config parameters (backward compatibility)
        """
        if instance:
            # Use instance credentials
            return instance.get_api_credentials()

        # Try to get default instance
        default_instance = self.env["woo.instance"].get_default_instance()
        if default_instance:
            return default_instance.get_api_credentials()

        # Fallback to legacy config parameters (backward compatibility)
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
            "No WooCommerce instance configured. "
            "Please create a WooCommerce instance in Settings > WooCommerce Instances"
        )

    def _wp_request(self, endpoint, method="GET", data=None, instance=None):
        """
        Make a request to WooCommerce API

        Args:
            endpoint: API endpoint (e.g., "orders", "products/123")
            method: HTTP method (GET, POST, PUT, DELETE)
            data: Request payload (for POST/PUT)
            instance: woo.instance record (optional, uses default if not provided)

        Returns:
            Response JSON data

        Raises:
            Exception: On API errors or connection issues
        """
        config = self._get_wp_config(instance)

        url = f"{config['url']}/wp-json/wc/v3/{endpoint}"

        try:
            response = requests.request(
                method,
                url,
                auth=(config["consumer_key"], config["consumer_secret"]),
                json=data,
                timeout=15,
            )

            if response.status_code in (200, 201):
                return response.json()

            # Handle errors
            try:
                error = response.json()
                message = error.get("message", "Error desconocido")
            except Exception:
                message = response.text

            raise Exception(f"[{response.status_code}] {message}")

        except requests.exceptions.RequestException as e:
            raise Exception(f"Error de conexión: {str(e)}")
