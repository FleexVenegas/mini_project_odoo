# -*- coding: utf-8 -*-
from odoo import models, fields
from odoo.exceptions import UserError
from .pricing_tools import calcular_precio_debug
from .pricing_tools import calcular_precio_mxn_debug
import logging

_logger = logging.getLogger(__name__)


class PriceCalculationTest(models.TransientModel):
    _name = "price.calculation.test"
    _description = "Prueba Detallada de Cálculo de Precio"

    product_id = fields.Many2one("product.product", string="Producto", required=True)
    pricelist_id = fields.Many2one(
        "product.pricelist", string="Lista de Precios", required=True
    )

    costo = fields.Float(string="Costo base", readonly=True)
    A = fields.Float(string="Multiplicador General", readonly=True)
    B = fields.Float(string="Flete Americano", readonly=True)
    C = fields.Float(string="Cargo por tipo (KIT/Normal)", readonly=True)
    D = fields.Float(string="Costo Facturación", readonly=True)
    E = fields.Float(string="Prima de Riesgo Nacional", readonly=True)
    G = fields.Float(string="Desglose IVA", readonly=True)
    F1 = fields.Float(string="Margen Bruto", readonly=True)
    F = fields.Float(string="Margen Ecommerce", readonly=True)
    H1 = fields.Float(string="Envío Ecommerce", readonly=True)
    divisor_final = fields.Float(string="Divisor Lista", readonly=True)
    resultado = fields.Float(string="Precio Calculado", readonly=True)
    formula_utilizada = fields.Char(string="Fórmula Aplicada", readonly=True)
    error = fields.Text(string="Error", readonly=True)
    formula_completa = fields.Text(string="Fórmula Detallada", readonly=True)
    valor_dollar = fields.Float(string="Valor del Dólar", readonly=True)
    currency_name = fields.Char(string="Moneda Costo", readonly=True)

    def ejecutar_prueba(self):
        self.ensure_one()
        try:
            valores = calcular_precio_debug(
                env=self.env, product=self.product_id, pricelist=self.pricelist_id
            )

            weighted = self.env["stock.weighted"].search(
                [("product_id", "=", self.product_id.id)], limit=1
            )

            if weighted and weighted.currency_id and weighted.currency_id.name == "MXN":
                try:
                    valores_mxn = calcular_precio_mxn_debug(
                        env=self.env,
                        product=self.product_id,
                        pricelist=self.pricelist_id,
                    )
                    if valores_mxn and not valores_mxn.get("error"):
                        valores["resultado"] = valores_mxn.get(
                            "resultado", valores["resultado"]
                        )
                        valores["formula_utilizada"] = valores_mxn.get(
                            "formula_utilizada", valores["formula_utilizada"]
                        )
                        valores["formula_completa"] = valores_mxn.get(
                            "formula_completa", valores["formula_completa"]
                        )
                except Exception as e_mxn:
                    _logger.warning(f"Error en cálculo MXN: {str(e_mxn)}")

            self.write(valores)

        except Exception as e:
            _logger.exception("Error en prueba de cálculo de precios")
            self.write({"error": str(e)})

        return {
            "type": "ir.actions.act_window",
            "res_model": "price.calculation.test",
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }

    def action_ver_formula_costo(self):
        """Abre el wizard con la fórmula detallada del costo ponderado"""
        self.ensure_one()
        if not self.product_id:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Producto no seleccionado",
                    "message": "Por favor, selecciona un producto primero.",
                    "type": "warning",
                    "sticky": False,
                },
            }

        # Llamar al método del wizard para abrirlo
        return self.env["costo.formula.wizard"].open_wizard(self.product_id.id)

    def actualiza_lista(self):
        self.actualizar_precio_lista(
            pricelist_id=self.pricelist_id.id,
            product_id=self.product_id.id,
            nuevo_precio=self.resultado,
        )
        return

    def actualizar_precio_lista(self, pricelist_id, product_id, nuevo_precio):
        try:
            pricelist_item = self.env["product.pricelist.item"].search(
                [
                    ("pricelist_id", "=", pricelist_id),
                    ("product_id", "=", product_id),
                    ("applied_on", "=", "0_product_variant"),
                ],
                limit=1,
            )

            if pricelist_item:
                pricelist_item.write({"fixed_price": nuevo_precio})
                _logger.info(
                    f"Precio actualizado para producto {product_id} en lista {pricelist_id}: {nuevo_precio}"
                )
                return {
                    "success": True,
                    "action": "updated",
                    "message": f"Precio actualizado exitosamente: ${nuevo_precio:.2f}",
                }
            else:
                product = self.env["product.product"].browse(product_id)
                new_item = self.env["product.pricelist.item"].create(
                    {
                        "pricelist_id": pricelist_id,
                        "applied_on": "0_product_variant",
                        "product_id": product_id,
                        "product_tmpl_id": product.product_tmpl_id.id,
                        "fixed_price": nuevo_precio,
                        "compute_price": "fixed",
                    }
                )
                _logger.info(
                    f"Nuevo precio creado para producto {product_id} en lista {pricelist_id}: {nuevo_precio}"
                )
                return {
                    "success": True,
                    "action": "created",
                    "message": f"Nuevo precio creado exitosamente: ${nuevo_precio:.2f}",
                }

        except Exception as e:
            _logger.error(f"Error al actualizar precio: {str(e)}")
            return {"success": False, "error": str(e)}
