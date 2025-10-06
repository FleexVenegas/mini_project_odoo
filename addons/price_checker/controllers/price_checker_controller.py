from odoo import http
from odoo.http import request

import logging

_logger = logging.getLogger(__name__)


class PriceCheckerController(http.Controller):

    @http.route("/price-checker", type="http", auth="public", website=True)
    def price_checker(self, **kw):
        # Obtener el parámetro de búsqueda
        query = kw.get("query", "")

        _logger.info(f"Consulta de búsqueda recibida: {query}")

        # Inicializar contexto con valores por defecto
        context = {"product": None, "prices": {}, "query": query, "error_message": None}

        # Si hay una consulta, buscar el producto
        if query:
            price_checker_model = request.env["price.checker"].sudo()

            # Buscar el producto (la función del modelo manejará todos los tipos de búsqueda)
            product_data = price_checker_model.find_product_price(name=query)

            if product_data:
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
