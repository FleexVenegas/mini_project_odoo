# from odoo import api, fields, models

# class StockInventoryRotation(models.Model):
#     _inherit = 'product.product'

#     last_sale_date = fields.Datetime(
#         string='Ultima venta',
#         compute='_compute_rotation_metrics',
#         readonly=True,
#         help='Fecha de la ultima venta confirmada para el producto.'
#     )

#     is_sold = fields.Boolean(
#         string='Se vende',
#         compute='_compute_rotation_metrics',
#         readonly=True,
#         help='Indica si el producto tiene al menos una venta confirmada.'
#     )

#     months_without_sale = fields.Integer(
#         string='Meses sin vender',
#         compute='_compute_rotation_metrics',
#         readonly=True,
#         help='Meses transcurridos desde la ultima venta confirmada.'
#     )

#     rotation_status = fields.Selection(
#         [('active', 'Activa'),
#          ('low', 'Baja'),
#          ('very_low', 'Muy baja'),
#          ('obsolete', 'Obsoleta'),
#          ('never', 'Sin ventas')],
#         string='Estado de rotacion',
#         compute='_compute_rotation_metrics',
#         readonly=True,
#         help='Estado de rotacion basado en los meses sin vender.'
#     )

#     @api.depends_context('company')
#     def _compute_rotation_metrics(self):
#         for product in self:
#             product.last_sale_date = False
#             product.is_sold = False
#             product.months_without_sale = 0
#             product.rotation_status = 'never'

#         if not self.ids:
#             return

#         product_ids = self.ids
#         company_id = self.env.company.id

#         self.env.cr.execute(
#             """
#             SELECT sol.product_id, MAX(so.date_order)
#               FROM sale_order_line sol
#               JOIN sale_order so ON so.id = sol.order_id
#              WHERE sol.product_id IN %s
#                AND so.company_id = %s
#                AND so.state IN ('sale', 'done')
#                AND sol.display_type IS NULL
#           GROUP BY sol.product_id
#             """,
#             (tuple(product_ids), company_id),
#         )
#         sales_by_key = {
#             row[0]: row[1]
#             for row in self.env.cr.fetchall()
#         }

#         today = fields.Date.context_today(self)
#         for product in self:
#             last_sale = sales_by_key.get(product.id)
#             product.last_sale_date = last_sale or False
#             product.is_sold = bool(last_sale)

#             if not last_sale:
#                 product.months_without_sale = 0
#                 product.rotation_status = 'never'
#                 continue

#             sale_date = fields.Datetime.to_datetime(last_sale).date()
#             months = (today.year - sale_date.year) * 12 + (today.month - sale_date.month)
#             if today.day < sale_date.day:
#                 months -= 1
#             months = max(months, 0)
#             product.months_without_sale = months

#             if months <= 1:
#                 product.rotation_status = 'active'
#             elif months <= 3:
#                 product.rotation_status = 'low'
#             elif months <= 6:
#                 product.rotation_status = 'very_low'
#             else:
#                 product.rotation_status = 'obsolete'





from odoo import api, fields, models
from datetime import timedelta
import math


_ROTATION_GROUP = 'stock_inventory_rotation.group_stock_rotation_visibility'


# Caps configurables (podrían moverse a res.config.settings en el futuro)
_FREQ_CAP = 20    # órdenes en 90d que representan "máxima frecuencia"
_VOL_CAP  = 200   # unidades en 90d que representan "máximo volumen"
_MAX_DAYS = 365   # días sin venta a partir del cual recency = 0


class ProductProduct(models.Model):
    _inherit = 'product.product'

    # ----------------------------
    # BASE: última venta
    # ----------------------------
    last_sale_date = fields.Datetime(
        string='Última venta',
        compute='_compute_sales_rotation',
        store=False,
        groups=_ROTATION_GROUP,
    )
    last_sale_days = fields.Integer(
        string='Días desde última venta',
        compute='_compute_sales_rotation',
        store=False,
        groups=_ROTATION_GROUP,
    )

    # ----------------------------
    # VOLUMEN (últimos 90 días)
    # ----------------------------
    sales_count_90d = fields.Integer(
        string='Órdenes (90d)',
        compute='_compute_sales_rotation',
        store=False,
        groups=_ROTATION_GROUP,
    )
    sales_qty_90d = fields.Float(
        string='Cantidad vendida (90d)',
        compute='_compute_sales_rotation',
        store=False,
        groups=_ROTATION_GROUP,
    )

    # ----------------------------
    # TOTAL HISTÓRICO
    # ----------------------------
    sales_count_total = fields.Integer(
        string='Órdenes totales',
        compute='_compute_sales_rotation',
        store=False,
        groups=_ROTATION_GROUP,
    )

    # ----------------------------
    # SCORE (0–100) y STATUS
    # ----------------------------
    rotation_score = fields.Float(
        string='Score de rotación',
        compute='_compute_sales_rotation',
        store=False,
        groups=_ROTATION_GROUP,
    )
    rotation_status = fields.Selection(
        [
            ('fast',   'Alta rotación'),
            ('stable', 'Estable'),
            ('slow',   'Lenta'),
            ('dead',   'Sin demanda'),
        ],
        string='Estado de rotación',
        compute='_compute_sales_rotation',
        store=False,
        groups=_ROTATION_GROUP,
    )

    # ----------------------------
    # COMPUTE
    # ----------------------------
    @api.depends_context('company')
    def _compute_sales_rotation(self):
        self._reset_rotation_fields()

        product_ids = self.ids
        if not product_ids:
            return

        company_id = self.env.company.id
        today = fields.Datetime.now()
        limit_90d = today - timedelta(days=90)

        data = self._fetch_rotation_data(product_ids, company_id, limit_90d)

        for p in self:
            row = data.get(p.id)
            if not row:
                continue

            last_sale = fields.Datetime.from_string(str(row['last_sale'])) \
                if row['last_sale'] else False

            p.last_sale_date    = last_sale
            p.last_sale_days    = (today - last_sale).days if last_sale else _MAX_DAYS
            p.sales_count_total = row['total']
            p.sales_count_90d   = row['count_90d']
            p.sales_qty_90d     = row['qty_90d']
            p.rotation_score    = self._calc_score(p)
            p.rotation_status   = self._classify(p.rotation_score)

    # ----------------------------
    # HELPERS
    # ----------------------------
    def _reset_rotation_fields(self):
        """Resetea todos los campos calculados a sus valores neutros."""
        for p in self:
            p.last_sale_date    = False
            p.last_sale_days    = _MAX_DAYS
            p.sales_count_90d   = 0
            p.sales_qty_90d     = 0.0
            p.sales_count_total = 0
            p.rotation_score    = 0.0
            p.rotation_status   = 'dead'

    def _fetch_rotation_data(self, product_ids, company_id, limit_90d):
        """
        Ejecuta la query y devuelve un dict {product_id: {...}}.
        Se usa una lista Python para evitar el problema de tupla de un solo elemento.
        """
        # psycopg2 acepta listas directamente con ANY(), evitando el bug de (id,)
        self.env.cr.execute("""
            SELECT
                sol.product_id,
                MAX(so.date_order)                                          AS last_sale,
                COUNT(*)                                                    AS total_lines,
                COUNT(*) FILTER (WHERE so.date_order >= %s)                 AS count_90d,
                COALESCE(
                    SUM(sol.product_uom_qty) FILTER (WHERE so.date_order >= %s),
                    0
                )                                                           AS qty_90d
            FROM sale_order_line  sol
            JOIN sale_order       so  ON so.id = sol.order_id
            WHERE sol.product_id = ANY(%s)
              AND so.company_id  = %s
              AND so.state       IN ('sale', 'done')
              AND sol.display_type IS NULL
            GROUP BY sol.product_id
        """, (limit_90d, limit_90d, product_ids, company_id))

        return {
            row[0]: {
                'last_sale':  row[1],
                'total':      row[2],
                'count_90d':  row[3] or 0,
                'qty_90d':    float(row[4] or 0),
            }
            for row in self.env.cr.fetchall()
        }

    @staticmethod
    def _calc_score(p):
        """
        Score 0–100 usando escala logarítmica para recency y caps para
        frequency/volume, evitando saturación prematura.

        Recency (40 %): decaimiento logarítmico — penaliza más los primeros
        días inactivos que los últimos, hasta _MAX_DAYS donde llega a 0.
        Frequency (30 %): órdenes_90d / _FREQ_CAP, capped a 1.
        Volume (30 %): qty_90d / _VOL_CAP, capped a 1.
        """
        days = p.last_sale_days or _MAX_DAYS

        # Recency: 100 si vendido hoy, 0 si >= _MAX_DAYS, curva log entre medio
        if days >= _MAX_DAYS:
            recency = 0.0
        else:
            recency = max(0.0, 1.0 - math.log1p(days) / math.log1p(_MAX_DAYS))

        frequency = min(p.sales_count_90d / _FREQ_CAP, 1.0)
        volume    = min(p.sales_qty_90d   / _VOL_CAP,  1.0)

        score = (recency * 0.40 + frequency * 0.30 + volume * 0.30) * 100
        return round(score, 2)

    @staticmethod
    def _classify(score):
        if score >= 70:
            return 'fast'
        if score >= 40:
            return 'stable'
        if score > 0:
            return 'slow'
        return 'dead'