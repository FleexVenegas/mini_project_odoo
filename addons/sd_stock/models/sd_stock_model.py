from odoo import models, fields, _
from odoo.exceptions import UserError

import logging

_logger = logging.getLogger(__name__)


class SDStock(models.Model):
    _name = "sd.stock"
    _description = "SD Stock - External Stores Inventory"

    pass

