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
        
        _logger.error(
            f"Data {woo_order_record}: No default client configured"
        )

        Partner = self.env["res.partner"]

        # Search by email if it exists
        if woo_order_record.customer_email:
            partner = Partner.search(
                [("email", "=", woo_order_record.customer_email)], limit=1
            )
            if partner:
                _logger.debug(f"Customer found by email: {partner.name}")
                return partner

        # Create new customer


        # TODO Implement logic to extract the partner's name from the order data, as WooCommerce does not provide a separate field for the customer's name. For now, we will use the email or a default name if the email is not available.

        partner_vals = {
            "name": woo_order_record.customer_name or "WooCommerce Customer",
            "email": woo_order_record.customer_email,
            "phone": woo_order_record.customer_phone,
            "street": woo_order_record.address_1,
            "street2": woo_order_record.address_2,
            "city": woo_order_record.city,
            "state_id": self.env["res.country.state"].search(
                [("code", "=", woo_order_record.state)], limit=1
            ).id
            if woo_order_record.state else None,
            "zip": woo_order_record.postcode,
            "country_id": self.env["res.country"].search(
                [("code", "=", woo_order_record.country)], limit=1
            ).id if woo_order_record.country else None,
            "comment": f"Customer imported from WooCommerce - Order {woo_order_record.order_number}",
        }

        partner = Partner.create(partner_vals)
        _logger.info(f"New customer created: {partner.name}")

        return partner
