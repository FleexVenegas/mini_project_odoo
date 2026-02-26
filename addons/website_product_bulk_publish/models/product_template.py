# Copyright 2024 Diego Venegas
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

import logging

from odoo import _, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    """Extend product.template to add bulk publish/unpublish actions."""

    _inherit = "product.template"

    def action_publish_on_website(self):
        """
        Publish selected products on the website.

        This method sets is_published=True for all selected products in a single
        write operation. It also shows a notification to the user with the number
        of products published.

        :raises UserError: If no products are selected or none can be published.
        :return: Notification action with success message.
        :rtype: dict
        """
        if not self:
            raise UserError(_("No products selected."))

        # Filter products that are not already published
        products_to_publish = self.filtered(lambda p: not p.is_published)

        if not products_to_publish:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Information"),
                    "message": _("All selected products are already published."),
                    "type": "info",
                    "sticky": False,
                },
            }

        # Bulk write operation for better performance
        products_to_publish.write({"is_published": True})

        _logger.info(
            "Published %d product(s) on website: %s",
            len(products_to_publish),
            products_to_publish.mapped("name"),
        )

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Success"),
                "message": _("%d product(s) published on website.", len(products_to_publish)),
                "type": "success",
                "sticky": False,
            },
        }

    def action_unpublish_from_website(self):
        """
        Unpublish selected products from the website.

        This method sets is_published=False for all selected products in a single
        write operation. It also shows a notification to the user with the number
        of products unpublished.

        :raises UserError: If no products are selected or none can be unpublished.
        :return: Notification action with success message.
        :rtype: dict
        """
        if not self:
            raise UserError(_("No products selected."))

        # Filter products that are currently published
        products_to_unpublish = self.filtered(lambda p: p.is_published)

        if not products_to_unpublish:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Information"),
                    "message": _("All selected products are already unpublished."),
                    "type": "info",
                    "sticky": False,
                },
            }

        # Bulk write operation for better performance
        products_to_unpublish.write({"is_published": False})

        _logger.info(
            "Unpublished %d product(s) from website: %s",
            len(products_to_unpublish),
            products_to_unpublish.mapped("name"),
        )

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Success"),
                "message": _("%d product(s) unpublished from website.", len(products_to_unpublish)),
                "type": "success",
                "sticky": False,
            },
        }
