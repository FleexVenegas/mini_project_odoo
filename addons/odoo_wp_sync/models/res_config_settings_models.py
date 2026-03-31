from odoo import models, fields, api
import requests
import re


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    wp_url = fields.Char(
        string="WordPress API URL", config_parameter="odoo_wp_sync.wp_url"
    )
    wp_ck = fields.Char(string="Consumer Key", config_parameter="odoo_wp_sync.wp_ck")
    wp_cs = fields.Char(string="Consumer Secret", config_parameter="odoo_wp_sync.wp_cs")

    def action_test_connection(self):
        """Test WordPress/WooCommerce connection"""
        # Get configuration parameters directly from system
        ICP = self.env["ir.config_parameter"].sudo()
        wp_url = ICP.get_param("odoo_wp_sync.wp_url", "")
        wp_ck = ICP.get_param("odoo_wp_sync.wp_ck", "")
        wp_cs = ICP.get_param("odoo_wp_sync.wp_cs", "")

        if not wp_url:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Error de Configuración",
                    "message": "Por favor configure la URL de WordPress primero",
                    "type": "warning",
                },
            }

        try:
            response = requests.get(
                f"{wp_url}/wp-json/wc/v3/system_status",
                auth=(wp_ck, wp_cs) if wp_ck and wp_cs else None,
                timeout=10,
            )

            if response.status_code == 200:
                return {
                    "type": "ir.actions.client",
                    "tag": "display_notification",
                    "params": {
                        "title": "Conexión exitosa",
                        "message": "La conexión con WordPress/WooCommerce fue exitosa",
                        "type": "success",
                    },
                }

            try:
                error_data = response.json()
                message = error_data.get("message", "Error desconocido")

                # limpiar HTML
                message = re.sub("<[^<]+?>", "", message)

            except Exception:
                message = response.text

            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": f"Error {response.status_code}",
                    "message": message,
                    "type": "danger",
                },
            }

        except requests.exceptions.Timeout:
            message = "El servidor tardó demasiado en responder"

        except requests.exceptions.ConnectionError:
            message = "No se pudo conectar al servidor"

        except Exception as e:
            message = str(e)

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Error de conexión",
                "message": message,
                "type": "danger",
            },
        }
