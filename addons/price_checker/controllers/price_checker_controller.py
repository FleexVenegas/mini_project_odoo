from odoo import http
from odoo.http import request

import logging

_logger = logging.getLogger(__name__)


class PriceCheckerController(http.Controller):

    @http.route("/price-checker", type="http", auth="public", website=True)
    def price_checker_landing(self, **kw):
        """
        Ruta principal - muestra selector de sucursal
        """
        # Obtener todas las sucursales activas
        warehouses = request.env["stock.warehouse"].sudo().search([])

        _logger.info(
            f"Mostrando selector de sucursal. Sucursales encontradas: {len(warehouses)}"
        )

        return request.render(
            "price_checker.branch_selector", {"warehouses": warehouses}
        )

    @http.route("/price-checker/branch", type="http", auth="public", website=True)
    def price_checker(self, **kw):
        """
        Ruta del checador de precios - requiere warehouse_id
        """
        # Obtener el parámetro de búsqueda
        query = kw.get("query", "")
        warehouse_id = kw.get("warehouse_id", None)

        _logger.info(
            f"Consulta de búsqueda recibida: {query}, warehouse_id: {warehouse_id}"
        )

        # Si no hay warehouse_id, redirigir al selector
        if not warehouse_id:
            _logger.warning("No se proporcionó warehouse_id, redirigiendo al selector")
            return request.redirect("/price-checker")

        # Validar que el warehouse existe
        try:
            warehouse_id = int(warehouse_id)
            warehouse = request.env["stock.warehouse"].sudo().browse(warehouse_id)
            if not warehouse.exists():
                _logger.error(f"Warehouse {warehouse_id} no existe")
                return request.redirect("/price-checker")
        except (ValueError, TypeError):
            _logger.error(f"warehouse_id inválido: {warehouse_id}")
            return request.redirect("/price-checker")

        # Inicializar contexto con valores por defecto
        context = {
            "product": None,
            "prices": {},
            "query": query,
            "error_message": None,
            "warehouse": warehouse,
            "warehouse_id": warehouse_id,
        }

        # Si hay una consulta, buscar el producto
        if query:
            price_checker_model = request.env["price.checker"].sudo()

            # Buscar el producto (la función del modelo manejará todos los tipos de búsqueda)
            product_data = price_checker_model.find_product_price(
                name=query, warehouse_id=warehouse_id
            )

            if product_data:
                # Verificar si hay un error en la respuesta
                if "error" in product_data:
                    context["error_message"] = product_data["error"]
                    _logger.warning(f"Error en búsqueda: {product_data['error']}")
                else:
                    # Producto encontrado correctamente
                    _logger.info(f"Datos del producto encontrados: {product_data}")
                    _logger.info(f"Precios: {product_data.get('prices', {})}")
                    context.update(
                        {
                            "product": product_data,
                            "prices": product_data.get("prices", {}),
                        }
                    )
            else:
                context["error_message"] = (
                    f'No se encontró ningún producto con: "{query}"'
                )

        return request.render("price_checker.price_checker_form", context)
