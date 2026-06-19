# -*- coding: utf-8 -*-
from odoo import models, fields, api
from dateutil.relativedelta import relativedelta
import logging
_logger = logging.getLogger(__name__)


class ProductProduct(models.Model):
    _inherit = 'product.product'

    # ── Sell-Through a 6 meses ──────────────────────────────────────────────
    sell_through_6m = fields.Float(
        string='Sell-Through 6m (%)',
        compute='_compute_sell_through_6m',
        digits=(5, 2),
        store=False,
        help='(Unidades vendidas últimos 6 meses / Stock inicial hace 6 meses)',
    )
    sell_through_6m_sold = fields.Float(
        string='Vendido 6m (uds)',
        compute='_compute_sell_through_6m',
        store=False,
    )
    sell_through_6m_initial_stock = fields.Float(
        string='Stock inicial 6m (uds)',
        compute='_compute_sell_through_6m',
        store=False,
    )

    sell_through_6m_available_stock = fields.Float(
        string='Disponible 6m (uds)',
        compute='_compute_sell_through_6m',
        store=False,
    )

    # ── Sell-Through a 9 meses ──────────────────────────────────────────────
    sell_through_9m = fields.Float(
        string='Sell-Through 9m (%)',
        compute='_compute_sell_through_9m',
        digits=(5, 2),
        store=False,
        help='(Unidades vendidas últimos 9 meses / Stock inicial hace 9 meses)',
    )
    sell_through_9m_sold = fields.Float(
        string='Vendido 9m (uds)',
        compute='_compute_sell_through_9m',
        store=False,
    )
    sell_through_9m_initial_stock = fields.Float(
        string='Stock inicial 9m (uds)',
        compute='_compute_sell_through_9m',
        store=False,
    )

    # ── Helpers privados ────────────────────────────────────────────────────

    def _get_warehouse_internal_location_ids(self):
        
        ctx = self.env.context
        
        # Odoo puede inyectar el warehouse con distintas keys según el módulo/vista
        warehouse_id = (
            ctx.get('warehouse_id')
            or ctx.get('warehouse')
            or ctx.get('default_warehouse_id')
        )

        _logger.info("_get_warehouse_internal_location_ids : warehouse_id=%s", warehouse_id)

        if not warehouse_id and ctx.get('active_model') == 'stock.warehouse':
            warehouse_id = ctx.get('active_id')
        
        if not warehouse_id:
            return None
        
        warehouse = self.env['stock.warehouse'].browse(int(warehouse_id)).exists()
        if not warehouse or not warehouse.lot_stock_id:
            return []

        return self.env['stock.location'].search([
            # ('id', 'child_of', warehouse.lot_stock_id.id),
            ('id', 'child_of', warehouse.view_location_id.id),
            ('usage', '=', 'internal'),
        ]).ids


    def _get_sold_qty(self, product_ids, date_from, date_to, location_ids=None):
        query = """
            SELECT
                sm.product_id,
                SUM(sm.quantity) AS qty
            FROM stock_move sm
            JOIN stock_location src ON src.id = sm.location_id
            JOIN stock_location dest ON dest.id = sm.location_dest_id
            WHERE sm.state = 'done'
              AND sm.product_id = ANY(%s)
              AND sm.company_id = %s
              AND src.usage IN ('internal', 'transit')
              AND dest.usage = 'customer'
              AND sm.date >= %s
              AND sm.date <  %s
        """
        params = [product_ids, self.env.company.id, date_from, date_to]

        if location_ids is not None:
            query += "\n              AND sm.location_id = ANY(%s)"
            params.append(location_ids)

        query += "\n            GROUP BY sm.product_id"

        self.env.cr.execute(query, params)
        return {row[0]: row[1] for row in self.env.cr.fetchall()}

    def _get_moves_in_period(self, product_ids, date_from, date_to, location_ids=None):
        query = """
            SELECT
                sm.product_id,
                SUM(
                    CASE WHEN src.usage = 'supplier'
                    AND dest.usage = 'internal'
                    THEN sm.quantity ELSE 0 END
                ) AS qty_in,

                SUM(
                    CASE WHEN src.usage = 'internal'
                    AND dest.usage = 'customer'
                    THEN sm.quantity ELSE 0 END
                ) AS qty_out

            FROM stock_move sm
            JOIN stock_location src ON src.id = sm.location_id
            JOIN stock_location dest ON dest.id = sm.location_dest_id

            WHERE sm.state = 'done'
            AND sm.product_id = ANY(%s)
            AND sm.company_id = %s
            AND sm.date >= %s
            AND sm.date < %s
        """
        params = [product_ids, self.env.company.id, date_from, date_to]

        if location_ids is not None:
            query += "\n            AND (sm.location_id = ANY(%s) OR sm.location_dest_id = ANY(%s))"
            params.extend([location_ids, location_ids])

        query += "\n            GROUP BY sm.product_id;"

        self.env.cr.execute(query, params)
        return {
            row[0]: {'in': row[1] or 0.0, 'out': row[2] or 0.0}
            for row in self.env.cr.fetchall()
        }

    def _get_current_stock(self, product_ids, location_ids=None):

        query = """
            SELECT sq.product_id, SUM(sq.quantity) AS qty
            FROM stock_quant sq
            JOIN stock_location loc ON loc.id = sq.location_id
            WHERE sq.product_id = ANY(%s)
            AND loc.usage = 'internal'
            AND (sq.company_id IS NULL OR sq.company_id = %s)
        """
        params = [product_ids, self.env.company.id]

        if location_ids is not None:
            query += "\n            AND sq.location_id = ANY(%s)"
            params.append(location_ids)

        query += "\n            GROUP BY sq.product_id"

        self.env.cr.execute(query, params)
        rows = self.env.cr.fetchall()
        _logger.info("_get_current_stock result=%s", rows)
        return {row[0]: row[1] or 0.0 for row in rows}

    def _compute_sell_through(self, months):
        # Usar datetime evita cortar el periodo a las 00:00 y perder movimientos del dia.
        date_to = fields.Datetime.now()
        date_from = date_to - relativedelta(months=months)
        location_ids = self._get_warehouse_internal_location_ids()


        _logger.info("_compute_sell_through location_ids=%s", location_ids)


        product_ids = self.ids
        if not product_ids:
            return {}

        sold_map    = self._get_sold_qty(product_ids, date_from, date_to, location_ids=location_ids)
        moves_map   = self._get_moves_in_period(product_ids, date_from, date_to, location_ids=location_ids)
        current_map = self._get_current_stock(product_ids, location_ids=location_ids)

        result = {}
        for product in self:
            pid     = product.id
            current = current_map.get(pid, 0.0)
            moves   = moves_map.get(pid, {'in': 0.0, 'out': 0.0})
            sold    = sold_map.get(pid, 0.0)

            initial = max(current - moves['in'] + moves['out'], 0.0)

            available = initial + moves['in']

            rate = round(sold / available, 4) if available > 0 else 0.0

            result[pid] = {
                'sold': sold,
                'initial': initial,
                'available': available,
                'rate': rate,
            }

        return result

    # ── Compute methods ─────────────────────────────────────────────────────

    @api.depends_context('company', 'allowed_company_ids', 'warehouse', 'warehouse_id', 'active_model', 'active_id')
    def _compute_sell_through_6m(self):

        _logger.info("wareouse=: %s", self.env.context.get('warehouse'),)


        data = self._compute_sell_through(months=6)

        for product in self:
            d = data.get(product.id, {})
            product.sell_through_6m               = d.get('rate', 0.0)
            product.sell_through_6m_sold          = d.get('sold', 0.0)
            product.sell_through_6m_initial_stock = d.get('initial', 0.0)
            product.sell_through_6m_available_stock = d.get('available', 0.0)
    
    @api.depends_context('company', 'allowed_company_ids', 'warehouse', 'warehouse_id', 'active_model', 'active_id')
    def _compute_sell_through_9m(self):
        data = self._compute_sell_through(months=12)
        for product in self:
            d = data.get(product.id, {})
            product.sell_through_9m               = d.get('rate', 0.0)
            product.sell_through_9m_sold          = d.get('sold', 0.0)
            product.sell_through_9m_initial_stock = d.get('initial', 0.0)