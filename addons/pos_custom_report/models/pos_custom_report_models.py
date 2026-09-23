from collections import defaultdict

from odoo import models, fields

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
    sales_total = fields.Float(string="Total ventas", readonly=True)
    refunds_total = fields.Float(string="Total devoluciones", readonly=True)
    opening_total = fields.Float(string="Total apertura", readonly=True)
    orders_count = fields.Integer(string="Órdenes", readonly=True)

    caja_line_ids = fields.One2many(
        "pos.custom.report.caja.line",
        "wizard_id",
        string="Cajas",
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
            "name": "Reporte personalizado POS",
            "res_model": "pos.details.wizard",
            "res_id": self.id,
            "view_mode": "form",
            "views": [(False, "form")],
            "target": "new",
            "context": dict(self.env.context, dialog_size="extra-large"),
        }

    def _load_custom_report_into_wizard(self, report_data):
        self.caja_line_ids.unlink()

        caja_vals = []
        for caja in report_data["cajas"]:
            order_vals = []
            for order in caja["orders"]:
                refunded_text = (
                    ", ".join(order["refunded_orders"]) if order["refunded_orders"] else ""
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
            }
        )

    def _payment_method_label(self, payment_method):
        name = payment_method.name
        if isinstance(name, dict):
            lang = self.env.lang or "en_US"
            return name.get(lang) or name.get("en_US") or next(iter(name.values()), "N/D")
        return name or "N/D"

    def _prepare_custom_report_data(self):
        orders = self.env["pos.order"].search(
            [
                ("state", "in", ["paid", "invoiced", "done"]),
                ("date_order", ">=", self.start_date),
                ("date_order", "<=", self.end_date),
                ("config_id", "in", self.pos_config_ids.ids),
            ],
            order="date_order asc, name asc",
        )

        cajas = []
        sales_total = 0.0
        refunds_total = 0.0
        opening_total = 0.0

        for config in self.pos_config_ids:
            config_orders = orders.filtered(lambda o: o.config_id == config)
            caja_sales = 0.0
            caja_refunds = 0.0
            payments_by_method = defaultdict(float)
            order_lines = []

            for order in config_orders:
                is_refund = order.amount_total < 0 or bool(order.refunded_order_ids)
                payments = []
                for payment in order.payment_ids.filtered(lambda p: not p.is_change):
                    method_name = self._payment_method_label(payment.payment_method_id)
                    amount = payment.amount
                    payments.append({"method": method_name, "amount": amount})
                    payments_by_method[method_name] += amount

                if is_refund:
                    caja_refunds += abs(order.amount_total)
                else:
                    caja_sales += order.amount_total

                order_lines.append(
                    {
                        "name": order.name,
                        "pos_reference": order.pos_reference,
                        "date_order": order.date_order,
                        "session": order.session_id.name,
                        "total": 0.0 if is_refund else order.amount_total,
                        "refund_total": abs(order.amount_total) if is_refund else 0.0,
                        # En devoluciones el impacto va en refund_total; el neto de la línea es 0
                        "net_total": 0.0 if is_refund else order.amount_total,
                        "refunded_orders": order.refunded_order_ids.mapped("name"),
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

            cajas.append(
                {
                    "config_id": config.id,
                    "config_name": config.name,
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

        return {
            "cajas": cajas,
            "sales_total": sales_total,
            "refunds_total": refunds_total,
            "opening_total": opening_total,
            "orders_count": len(orders),
        }


class PosCustomReportCajaLine(models.TransientModel):
    _name = "pos.custom.report.caja.line"
    _description = "Caja - reporte personalizado POS"
    _order = "config_name"

    wizard_id = fields.Many2one("pos.details.wizard", required=True, ondelete="cascade")
    config_id = fields.Many2one("pos.config", string="Caja", readonly=True)
    config_name = fields.Char(string="Caja", readonly=True)
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
    refunded_orders = fields.Char(string="Órdenes devueltas", readonly=True)


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
