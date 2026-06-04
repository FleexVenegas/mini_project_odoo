from odoo import models, fields

class StockInventoryRotation(models.Model):
    _inherit = 'product.template'

    last_sale_date = fields.Datetime(
        string='Last Sale Date',
        help='The date and time of the last sale of this product.'
    )

    months_without_sale = fields.Integer(
        string='Months Without Sale',
        help='The number of months since the last sale of this product.'
    )

    rotation_status = fields.Selection(
        [('active', 'Active'),
         ('low', 'Low'),
         ('very_low', 'Very Low'),
         ('obsolete', 'Obsolete'),
         ('never', 'Never')],
        string='Rotation Status',
        help='The rotation status of the product based on its sales history.'
    )