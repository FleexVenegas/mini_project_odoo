import requests
from odoo import models


class OdooWpSyncWCApi(models.AbstractModel):
    _name = "odoo.wp.sync.wc.api"
    _description = "WooCommerce API Service"

    def _get_wp_config(self):
        params = self.env["ir.config_parameter"].sudo()
        return {
            "url": params.get_param("odoo_wp_sync.wp_url"),
            "ck": params.get_param("odoo_wp_sync.wp_ck"),
            "cs": params.get_param("odoo_wp_sync.wp_cs"),
        }

    def _wp_request(self, endpoint, method="GET", data=None):
        config = self._get_wp_config()

        url = f"{config['url']}/wp-json/wc/v3/{endpoint}"

        try:
            response = requests.request(
                method, url, auth=(config["ck"], config["cs"]), json=data, timeout=15
            )

            if response.status_code in (200, 201):
                return response.json()

            # manejo de error
            try:
                error = response.json()
                message = error.get("message", "Error desconocido")
            except Exception:
                message = response.text

            raise Exception(f"[{response.status_code}] {message}")

        except requests.exceptions.RequestException as e:
            raise Exception(f"Error de conexión: {str(e)}")
