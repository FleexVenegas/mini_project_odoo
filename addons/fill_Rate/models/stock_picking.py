# -*- coding: utf-8 -*-
from odoo import models, fields, api


class StockPicking(models.Model):
    """
    Extensión de Recepción/Picking para actualizar Fill Rate automáticamente.
    Cuando se valida una recepción, actualiza las cantidades recibidas.
    """

    _inherit = "stock.picking"

    def button_validate(self):
        """
        Sobrescribe la validación de recepción para actualizar Fill Rate.
        Se ejecuta cuando el usuario confirma la recepción de mercancía.
        """
        # Ejecutar la validación original
        res = super(StockPicking, self).button_validate()

        # Actualizar Fill Rate solo para recepciones de compra (incoming)
        for picking in self:
            if picking.picking_type_code == "incoming" and picking.purchase_id:
                picking._update_fill_rate_from_reception()

        return res

    def _update_fill_rate_from_reception(self):
        """
        Actualiza los registros de Fill Rate basándose en la recepción validada.
        Relaciona movimientos de stock con líneas de orden de compra.
        """
        self.ensure_one()

        if not self.purchase_id:
            return

        FillRateLine = self.env["fill.rate.line"]

        # Procesar cada movimiento validado
        for move in self.move_ids_without_package.filtered(lambda m: m.state == "done"):
            # Buscar la línea de orden de compra relacionada
            if not move.purchase_line_id:
                continue

            # Buscar el registro de fill rate correspondiente
            fill_rate_line = FillRateLine.search(
                [("purchase_order_line_id", "=", move.purchase_line_id.id)], limit=1
            )

            if fill_rate_line:
                # Actualizar la cantidad recibida
                fill_rate_line.update_received_quantity()

        # Recalcular el fill rate del proveedor
        if self.partner_id:
            self.partner_id._compute_fill_rate()
            self.partner_id._compute_supplier_class()


class StockMove(models.Model):
    """
    Extensión de Movimientos de Stock para facilitar relaciones.
    """

    _inherit = "stock.move"

    def _action_done(self, cancel_backorder=False):
        """
        Hook cuando un movimiento se marca como realizado.
        Útil para actualizaciones adicionales si es necesario.
        """
        res = super(StockMove, self)._action_done(cancel_backorder=cancel_backorder)

        # Actualizar fill rate si es una recepción de compra
        for move in self:
            if move.picking_code == "incoming" and move.purchase_line_id:
                # Buscar y actualizar el registro de fill rate
                fill_rate_line = self.env["fill.rate.line"].search(
                    [("purchase_order_line_id", "=", move.purchase_line_id.id)], limit=1
                )

                if fill_rate_line:
                    fill_rate_line.update_received_quantity()

        return res
