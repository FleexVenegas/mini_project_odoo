from odoo import models, fields, api
import json
import logging
from datetime import datetime

_logger = logging.getLogger(__name__)


class OdooWpSync(models.Model):
    _name = "odoo.wp.sync"
    _description = "WooCommerce Orders Sync"
    _order = "date_created desc"

    # Display name
    name = fields.Char(string="Name", compute="_compute_name", store=True)

    # WooCommerce Order Info
    wc_order_id = fields.Integer(
        string="WooCommerce Order ID", required=True, index=True
    )
    order_number = fields.Char(string="Order Number", readonly=True)

    # Customer Info
    customer_name = fields.Char(string="Customer Name")
    customer_email = fields.Char(string="Customer Email")
    customer_phone = fields.Char(string="Phone")

    # Order Details
    status = fields.Selection(
        [
            ("pending", "Pending Payment"),
            ("processing", "Processing"),
            ("on-hold", "On Hold"),
            ("completed", "Completed"),
            ("cancelled", "Cancelled"),
            ("refunded", "Refunded"),
            ("failed", "Failed"),
        ],
        string="Status",
        default="pending",
    )

    date_created = fields.Datetime(string="Date Created")
    total = fields.Float(string="Total Amount")
    currency = fields.Char(string="Currency", default="USD")

    # Items and Details
    items_info = fields.Text(string="Order Items")
    shipping_address = fields.Text(string="Shipping Address")
    payment_method = fields.Char(string="Payment Method")
    created_via = fields.Char(
        string="Origin", help="Order source (checkout, admin, etc.)"
    )

    # Raw Data
    raw_data = fields.Text(string="Raw JSON Data", readonly=True)

    sale_order_id = fields.Many2one("sale.order")

    # Sync Info
    synced_date = fields.Datetime(string="Last Synced", default=fields.Datetime.now)

    _sql_constraints = [
        (
            "wc_order_id_unique",
            "unique(wc_order_id)",
            "WooCommerce Order ID must be unique!",
        )
    ]

    @api.depends("order_number", "customer_name")
    def _compute_name(self):
        """Compute display name combining order number and customer name"""
        for record in self:
            if record.order_number and record.customer_name:
                record.name = f"{record.order_number} - {record.customer_name}"
            elif record.order_number:
                record.name = record.order_number
            else:
                record.name = f"Order #{record.wc_order_id}"

    def action_open_sync_wizard(self):
        """Abre el wizard de confirmación para sincronizar con WooCommerce"""
        confirmation_wizard = self.env["confirmation.wizard"]

        # Ahora solo necesitas pasar texto plano
        description = "Esta acción descargará todas las órdenes recientes desde WooCommerce y las importará en Odoo. Este proceso puede tardar unos minutos dependiendo de la cantidad de órdenes."

        return confirmation_wizard.create_confirmation(
            model_name="odoo.wp.sync",
            method_name="action_sync",
            title="¿Sincronizar con WooCommerce?",
            description=description,
            dialog_size="medium",  # Opciones: 'small', 'medium', 'large', 'extra-large'
        )

    def action_sync(self):
        """Synchronize orders from WooCommerce"""
        try:
            api = self.env["odoo.wp.sync.wc.api"]

            page = 1
            per_page = 4

            # Get orders from WooCommerce (adjust pagination as needed)
            orders = api._wp_request(f"orders?per_page={per_page}&page={page}")

            _logger.info(f"Órdenes obtenidas de WooCommerce: {len(orders)}")

            created_count = 0
            updated_count = 0

            for order_data in orders:
                order_id = order_data.get("id")

                # Check if order already exists
                existing_order = self.search([("wc_order_id", "=", order_id)], limit=1)

                # Prepare order values
                vals = self._prepare_order_vals(order_data)

                if existing_order:
                    existing_order.write(vals)
                    updated_count += 1
                else:
                    self.create(vals)
                    created_count += 1

            # Show result to user
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Sincronización exitosa",
                    "message": f"Creadas: {created_count} | Actualizadas: {updated_count} | Total: {len(orders)} órdenes",
                    "type": "success",
                    "sticky": False,
                },
            }

        except Exception as e:
            _logger.error(f"Error en sincronización: {str(e)}", exc_info=True)
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Error de sincronización",
                    "message": str(e),
                    "type": "danger",
                    "sticky": True,
                },
            }

    def _prepare_order_vals(self, order_data):
        """Prepare order values from WooCommerce data"""
        # Customer info
        billing = order_data.get("billing", {})
        customer_name = (
            f"{billing.get('first_name', '')} {billing.get('last_name', '')}".strip()
        )

        # Shipping address
        shipping = order_data.get("shipping", {})
        shipping_address = ""
        if shipping:
            shipping_address = (
                f"{shipping.get('address_1', '')} {shipping.get('address_2', '')}\n"
                f"{shipping.get('city', '')}, {shipping.get('state', '')} {shipping.get('postcode', '')}\n"
                f"{shipping.get('country', '')}"
            )

        # Order items
        items_list = []
        for item in order_data.get("line_items", []):
            items_list.append(
                f"•[{item.get('sku', '')}] {item.get('name', '')} x {item.get('quantity', 0)} - ${item.get('total', 0)}"
            )
        items_info = "\n".join(items_list)

        # Convert WooCommerce date format to Odoo format
        date_created = order_data.get("date_created")
        if date_created:
            # WooCommerce format: "2026-03-29T19:57:05"
            # Odoo format: "2026-03-29 19:57:05"
            date_created = date_created.replace("T", " ").split(".")[
                0
            ]  # Remove milliseconds if present

        return {
            "wc_order_id": order_data.get("id"),
            "order_number": order_data.get("number"),
            "customer_name": customer_name or "Guest",
            "customer_email": billing.get("email", ""),
            "customer_phone": billing.get("phone", ""),
            "status": order_data.get("status", "pending"),
            "date_created": date_created,
            "total": float(order_data.get("total", 0)),
            "currency": order_data.get("currency", "USD"),
            "items_info": items_info,
            "shipping_address": shipping_address.strip(),
            "payment_method": order_data.get("payment_method_title", ""),
            "created_via": order_data.get("created_via", ""),
            "raw_data": json.dumps(order_data, indent=2),
            "synced_date": fields.Datetime.now(),
        }

    def action_open_create_sale_order_wizard(self):
        """Abre el wizard de confirmación para crear pedidos en Odoo (soporta múltiples registros)"""
        confirmation_wizard = self.env["confirmation.wizard"]

        # Filtrar solo las órdenes que NO tienen pedido asociado
        orders_to_create = self.filtered(lambda o: not o.sale_order_id)
        orders_already_exist = self.filtered(lambda o: o.sale_order_id)

        if not orders_to_create:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Sin órdenes para crear",
                    "message": f"Todas las órdenes seleccionadas ({len(self)}) ya tienen pedidos asociados.",
                    "type": "warning",
                    "sticky": False,
                },
            }

        # Preparar descripción según la cantidad
        if len(orders_to_create) == 1:
            order = orders_to_create
            description = f"Se creará un pedido de venta en Odoo para la orden #{order.order_number} de {order.customer_name} por un total de {order.currency} {order.total}"
        else:
            total_amount = sum(orders_to_create.mapped("total"))
            currency = orders_to_create[0].currency if orders_to_create else "USD"

            description = f"Se crearán {len(orders_to_create)} pedidos de venta en Odoo por un total de {currency} {total_amount:.2f}"

            if orders_already_exist:
                description += f"\n\nNota: {len(orders_already_exist)} órdenes ya tienen pedidos asociados y serán omitidas."

        # Pasar los IDs de los registros a procesar
        return confirmation_wizard.create_confirmation(
            model_name="odoo.wp.sync",
            method_name="action_create_sale_order",
            record_ids=orders_to_create.ids,  # Usar record_ids para múltiples
            title="¿Crear Pedido(s) en Odoo?",
            description=description,
            dialog_size="medium",
        )

    def action_create_sale_order(self):
        """
        Crea órdenes de venta en Odoo a partir de los datos de WooCommerce.
        Soporta procesamiento de múltiples registros.
        Delega la lógica al helper woo.sale.order.helper.
        """
        helper = self.env["woo.sale.order.helper"]

        # Contadores para el resumen
        created_count = 0
        linked_count = 0
        skipped_count = 0
        error_count = 0
        errors = []

        created_orders = self.env["sale.order"]

        for woo_order in self:
            # Saltar si ya tiene pedido asociado
            if woo_order.sale_order_id:
                skipped_count += 1
                continue

            try:
                result = helper.create_sale_order_from_woo(woo_order)
                order = result["order"]
                was_created = result["created"]

                # Guardar relación con el pedido
                woo_order.sale_order_id = order.id

                if was_created:
                    created_count += 1
                    created_orders |= order
                else:
                    linked_count += 1

            except Exception as e:
                error_count += 1
                errors.append(f"Orden #{woo_order.order_number}: {str(e)}")
                _logger.error(
                    f"Error al crear orden de venta para Woo Order ID {woo_order.wc_order_id}: {str(e)}",
                    exc_info=True,
                )

        # Preparar mensaje de resumen
        total_processed = len(self)
        message_parts = []

        if created_count > 0:
            message_parts.append(f"✅ {created_count} pedido(s) creado(s)")
        if linked_count > 0:
            message_parts.append(
                f"🔗 {linked_count} pedido(s) vinculado(s) (ya existían)"
            )
        if skipped_count > 0:
            message_parts.append(f"⏭️ {skipped_count} omitido(s) (ya tenían pedidos)")
        if error_count > 0:
            message_parts.append(f"❌ {error_count} error(es)")

        message = "\n".join(message_parts)

        # Agregar detalles de errores si existen
        if errors:
            message += "\n\nErrores:\n" + "\n".join(
                errors[:3]
            )  # Mostrar máximo 3 errores
            if len(errors) > 3:
                message += f"\n... y {len(errors) - 3} error(es) más"

        # Determinar tipo de notificación
        if error_count == total_processed:
            notification_type = "danger"
            title = "Errores al crear pedidos"
        elif error_count > 0:
            notification_type = "warning"
            title = "Pedidos creados con errores"
        else:
            notification_type = "success"
            title = "Pedidos procesados exitosamente"

        # Si solo se creó un pedido, abrirlo automáticamente
        if created_count == 1 and len(created_orders) == 1:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": title,
                    "message": message,
                    "type": notification_type,
                    "sticky": False,
                    "next": {
                        "type": "ir.actions.act_window",
                        "res_model": "sale.order",
                        "res_id": created_orders.id,
                        "views": [[False, "form"]],
                        "target": "current",
                    },
                },
            }

        # Si se crearon múltiples pedidos, mostrar lista
        if created_count > 1:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": title,
                    "message": message,
                    "type": notification_type,
                    "sticky": False,
                    "next": {
                        "type": "ir.actions.act_window",
                        "res_model": "sale.order",
                        "domain": [("id", "in", created_orders.ids)],
                        "views": [[False, "tree"], [False, "form"]],
                        "target": "current",
                        "name": "Pedidos Creados",
                    },
                },
            }

        # Solo mostrar notificación
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": title,
                "message": message,
                "type": notification_type,
                "sticky": error_count > 0,
            },
        }

    def action_open_sale_order(self):
        """Abre el pedido de venta asociado"""
        self.ensure_one()

        if not self.sale_order_id:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Sin pedido asociado",
                    "message": "Esta orden no tiene un pedido de venta asociado.",
                    "type": "warning",
                    "sticky": False,
                },
            }

        return {
            "type": "ir.actions.act_window",
            "res_model": "sale.order",
            "res_id": self.sale_order_id.id,
            "views": [[False, "form"]],
            "target": "current",
        }
