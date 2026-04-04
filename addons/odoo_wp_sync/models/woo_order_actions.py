"""
Acciones sobre pedidos de WooCommerce desde Odoo.

Cada acción pública sigue la misma convención:
  - Acepta uno o varios registros (self puede ser un recordset).
  - Devuelve una notificación con resumen de éxitos/errores.
  - Delega la llamada HTTP a odoo.wp.sync.wc.api._wp_request.

Agregar nuevas acciones aquí mantendrá odoo_wp_sync_models.py limpio.
"""

import logging
from odoo import models, _

_logger = logging.getLogger(__name__)

# Etiquetas legibles para el resumen de notificaciones
_STATUS_LABELS = {
    "pending": "Pago Pendiente",
    "processing": "En Proceso",
    "on-hold": "En Espera",
    "completed": "Completado",
    "cancelled": "Cancelado",
    "refunded": "Reembolsado",
    "failed": "Fallido",
}


class WooOrderActions(models.Model):
    """
    Mixin de acciones remotas sobre pedidos de WooCommerce.
    Se mezcla directamente en odoo.wp.sync mediante _inherit.
    """

    _inherit = "odoo.wp.sync"

    # ── Helpers internos ───────────────────────────────────────────────────────

    def _wc_update_order_status(self, new_status):
        """
        Envía a WooCommerce el cambio de estado para cada pedido del recordset.

        Returns:
            tuple(list[str], list[str]): (éxitos, errores)
        """
        api = self.env["odoo.wp.sync.wc.api"]
        successes = []
        errors = []

        for order in self:
            try:
                api._wp_request(
                    endpoint=f"orders/{order.wc_order_id}",
                    method="PUT",
                    data={"status": new_status},
                    instance=order.instance_id,
                )
                order.status = new_status
                successes.append(order.order_number or str(order.wc_order_id))
                _logger.info(
                    "Order %s updated to '%s' in WooCommerce",
                    order.order_number,
                    new_status,
                )
            except Exception as e:
                errors.append(f"#{order.order_number}: {e}")
                _logger.error(
                    "Failed to update order %s to '%s': %s",
                    order.order_number,
                    new_status,
                    e,
                )

        return successes, errors

    @staticmethod
    def _build_status_notification(new_status, successes, errors):
        """Construye el dict de notificación estándar."""
        label = _STATUS_LABELS.get(new_status, new_status)
        total = len(successes) + len(errors)

        if errors and not successes:
            title = _("Error al actualizar estado")
            notif_type = "danger"
            message = "\n".join(errors[:5])
            if len(errors) > 5:
                message += f"\n… y {len(errors) - 5} error(es) más"
        elif errors:
            title = _("Actualizado con advertencias")
            notif_type = "warning"
            message = (
                f"✅ {len(successes)} actualizado(s) a '{label}'\n"
                f"❌ {len(errors)} error(es):\n" + "\n".join(errors[:3])
            )
        else:
            title = _("Estado actualizado")
            notif_type = "success"
            message = (
                f"✅ {len(successes)} de {total} pedido(s) "
                f"actualizado(s) a '{label}' en WooCommerce"
            )

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": title,
                "message": message,
                "type": notif_type,
                "sticky": notif_type != "success",
            },
        }

    # ── Acciones públicas de cambio de estado ──────────────────────────────────

    def action_wc_mark_completed(self):
        """Marca el pedido como 'completed' en WooCommerce."""
        successes, errors = self._wc_update_order_status("completed")
        return self._build_status_notification("completed", successes, errors)

    def action_wc_mark_processing(self):
        """Marca el pedido como 'processing' en WooCommerce."""
        successes, errors = self._wc_update_order_status("processing")
        return self._build_status_notification("processing", successes, errors)

    def action_wc_mark_cancelled(self):
        """Marca el pedido como 'cancelled' en WooCommerce."""
        successes, errors = self._wc_update_order_status("cancelled")
        return self._build_status_notification("cancelled", successes, errors)

    def action_wc_mark_on_hold(self):
        """Marca el pedido como 'on-hold' en WooCommerce."""
        successes, errors = self._wc_update_order_status("on-hold")
        return self._build_status_notification("on-hold", successes, errors)

    def action_wc_mark_pending(self):
        """Marca el pedido como 'pending' en WooCommerce."""
        successes, errors = self._wc_update_order_status("pending")
        return self._build_status_notification("pending", successes, errors)

    def action_wc_mark_refunded(self):
        """Marca el pedido como 'refunded' en WooCommerce."""
        successes, errors = self._wc_update_order_status("refunded")
        return self._build_status_notification("refunded", successes, errors)

    # ── Otras acciones futuras ─────────────────────────────────────────────────
    # Añadir aquí: notas de pedido, reenvío de correo, actualización de tracking, etc.
