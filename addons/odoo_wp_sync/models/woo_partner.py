from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)


class WooPartner(models.AbstractModel):
    _name = "woo.partner"

    @api.model
    def create_partner_from_woo_data(self, woo_order_record):
        """
        Creates or updates a partner in Odoo from WooCommerce data.
        This method must be implemented by the concrete model that inherits from this abstract one.
        :param woo_order_record: odoo.wp.sync record with the WooCommerce partner data
        :return: The created or updated partner record in Odoo
        """

        # Use the instance's default client if configured
        default_client = woo_order_record.instance_id.client_id
        if default_client:
            _logger.debug(f"Using instance default client: {default_client.name}")
            return default_client

        Partner = self.env["res.partner"]

        # Buscar por email si existe
        if woo_order_record.customer_email:
            partner = Partner.search(
                [("email", "=", woo_order_record.customer_email)], limit=1
            )
            if partner:
                _logger.debug(f"Cliente encontrado por email: {partner.name}")
                return partner

        # Crear nuevo cliente
        partner_vals = {
            "name": woo_order_record.customer_name or "Cliente WooCommerce",
            "email": woo_order_record.customer_email,
            "phone": woo_order_record.customer_phone,
            "comment": f"Cliente importado desde WooCommerce - Order {woo_order_record.order_number}",
        }

        partner = Partner.create(partner_vals)
        _logger.info(f"Nuevo cliente creado: {partner.name}")

        return partner
