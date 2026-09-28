from collections import defaultdict

from odoo import api, models, fields

import logging

_logger = logging.getLogger(__name__)


class PosDetailsWizard(models.TransientModel):
    _inherit = "pos.details.wizard"

    OPTION_STANDARD = "standard"
    OPTION_CUSTOM = "custom"

    option_custom_report = fields.Selection(
        [
            (OPTION_STANDARD, "Estándar"),
            (OPTION_CUSTOM, "Personalizado"),
        ],
        string="Opción de reporte",
        default=OPTION_CUSTOM,
        required=True,
    )
    show_results = fields.Boolean(default=False)
    warehouse_ids = fields.Many2many(
        "stock.warehouse",
        "pos_custom_report_wizard_warehouse_rel",
        "wizard_id",
        "warehouse_id",
        string="Tiendas",
        default=lambda self: self._warehouses_with_pos(),
    )
    allowed_warehouse_ids = fields.Many2many(
        "stock.warehouse",
        compute="_compute_allowed_warehouse_ids",
        string="Tiendas con caja",
    )
    sales_total = fields.Float(string="Total ventas", readonly=True)
    refunds_total = fields.Float(string="Total devoluciones", readonly=True)
    opening_total = fields.Float(string="Total apertura", readonly=True)
    orders_count = fields.Integer(string="Órdenes", readonly=True)

    caja_line_ids = fields.One2many(
        "pos.custom.report.caja.line",
        "wizard_id",
        string="Cajas",
    )
    store_payment_line_ids = fields.One2many(
        "pos.custom.report.store.payment",
        "wizard_id",
        string="Métodos de pago por tienda",
    )

    @api.depends_context("uid")
    def _compute_allowed_warehouse_ids(self):
        warehouses = self._warehouses_with_pos()
        for wizard in self:
            wizard.allowed_warehouse_ids = warehouses

    def _warehouses_with_pos(self):
        """Almacenes que tienen al menos una caja (pos.config) asignada."""
        return (
            self.env["pos.config"]
            .search([])
            .mapped("picking_type_id.warehouse_id")
        )

    def _pos_configs_for_warehouses(self):
        """Cajas cuyo tipo de operación pertenece a las tiendas seleccionadas."""
        self.ensure_one()
        if not self.warehouse_ids:
            return self.env["pos.config"]
        return self.env["pos.config"].search([]).filtered(
            lambda pos: pos.picking_type_id.warehouse_id in self.warehouse_ids
        )

    def generate_report(self):
        self.ensure_one()
        if self.option_custom_report == self.OPTION_CUSTOM:
            return self.action_show_custom_report()
        return super().generate_report()

    def action_show_custom_report(self):
        self.ensure_one()
        report_data = self._prepare_custom_report_data()
        self._load_custom_report_into_wizard(report_data)
        _logger.info(
            "Reporte personalizado POS: %s cajas, %s órdenes",
            len(report_data["cajas"]),
            self.orders_count,
        )
        return {
            "type": "ir.actions.act_window",
            "name": "Póliza de venta",
            "res_model": "pos.details.wizard",
            "res_id": self.id,
            "view_mode": "form",
            "views": [(False, "form")],
            "target": "new",
            "context": dict(self.env.context, dialog_size="extra-large"),
        }

    def action_print_policy_pdf(self):
        self.ensure_one()
        return self.env.ref(
            "pos_custom_report.action_report_pos_policy"
        ).report_action(self)

    def _load_custom_report_into_wizard(self, report_data):
        self.caja_line_ids.unlink()
        self.store_payment_line_ids.unlink()

        caja_vals = []
        for caja in report_data["cajas"]:
            order_vals = []
            for order in caja["orders"]:
                refunded_text = (
                    ", ".join(order["refunded_orders"])
                    if order["refunded_orders"]
                    else ""
                )
                order_vals.append(
                    (
                        0,
                        0,
                        {
                            "order_name": order["name"],
                            "pos_reference": order["pos_reference"] or "",
                            "date_order": order["date_order"],
                            "session_name": order["session"],
                            "total": order["total"],
                            "refund_total": order["refund_total"],
                            "net_total": order["net_total"],
                            "refunded_orders": refunded_text,
                        },
                    )
                )

            payment_vals = [
                (0, 0, {"method_name": method, "amount": amount})
                for method, amount in caja["payments_by_method"].items()
            ]
            opening_vals = [
                (0, 0, {"session_name": row["session"], "opening": row["opening"]})
                for row in caja["opening_by_session"]
            ]

            caja_vals.append(
                (
                    0,
                    0,
                    {
                        "config_id": caja["config_id"],
                        "config_name": caja["config_name"],
                        "warehouse_name": caja["warehouse_name"],
                        "orders_count": len(caja["orders"]),
                        "sales_total": caja["sales_total"],
                        "refunds_total": caja["refunds_total"],
                        "net_total": caja["sales_total"] - caja["refunds_total"],
                        "opening_total": caja["opening_total"],
                        "order_line_ids": order_vals,
                        "payment_line_ids": payment_vals,
                        "opening_line_ids": opening_vals,
                    },
                )
            )

        self.write(
            {
                "show_results": True,
                "sales_total": report_data["sales_total"],
                "refunds_total": report_data["refunds_total"],
                "opening_total": report_data["opening_total"],
                "orders_count": report_data["orders_count"],
                "caja_line_ids": caja_vals,
                "store_payment_line_ids": [
                    (
                        0,
                        0,
                        {
                            "warehouse_name": row["warehouse_name"],
                            "method_name": row["method_name"],
                            "amount": row["amount"],
                        },
                    )
                    for row in report_data["store_payments"]
                ],
            }
        )

    def _is_refund_order(self, order):
        return order.amount_total < 0 or bool(order.refunded_order_ids)

    def _allocate_refund_to_originals(self, order):
        """Reparte el monto de un reembolso entre las órdenes que devuelve."""
        shares = defaultdict(float)
        for line in order.lines:
            original_line = line.refunded_orderline_id
            if not original_line:
                continue
            shares[original_line.order_id.id] += abs(line.price_subtotal_incl)

        if sum(shares.values()) > 0.0001:
            return shares

        originals = order.refunded_order_ids
        shares = defaultdict(float)
        if len(originals) == 1:
            shares[originals.id] = abs(order.amount_total)
        return shares

    def _payment_method_label(self, payment_method):
        name = payment_method.name
        if isinstance(name, dict):
            lang = self.env.lang or "en_US"
            return (
                name.get(lang) or name.get("en_US") or next(iter(name.values()), "N/D")
            )
        return name or "N/D"

    def _prepare_custom_report_data(self):
        pos_configs = self._pos_configs_for_warehouses()
        orders = self.env["pos.order"].search(
            [
                ("state", "in", ["paid", "invoiced", "done"]),
                ("date_order", ">=", self.start_date),
                ("date_order", "<=", self.end_date),
                ("config_id", "in", pos_configs.ids),
            ],
            order="date_order asc, name asc",
        )

        cajas = []
        sales_total = 0.0
        refunds_total = 0.0
        opening_total = 0.0
        payments_by_store = defaultdict(lambda: {"name": "", "methods": defaultdict(float)})
        report_order_ids = set(orders.ids)
        # Monto y documentos de reembolso que corresponden a cada orden de origen
        refunds_on_order = defaultdict(lambda: {"amount": 0.0, "names": []})

        for order in orders:
            if not self._is_refund_order(order):
                continue
            for original_id, amount in self._allocate_refund_to_originals(
                order
            ).items():
                if original_id not in report_order_ids or original_id == order.id:
                    continue
                refunds_on_order[original_id]["amount"] += amount
                refunds_on_order[original_id]["names"].append(order.name)

        for config in pos_configs:
            config_orders = orders.filtered(lambda o: o.config_id == config)
            caja_sales = 0.0
            caja_refunds = 0.0
            payments_by_method = defaultdict(float)
            order_lines = []

            for order in config_orders:
                is_refund = self._is_refund_order(order)
                payments = []
                for payment in order.payment_ids.filtered(lambda p: not p.is_change):
                    method_name = self._payment_method_label(payment.payment_method_id)
                    amount = payment.amount
                    payments.append({"method": method_name, "amount": amount})
                    payments_by_method[method_name] += amount

                if is_refund:
                    caja_refunds += abs(order.amount_total)
                    # El movimiento de reembolso se conserva como fila propia.
                    # El monto queda aplicado en la orden de origen; aquí el neto es 0
                    # para no restarlo otra vez.
                    line_total = 0.0
                    line_refund = abs(order.amount_total)
                    line_net = 0.0
                    related_orders = order.refunded_order_ids.mapped("name")
                else:
                    caja_sales += order.amount_total
                    applied = refunds_on_order.get(order.id)
                    line_total = order.amount_total
                    line_refund = applied["amount"] if applied else 0.0
                    line_net = line_total - line_refund
                    related_orders = applied["names"] if applied else []

                order_lines.append(
                    {
                        "name": order.name,
                        "pos_reference": order.pos_reference,
                        "date_order": order.date_order,
                        "session": order.session_id.name,
                        "total": line_total,
                        "refund_total": line_refund,
                        "net_total": line_net,
                        "refunded_orders": related_orders,
                        "payments": payments,
                    }
                )

            sessions = config_orders.mapped("session_id")
            opening_by_session = [
                {
                    "session": session.name,
                    "opening": session.cash_register_balance_start,
                }
                for session in sessions
            ]
            caja_opening = sum(sessions.mapped("cash_register_balance_start"))

            warehouse = config.picking_type_id.warehouse_id
            store_key = warehouse.id or 0
            payments_by_store[store_key]["name"] = warehouse.name or ""
            for method_name, amount in payments_by_method.items():
                payments_by_store[store_key]["methods"][method_name] += amount

            cajas.append(
                {
                    "config_id": config.id,
                    "config_name": config.name,
                    "warehouse_name": warehouse.name or "",
                    "orders": order_lines,
                    "sales_total": caja_sales,
                    "refunds_total": caja_refunds,
                    "payments_by_method": dict(payments_by_method),
                    "opening_by_session": opening_by_session,
                    "opening_total": caja_opening,
                }
            )

            sales_total += caja_sales
            refunds_total += caja_refunds
            opening_total += caja_opening

        store_payments = []
        for store in sorted(payments_by_store.values(), key=lambda row: row["name"]):
            for method_name in sorted(store["methods"]):
                store_payments.append(
                    {
                        "warehouse_name": store["name"],
                        "method_name": method_name,
                        "amount": store["methods"][method_name],
                    }
                )

        return {
            "cajas": cajas,
            "sales_total": sales_total,
            "refunds_total": refunds_total,
            "opening_total": opening_total,
            "orders_count": len(orders),
            "store_payments": store_payments,
        }


class PosCustomReportStorePayment(models.TransientModel):
    _name = "pos.custom.report.store.payment"
    _description = "Métodos de pago por tienda - reporte personalizado POS"
    _order = "warehouse_name, method_name"

    wizard_id = fields.Many2one("pos.details.wizard", required=True, ondelete="cascade")
    warehouse_name = fields.Char(string="Tienda", readonly=True)
    method_name = fields.Char(string="Método de pago", readonly=True)
    amount = fields.Float(string="Total", readonly=True)


class PosCustomReportCajaLine(models.TransientModel):
    _name = "pos.custom.report.caja.line"
    _description = "Caja - reporte personalizado POS"
    _order = "config_name"

    wizard_id = fields.Many2one("pos.details.wizard", required=True, ondelete="cascade")
    config_id = fields.Many2one("pos.config", string="Caja", readonly=True)
    config_name = fields.Char(string="Caja", readonly=True)
    warehouse_name = fields.Char(string="Tienda", readonly=True)
    orders_count = fields.Integer(string="Órdenes", readonly=True)
    sales_total = fields.Float(string="Total ventas", readonly=True)
    refunds_total = fields.Float(string="Total devoluciones", readonly=True)
    net_total = fields.Float(string="Total neto", readonly=True)
    opening_total = fields.Float(string="Total apertura", readonly=True)

    order_line_ids = fields.One2many(
        "pos.custom.report.order.line",
        "caja_line_id",
        string="Órdenes",
    )
    payment_line_ids = fields.One2many(
        "pos.custom.report.payment.line",
        "caja_line_id",
        string="Métodos de pago",
    )
    opening_line_ids = fields.One2many(
        "pos.custom.report.opening.line",
        "caja_line_id",
        string="Apertura",
    )


class PosCustomReportOrderLine(models.TransientModel):
    _name = "pos.custom.report.order.line"
    _description = "Línea de orden - reporte personalizado POS"

    caja_line_id = fields.Many2one(
        "pos.custom.report.caja.line",
        required=True,
        ondelete="cascade",
    )
    order_name = fields.Char(string="Orden", readonly=True)
    pos_reference = fields.Char(string="Referencia", readonly=True)
    date_order = fields.Datetime(string="Fecha", readonly=True)
    session_name = fields.Char(string="Sesión", readonly=True)
    total = fields.Float(string="Total orden", readonly=True)
    refund_total = fields.Float(string="Devolución", readonly=True)
    net_total = fields.Float(string="Total neto", readonly=True)
    refunded_orders = fields.Char(string="Relación de devolución", readonly=True)


class PosCustomReportPaymentLine(models.TransientModel):
    _name = "pos.custom.report.payment.line"
    _description = "Totales por método de pago - reporte personalizado POS"

    caja_line_id = fields.Many2one(
        "pos.custom.report.caja.line",
        required=True,
        ondelete="cascade",
    )
    method_name = fields.Char(string="Método de pago", readonly=True)
    amount = fields.Float(string="Total", readonly=True)


class PosCustomReportOpeningLine(models.TransientModel):
    _name = "pos.custom.report.opening.line"
    _description = "Apertura por sesión - reporte personalizado POS"

    caja_line_id = fields.Many2one(
        "pos.custom.report.caja.line",
        required=True,
        ondelete="cascade",
    )
    session_name = fields.Char(string="Sesión", readonly=True)
    opening = fields.Float(string="Apertura", readonly=True)


