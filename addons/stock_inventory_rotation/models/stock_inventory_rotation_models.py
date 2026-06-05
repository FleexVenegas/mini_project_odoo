from odoo import api, fields, models

class StockInventoryRotation(models.Model):
    _inherit = 'stock.quant'

    last_sale_date = fields.Datetime(
        string='Ultima venta',
        compute='_compute_rotation_metrics',
        readonly=True,
        help='Fecha de la ultima venta confirmada para el producto.'
    )

    is_sold = fields.Boolean(
        string='Se vende',
        compute='_compute_rotation_metrics',
        readonly=True,
        help='Indica si el producto tiene al menos una venta confirmada.'
    )

    months_without_sale = fields.Integer(
        string='Meses sin vender',
        compute='_compute_rotation_metrics',
        readonly=True,
        help='Meses transcurridos desde la ultima venta confirmada.'
    )

    rotation_status = fields.Selection(
        [('active', 'Activa'),
         ('low', 'Baja'),
         ('very_low', 'Muy baja'),
         ('obsolete', 'Obsoleta'),
         ('never', 'Sin ventas')],
        string='Estado de rotacion',
        compute='_compute_rotation_metrics',
        readonly=True,
        help='Estado de rotacion basado en los meses sin vender.'
    )

    @api.depends('product_id', 'company_id')
    def _compute_rotation_metrics(self):
        for quant in self:
            quant.last_sale_date = False
            quant.is_sold = False
            quant.months_without_sale = 0
            quant.rotation_status = 'never'

        if not self:
            return

        products = self.mapped('product_id')
        if not products:
            return

        company_ids = self.mapped('company_id').ids or [self.env.company.id]
        product_ids = products.ids

        self.env.cr.execute(
            """
            SELECT sol.product_id, so.company_id, MAX(so.date_order)
              FROM sale_order_line sol
              JOIN sale_order so ON so.id = sol.order_id
             WHERE sol.product_id IN %s
               AND so.company_id IN %s
               AND so.state IN ('sale', 'done')
               AND sol.display_type IS NULL
          GROUP BY sol.product_id, so.company_id
            """,
            (tuple(product_ids), tuple(company_ids)),
        )
        sales_by_key = {
            (row[0], row[1]): row[2]
            for row in self.env.cr.fetchall()
        }

        today = fields.Date.context_today(self)
        for quant in self:
            company_id = quant.company_id.id or self.env.company.id
            last_sale = sales_by_key.get((quant.product_id.id, company_id))
            quant.last_sale_date = last_sale or False
            quant.is_sold = bool(last_sale)

            if not last_sale:
                quant.months_without_sale = 0
                quant.rotation_status = 'never'
                continue

            sale_date = fields.Datetime.to_datetime(last_sale).date()
            months = (today.year - sale_date.year) * 12 + (today.month - sale_date.month)
            if today.day < sale_date.day:
                months -= 1
            months = max(months, 0)
            quant.months_without_sale = months

            if months <= 1:
                quant.rotation_status = 'active'
            elif months <= 3:
                quant.rotation_status = 'low'
            elif months <= 6:
                quant.rotation_status = 'very_low'
            else:
                quant.rotation_status = 'obsolete'