from odoo import http
from odoo.http import request, Response
import json

import logging

_logger = logging.getLogger(__name__)


class PriceCheckerSfController(http.Controller):
    @staticmethod
    def _respond(data, status=200):
        return Response(
            json.dumps(data),
            content_type="application/json",
            status=status,
        )

    def _error_response(self, message, status=400, **extra):
        payload = {
            "error": True,
            "message": message,
        }
        payload.update(extra)
        return self._respond(payload, status=status)

    def _parse_json_body(self):
        try:
            body = json.loads(request.httprequest.data or "{}")
        except json.JSONDecodeError:
            return None

        if not isinstance(body, dict):
            return None

        return body

    @http.route("/warehouse", type="http", auth="public", website=True)
    def get_warehouses(self, **kw):
        """
        Ruta para obtener las sucursales disponibles
        """
        warehouses = request.env["stock.warehouse"].sudo().search([])
        data = []

        for wh in warehouses:
            data.append({
                "id": wh.id,
                "name": wh.name,
                "code": wh.code,
                "company_id": wh.company_id.id,
                "company_name": wh.company_id.name,
            })
        _logger.info(f"Warehouses found: {data}")

        return self._respond(data)
    
    @http.route("/warehouse/products/prices", type="http", auth="public", csrf=False, methods=["POST"])
    def get_products_prices(self, **kw):
        body = self._parse_json_body()
        if body is None:
            return self._error_response("JSON inválido", status=400)

        warehouse_id = body.get("warehouse_id")

        warehouse, error = self._resolve_warehouse(warehouse_id)
        if error:
            return self._error_response(error, status=400)

        products = request.env["price.checker"].sudo().get_all_products_with_prices(
            warehouse_id=warehouse.id,
        )

        return self._respond({
            "warehouse_id": warehouse.id,
            "total": len(products),
            "products": products,
        })
    
    @http.route("/warehouse/products", type="http", auth="public", csrf=False, methods=["GET"])
    def get_products(self, **kw):
        try:
            products = request.env["price.checker"].sudo().get_all_products()

            return self._respond({
                "total": len(products),
                "products": products,
            }, status=200)

        except Exception as e:
            _logger.error(f"Error al obtener productos: {e}")
            return self._error_response(str(e), status=500)
    
    @http.route("/warehouse/branch", type="http", auth="public", csrf=False, methods=["POST"])
    def price_checker(self, **kw):
        body = self._parse_json_body()
        if body is None:
            return self._error_response("JSON inválido", status=400)

        query = body.get("query", "").strip()
        warehouse_id = body.get("warehouse_id")

        warehouse, error = self._resolve_warehouse(warehouse_id)
        if error:
            return self._error_response(error, status=400)

        if not query:
            return self._respond({
                "query": query,
                "warehouse": {
                    "id": warehouse.id,
                    "name": warehouse.name,
                    "code": warehouse.code,
                },
                "product": None,
            })

        product_data = request.env["price.checker"].sudo().find_product_price(
            name=query,
            warehouse_id=warehouse.id,
        )

        if not product_data:
            return self._error_response(f'No se encontró: "{query}"', status=404)

        if "error" in product_data:
            return self._error_response(product_data["error"], status=400)

        return self._respond({"product": product_data})

    def _resolve_warehouse(self, warehouse_id):
        if not warehouse_id:
            return None, "warehouse_id requerido"
        try:
            wid = int(warehouse_id)
        except (ValueError, TypeError):
            return None, "warehouse_id inválido"

        warehouse = request.env["stock.warehouse"].sudo().browse(wid)
        if not warehouse.exists():
            return None, "Warehouse no existe"

        return warehouse, None

