# -*- coding: utf-8 -*-
from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class CostoFormulaWizard(models.TransientModel):
    _name = "costo.formula.wizard"
    _description = "Wizard para mostrar fórmula del costo ponderado"

    product_id = fields.Many2one("product.product", string="Producto", readonly=True)
    costo_actual = fields.Float(string="Costo Ponderado Actual", readonly=True)
    moneda = fields.Char(string="Moneda", readonly=True)
    stock_actual = fields.Float(string="Stock Actual", readonly=True)
    tipo_cambio = fields.Float(string="Tipo de Cambio", readonly=True)
    fecha_calculo = fields.Datetime(string="Última Actualización", readonly=True)
    orden_compra = fields.Char(string="Última Orden de Compra", readonly=True)

    # Campos para el cálculo detallado
    cantidad_anterior = fields.Float(string="Cantidad Anterior", readonly=True)
    costo_anterior = fields.Float(string="Costo Anterior", readonly=True)
    cantidad_nueva = fields.Float(
        string="Cantidad Nueva (Última Compra)", readonly=True
    )
    costo_nuevo = fields.Float(string="Costo Nuevo (Última Compra)", readonly=True)

    formula_detallada = fields.Text(
        string="Fórmula Completa con Números", readonly=True
    )

    @api.model
    def open_wizard(self, product_id):
        """Abre el wizard con los datos del producto"""
        product = self.env["product.product"].browse(product_id)
        weighted = self.env["stock.weighted"].search(
            [("product_id", "=", product_id)], limit=1
        )

        if not weighted:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Sin información",
                    "message": "No se encontró información de costo ponderado para este producto.",
                    "type": "warning",
                    "sticky": False,
                },
            }

        # Obtener información del weighted
        costo_actual = weighted.unit_weighted_cost
        moneda = weighted.currency_id.name if weighted.currency_id else "N/A"
        stock_actual = weighted.current_stock
        tipo_cambio = weighted.ultimo_tipo_cambio
        fecha_calculo = weighted.ultimo_calculo_date
        orden_compra = weighted.order_id.name if weighted.order_id else "N/A"

        # Buscar la última compra para obtener los números del cálculo
        ultima_compra_info = self._obtener_ultima_compra_info(product, weighted)

        # Construir la fórmula detallada con números reales
        formula_detallada = self._construir_formula_con_numeros(
            weighted, ultima_compra_info
        )

        # Crear el wizard
        wizard = self.create(
            {
                "product_id": product_id,
                "costo_actual": costo_actual,
                "moneda": moneda,
                "stock_actual": stock_actual,
                "tipo_cambio": tipo_cambio,
                "fecha_calculo": fecha_calculo,
                "orden_compra": orden_compra,
                "cantidad_anterior": ultima_compra_info.get("cantidad_anterior", 0),
                "costo_anterior": ultima_compra_info.get("costo_anterior", 0),
                "cantidad_nueva": ultima_compra_info.get("cantidad_nueva", 0),
                "costo_nuevo": ultima_compra_info.get("costo_nuevo", 0),
                "formula_detallada": formula_detallada,
            }
        )

        return {
            "name": f"Fórmula del Costo Ponderado - {product.name}",
            "type": "ir.actions.act_window",
            "res_model": "costo.formula.wizard",
            "view_mode": "form",
            "res_id": wizard.id,
            "target": "new",
        }

    def action_close(self):
        """Cierra el wizard sin cerrar el wizard padre"""
        return {"type": "ir.actions.act_window_close"}

    def _obtener_ultima_compra_info(self, product, weighted):
        """Obtiene información de la última compra para mostrar el cálculo real"""
        resultado = {
            "cantidad_anterior": 0,
            "costo_anterior": 0,
            "cantidad_nueva": 0,
            "costo_nuevo": 0,
            "moneda_nueva": "N/A",
        }

        try:
            # Buscar la última orden de compra del producto
            if weighted.order_id:
                orden = weighted.order_id

                # Buscar la línea de la orden que corresponde a este producto
                linea = orden.order_line.filtered(
                    lambda l: l.product_id.id == product.id
                )

                if linea:
                    linea = linea[0]  # Tomar la primera si hay varias
                    resultado["cantidad_nueva"] = linea.product_qty
                    resultado["costo_nuevo"] = linea.price_unit
                    resultado["moneda_nueva"] = (
                        orden.currency_id.name if orden.currency_id else "N/A"
                    )

                    # Calcular cantidad y costo anterior
                    # El stock actual incluye la nueva compra, así que restamos
                    stock_total = weighted.current_stock
                    resultado["cantidad_anterior"] = (
                        stock_total - resultado["cantidad_nueva"]
                    )

                    # Para el costo anterior, necesitamos hacer un cálculo inverso
                    # Si tenemos: Costo_Ponderado = [(Cant_Ant × Costo_Ant) + (Cant_Nueva × Costo_Nuevo)] / Total
                    # Entonces: Costo_Ant = (Costo_Ponderado × Total - Cant_Nueva × Costo_Nuevo) / Cant_Ant

                    if resultado["cantidad_anterior"] > 0:
                        # Calcular el costo anterior usando fórmula inversa
                        costo_ponderado_actual = weighted.unit_weighted_cost
                        total_unidades = stock_total
                        cant_nueva = resultado["cantidad_nueva"]
                        costo_nuevo = resultado["costo_nuevo"]
                        cant_anterior = resultado["cantidad_anterior"]

                        # Fórmula inversa: Costo_Ant = (Costo_Pond × Total - Cant_Nueva × Costo_Nuevo) / Cant_Ant
                        costo_total_anterior = (
                            costo_ponderado_actual * total_unidades
                        ) - (cant_nueva * costo_nuevo)
                        resultado["costo_anterior"] = (
                            costo_total_anterior / cant_anterior
                        )
                    else:
                        # Si no hay stock anterior, el costo anterior es 0
                        resultado["costo_anterior"] = 0

        except Exception as e:
            _logger.error(f"Error obteniendo información de última compra: {str(e)}")

        return resultado

    def _construir_formula_con_numeros(self, weighted, compra_info):
        """Construye la fórmula con los números reales del cálculo"""
        try:
            costo_actual = weighted.unit_weighted_cost
            moneda = weighted.currency_id.name if weighted.currency_id else "N/A"
            stock_actual = weighted.current_stock
            tipo_cambio = weighted.ultimo_tipo_cambio

            cant_ant = compra_info.get("cantidad_anterior", 0)
            costo_ant = compra_info.get("costo_anterior", 0)
            cant_nueva = compra_info.get("cantidad_nueva", 0)
            costo_nuevo = compra_info.get("costo_nuevo", 0)

            # Cálculos intermedios
            costo_total_ant = cant_ant * costo_ant
            costo_total_nuevo = cant_nueva * costo_nuevo
            costo_total = costo_total_ant + costo_total_nuevo
            cantidad_total = cant_ant + cant_nueva

            formula = f"""
CÁLCULO DEL COSTO PONDERADO
{'=' * 70}

RESULTADO FINAL: {costo_actual:.4f} {moneda}

INFORMACIÓN GENERAL
{'-' * 70}
Stock Total:        {stock_actual:.2f} unidades
Moneda:             {moneda}
Tipo de Cambio:     {tipo_cambio:.4f}
Última Orden:       {weighted.order_id.name if weighted.order_id else 'N/A'}

DETALLE DEL CÁLCULO
{'-' * 70}

Stock Anterior:
  Cantidad:         {cant_ant:.2f} unidades
  Costo Unitario:   {costo_ant:.4f} {moneda}
  Costo Total:      {costo_total_ant:.4f} {moneda}

Nueva Compra:
  Cantidad:         {cant_nueva:.2f} unidades
  Costo Unitario:   {costo_nuevo:.4f} {moneda}
  Costo Total:      {costo_total_nuevo:.4f} {moneda}

CÁLCULO PONDERADO
{'-' * 70}

Fórmula:
  Costo Ponderado = (Costo Total Anterior + Costo Total Nueva Compra)
                    ───────────────────────────────────────────────
                              Cantidad Total

Desarrollo:
  1. Costo Total Anterior    = {cant_ant:.2f} × {costo_ant:.4f}
                               = {costo_total_ant:.4f}

  2. Costo Total Nueva       = {cant_nueva:.2f} × {costo_nuevo:.4f}
                               = {costo_total_nuevo:.4f}

  3. Suma de Costos          = {costo_total_ant:.4f} + {costo_total_nuevo:.4f}
                               = {costo_total:.4f}

  4. Cantidad Total          = {cant_ant:.2f} + {cant_nueva:.2f}
                               = {cantidad_total:.2f}

  5. Costo Ponderado         = {costo_total:.4f} ÷ {cantidad_total:.2f}
                               = {costo_actual:.4f} {moneda}

{'=' * 70}

Nota: Este costo se actualiza automáticamente con cada recepción de
mercancía. Las conversiones de moneda se aplican según el tipo de
cambio vigente al momento de la compra.
"""
            return formula

        except Exception as e:
            _logger.error(f"Error construyendo fórmula con números: {str(e)}")
            return f"Error al construir fórmula: {str(e)}"
