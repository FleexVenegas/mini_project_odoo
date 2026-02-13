import logging
from odoo import models, fields

_logger = logging.getLogger(__name__)


class CategoryModel(models.Model):
    _name = "key.category"
    _description = "Categoría de Contraseñas"

    name = fields.Char(string="Nombre de la Categoría", required=True)
    description = fields.Text(string="Descripción")
