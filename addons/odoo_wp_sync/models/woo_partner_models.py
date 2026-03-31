from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)


class WooPartner(models.AbstractModel):
    _name = "woo.partner"

    @api.model
    def create_partner_from_woo_data(self, woo_order_record):
        """
        Crea o actualiza un partner en Odoo a partir de los datos de WooCommerce.
        Este método debe ser implementado por el modelo concreto que herede de este abstracto.
        :param woo_order_record: Registro de odoo.wp.sync con los datos del partner de WooCommerce
        :return: Registro del partner creado o actualizado en Odoo
        """

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
