from odoo import models, fields, api, _
from odoo.exceptions import UserError
from ..utils.woo_mapper_state import map_state_code_mx
import json
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

        # Extract shipping address for potential use in partner creation
        shipping = (
            json.loads(woo_order_record.shipping_address)
            if woo_order_record.shipping_address
            else {}
        )

        if default_client:
            _logger.debug(f"Using instance default client: {default_client.name}")
            return default_client

        _logger.error(f"Data {woo_order_record}: No default client configured")

        Partner = self.env["res.partner"]

        # Search by email if it exists
        if woo_order_record.customer_email:
            partner = Partner.search(
                [("email", "=", woo_order_record.customer_email)], limit=1
            )
            if partner:
                _logger.debug(f"Customer found by email: {partner.name}")
                return partner

        # Map state code if it's from Mexico to improve matching with Odoo states
        state_code = map_state_code_mx(shipping.get("state"))

        # Resolve country
        country = self.env["res.country"].search(
            [("code", "=", shipping.get("country"))], limit=1
        )

        # Resolve state
        state = (
            self.env["res.country.state"].search(
                [("code", "=", state_code), ("country_id", "=", country.id)],
                limit=1,
            )
            if state_code and country
            else self.env["res.country.state"]
        )

        # Create new customer
        partner_vals = {
            "name": (woo_order_record.customer_name or "WooCommerce Customer").upper(),
            "email": woo_order_record.customer_email,
            "phone": woo_order_record.customer_phone,
            "street": shipping.get("address_1"),
            "street2": shipping.get("address_2"),
            "city": shipping.get("city"),
            "zip": shipping.get("postcode"),
            "country_id": country.id or False,
            "state_id": state.id or False,
            "comment": f"Cliente importado desde WooCommerce - Orden {woo_order_record.order_number}",
        }

        partner = Partner.create(partner_vals)
        _logger.info(f"New customer created: {partner.name}")

        return partner
