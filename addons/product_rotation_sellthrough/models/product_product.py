# -*- coding: utf-8 -*-
from odoo import models, fields, api
from dateutil.relativedelta import relativedelta


class ProductProduct(models.Model):
    _inherit = 'product.product'

    sell_through_6m = fields.Float(
        string='Sell-Through 6m (%)',
        compute='_compute_sell_through_6m',
        digits=(5, 2),
        store=False,
        help='Vendido / (Stock al inicio del periodo + entradas del periodo)',
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

    sell_through_9m = fields.Float(
        string='Sell-Through 12m (%)',
        compute='_compute_sell_through_9m',
        digits=(5, 2),
        store=False,
        help='Vendido / (Stock al inicio del periodo + entradas del periodo)',
    )
    sell_through_9m_sold = fields.Float(
        string='Vendido 12m (uds)',
        compute='_compute_sell_through_9m',
        store=False,
    )
    sell_through_9m_initial_stock = fields.Float(
        string='Stock inicial 12m (uds)',
        compute='_compute_sell_through_9m',
        store=False,
    )
    sell_through_9m_available_stock = fields.Float(
        string='Disponible 12m (uds)',
        compute='_compute_sell_through_9m',
        store=False,
    )

    def _get_warehouse_id(self):
        ctx = self.env.context
        warehouse_id = (
            ctx.get('warehouse_id')
            or ctx.get('warehouse')
            or ctx.get('default_warehouse_id')
        )
        if not warehouse_id and ctx.get('active_model') == 'stock.warehouse':
            warehouse_id = ctx.get('active_id')
        return int(warehouse_id) if warehouse_id else False

    def _get_warehouse_internal_location_ids(self):
        warehouse_id = self._get_warehouse_id()
        if not warehouse_id:
            return None

        warehouse = self.env['stock.warehouse'].browse(warehouse_id).exists()
        if not warehouse or not warehouse.view_location_id:
            return []

        return self.env['stock.location'].search([
            ('id', 'child_of', warehouse.view_location_id.id),
            ('usage', '=', 'internal'),
        ]).ids

    def _get_opening_stock(self, date_from):
        warehouse_id = self._get_warehouse_id()
        to_date = date_from - relativedelta(seconds=1)
        ctx = {'to_date': to_date}
        if warehouse_id:
            ctx['warehouse_id'] = warehouse_id

        quantities = self.with_context(**ctx)._compute_quantities_dict(
            None, None, None, to_date=to_date
        )
        return {
            product_id: quantities.get(product_id, {}).get('qty_available', 0.0)
            for product_id in self.ids
        }

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
              AND sm.date < %s
        """
        params = [product_ids, self.env.company.id, date_from, date_to]

        if location_ids is not None:
            query += "\n              AND sm.location_id = ANY(%s)"
            params.append(location_ids)

        query += "\n            GROUP BY sm.product_id"

        self.env.cr.execute(query, params)
        return {row[0]: row[1] or 0.0 for row in self.env.cr.fetchall()}

    def _get_incoming_qty(self, product_ids, date_from, date_to, location_ids=None):
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
              AND src.usage = 'supplier'
              AND dest.usage = 'internal'
              AND sm.date >= %s
              AND sm.date < %s
        """
        params = [product_ids, self.env.company.id, date_from, date_to]

        if location_ids is not None:
            query += "\n              AND sm.location_dest_id = ANY(%s)"
            params.append(location_ids)

        query += "\n            GROUP BY sm.product_id"

        self.env.cr.execute(query, params)
        return {row[0]: row[1] or 0.0 for row in self.env.cr.fetchall()}

    def _compute_sell_through(self, months):
        date_to = fields.Datetime.now()
        date_from = date_to - relativedelta(months=months)
        location_ids = self._get_warehouse_internal_location_ids()
        product_ids = self.ids
        if not product_ids:
            return {}

        opening_map = self._get_opening_stock(date_from)
        sold_map = self._get_sold_qty(product_ids, date_from, date_to, location_ids=location_ids)
        incoming_map = self._get_incoming_qty(product_ids, date_from, date_to, location_ids=location_ids)

        result = {}
        for product in self:
            pid = product.id
            initial = max(opening_map.get(pid, 0.0), 0.0)
            incoming = incoming_map.get(pid, 0.0)
            sold = sold_map.get(pid, 0.0)
            available = initial + incoming
            rate = round(sold / available, 4) if available > 0 else 0.0

            result[pid] = {
                'sold': sold,
                'initial': initial,
                'available': available,
                'rate': rate,
            }
        return result

    @api.depends_context('company', 'allowed_company_ids', 'warehouse', 'warehouse_id', 'active_model', 'active_id')
    def _compute_sell_through_6m(self):
        data = self._compute_sell_through(months=6)
        for product in self:
            d = data.get(product.id, {})
            product.sell_through_6m = d.get('rate', 0.0)
            product.sell_through_6m_sold = d.get('sold', 0.0)
            product.sell_through_6m_initial_stock = d.get('initial', 0.0)
            product.sell_through_6m_available_stock = d.get('available', 0.0)

    @api.depends_context('company', 'allowed_company_ids', 'warehouse', 'warehouse_id', 'active_model', 'active_id')
    def _compute_sell_through_9m(self):
        data = self._compute_sell_through(months=12)
        for product in self:
            d = data.get(product.id, {})
            product.sell_through_9m = d.get('rate', 0.0)
            product.sell_through_9m_sold = d.get('sold', 0.0)
            product.sell_through_9m_initial_stock = d.get('initial', 0.0)
            product.sell_through_9m_available_stock = d.get('available', 0.0)
