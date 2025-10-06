from odoo import models, fields

import logging

_logger = logging.getLogger(__name__)


class PriceChecker(models.Model):
    _name = "price.checker"
    _description = "Price Checker"

    def find_product_price(self, sku=None, barcode=None, name=None):
        """Buscar un producto por SKU, código de barras o nombre y devolver precios"""

        # Obtener el término de búsqueda
        search_term = sku or barcode or name
        if not search_term:
            _logger.info("No se proporcionó término de búsqueda")
            return None

        _logger.info(f"=== INICIANDO BÚSQUEDA ===")
        _logger.info(
            f"Término de búsqueda: '{search_term}' (tipo: {type(search_term)})"
        )
        _logger.info(f"Parámetros - SKU: {sku}, Barcode: {barcode}, Name: {name}")

        # Verificar que el modelo product.product existe y tiene datos
        Product = self.env["product.product"].sudo()
        total_products = Product.search_count([])
        _logger.info(f"Total de productos en la base de datos: {total_products}")

        if total_products == 0:
            _logger.error("No hay productos en la base de datos")
            return None

        product = False

        # 1. Buscar por SKU exacto
        _logger.info(f"1. Buscando por SKU exacto: '{search_term}'")
        try:
            domain = [("default_code", "=", search_term)]
            product = Product.search(domain, limit=1)
            _logger.info(f"   Resultado SKU: {len(product)} productos encontrados")
            if product:
                _logger.info(
                    f"   ✓ Producto encontrado por SKU: {product.name} (ID: {product.id})"
                )
        except Exception as e:
            _logger.error(f"   Error en búsqueda por SKU: {e}")

        # 2. Buscar por código de barras exacto
        if not product:
            _logger.info(f"2. Buscando por código de barras exacto: '{search_term}'")
            try:
                domain = [("barcode", "=", search_term)]
                product = Product.search(domain, limit=1)
                _logger.info(
                    f"   Resultado Barcode: {len(product)} productos encontrados"
                )
                if product:
                    _logger.info(
                        f"   ✓ Producto encontrado por código de barras: {product.name} (ID: {product.id})"
                    )
            except Exception as e:
                _logger.error(f"   Error en búsqueda por código de barras: {e}")

        # 3. Buscar por nombre (parcial)
        if not product:
            _logger.info(f"3. Buscando por nombre parcial: '{search_term}'")
            try:
                domain = [("name", "ilike", search_term)]
                products = Product.search(domain, limit=3)
                _logger.info(
                    f"   Resultado Name: {len(products)} productos encontrados"
                )
                if products:
                    product = products[0]
                    _logger.info(
                        f"   ✓ Producto encontrado por nombre: {product.name} (ID: {product.id})"
                    )
                    # Log otros productos encontrados
                    for i, p in enumerate(products[1:3], 1):
                        _logger.info(f"   - Alternativa {i}: {p.name}")
            except Exception as e:
                _logger.error(f"   Error en búsqueda por nombre: {e}")

        _logger.info(f"=== RESULTADO FINAL ===")
        _logger.info(f"Producto encontrado: {product.name if product else 'NINGUNO'}")

        if not product:
            return None

        # Obtener diferentes precios según las listas de precios
        prices = {}

        # Lista de precios que queremos mostrar (puedes personalizar estos nombres)
        price_lists = [
            ("High Runner", "High Runner"),
            ("LISTA MEDIO MAYOREO OBREGON", "Medio mayoreo"),
            ("LISTA MAYOREO CONTADO OBREGON", "Mayoreo"),
        ]

        for pricelist_name, display_name in price_lists:
            pricelist = (
                self.env["product.pricelist"]
                .sudo()
                .search([("name", "=", pricelist_name)], limit=1)
            )
            if pricelist:
                try:
                    # Obtener precio base del producto
                    base_price = product.lst_price

                    # Obtener precio de la lista de precios
                    pricelist_price = pricelist._get_product_price(
                        product, 1.0, uom=product.uom_id
                    )

                    # Si el precio de la lista es diferente al precio base,
                    # significa que hay una regla aplicable para este producto
                    if (
                        abs(pricelist_price - base_price) > 0.01
                    ):  # Tolerancia para decimales
                        # Aplicar IVA del 16% (multiplicar por 1.16)
                        price_with_tax = pricelist_price * 1.16
                        prices[display_name] = price_with_tax
                        _logger.info(
                            f"Precio obtenido de '{display_name}': ${price_with_tax:.2f} (sin IVA: ${pricelist_price:.2f}, base: ${base_price:.2f})"
                        )
                    else:
                        # El precio no cambió, no hay regla específica para este producto
                        prices[display_name] = 0.0
                        _logger.info(
                            f"Sin regla específica en '{display_name}' - precio: $0.00 (base: ${base_price:.2f})"
                        )

                except Exception as e:
                    _logger.error(f"Error obteniendo precio de '{display_name}': {e}")
                    # Si hay error obteniendo el precio, poner en cero
                    prices[display_name] = 0.0
            else:
                # Si no existe la lista de precios, poner precio en cero
                prices[display_name] = 0.0
                _logger.info(
                    f"Lista de precios '{pricelist_name}' no encontrada - precio: $0.00"
                )

        # Si no hay listas de precios específicas, usar precio de lista con IVA
        if not prices:
            price_with_tax = product.lst_price * 1.16
            prices["Precio de lista"] = price_with_tax

        return {
            "id": product.id,
            "name": product.name,
            "sku": product.default_code,
            "barcode": product.barcode,
            "prices": prices,
        }
