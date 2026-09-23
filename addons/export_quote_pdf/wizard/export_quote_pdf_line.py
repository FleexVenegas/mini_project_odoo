from odoo import fields, models


class ExportQuotePdfLine(models.TransientModel):
    _name = 'export.quote.pdf.line'
    _description = 'Extracted Quote PDF Line'

    wizard_id = fields.Many2one(
        'export.quote.pdf.wizard',
        required=True,
        ondelete='cascade',
    )

    quantity = fields.Float(
        string='Cantidad',
    )

    uom = fields.Char(
        string='UM',
    )

    adventa_sku = fields.Char(
        string='SKU Adventa',
    )

    supplier_sku = fields.Char(
        string='SKU Proveedor',
    )

    description = fields.Text(
        string='Descripción',
    )

    unit_price = fields.Float(
        string='Precio unitario',
    )

    amount = fields.Float(
        string='Importe',
    )