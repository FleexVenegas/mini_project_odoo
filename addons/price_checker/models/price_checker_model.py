from odoo import models, fields

import logging

_logger = logging.getLogger(__name__)


class PriceChecker(models.Model):
    _name = "price.checker"
    _description = "Price Checker"

    def find_product_price(self, sku=None, barcode=None, name=None, warehouse_id=None):
        """Buscar un producto por SKU, código de barras o nombre y obtener precios según almacén."""

        # Obtener el término de búsqueda
        search_term = sku or barcode or name
        if not search_term:
            _logger.info("No se proporcionó término de búsqueda")
            return None

        # Verificar que el warehouse_id sea válido
        if not warehouse_id:
            _logger.warning("No se proporcionó warehouse_id")
            return {"error": "Debe seleccionar un almacén"}

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
            if product:
                _logger.info(
                    f"✓ Producto encontrado por SKU: {product.name} (ID: {product.id})"
                )
        except Exception as e:
            _logger.error(f"Error en búsqueda por SKU: {e}")

        # 2. Buscar por código de barras exacto
        if not product:
            _logger.info(f"2. Buscando por código de barras exacto: '{search_term}'")
            try:
                domain = [("barcode", "=", search_term)]
                product = Product.search(domain, limit=1)
                if product:
                    _logger.info(
                        f"✓ Producto encontrado por código de barras: {product.name} (ID: {product.id})"
                    )
            except Exception as e:
                _logger.error(f"Error en búsqueda por código de barras: {e}")

        if not product:
            _logger.warning(f"No se encontró producto con: {search_term}")
            return None

        # Obtener el almacén y sus listas de precios
        warehouse = self.env["stock.warehouse"].sudo().browse(warehouse_id)

        if not warehouse.exists():
            _logger.error(f"El almacén con ID {warehouse_id} no existe")
            return {"error": "Almacén no encontrado"}

        if not warehouse.price_checker_pricelist_id:
            _logger.warning(
                f"El almacén '{warehouse.name}' no tiene listas de precios asignadas"
            )
            # Devolver solo precio de lista
            price_with_tax = product.lst_price * 1.16
            return {
                "id": product.id,
                "name": product.name,
                "sku": product.default_code,
                "barcode": product.barcode,
                "prices": {"Precio de lista": {"value": price_with_tax, "label": None}},
                "image_1920": self._get_product_image(product),
                "warehouse": warehouse.name,
            }

        pricelists = warehouse.price_checker_pricelist_id
        _logger.info(
            f"Usando almacén: {warehouse.name} ({warehouse.identifier_name or 'Sin identificador'}) con {len(pricelists)} lista(s) de precios"
        )

        # Obtener diferentes precios según las listas de precios
        prices = self._get_product_prices(product, pricelists, warehouse)

        # Si no hay precios específicos, usar precio de lista
        if not prices:
            price_with_tax = product.lst_price * 1.16
            prices["Precio de lista"] = {"value": price_with_tax, "label": None}

        return {
            "id": product.id,
            "name": product.name,
            "sku": product.default_code,
            "barcode": product.barcode,
            "prices": prices,
            "image_1920": self._get_product_image(product),
            "warehouse": warehouse.name,
            "warehouse_identifier": warehouse.identifier_name or warehouse.name,
        }

    def _get_product_image(self, product):
        """Obtener la imagen del producto en formato base64."""
        image = product.image_1920
        if isinstance(image, bytes):
            image = image.decode()
        return image

    def _get_product_prices(self, product, pricelists, warehouse):
        """Obtener precios del producto para cada lista de precios con etiquetas específicas por almacén."""
        prices = {}
        base_price = product.lst_price

        # Obtener todas las etiquetas configuradas para este almacén
        LabelModel = self.env["pricelist.warehouse.label"].sudo()
        labels_config = LabelModel.search(
            [("warehouse_id", "=", warehouse.id), ("enable_label", "=", True)]
        )

        # Crear un diccionario para acceso rápido: {pricelist_id: label_text}
        labels_by_pricelist = {
            label.pricelist_id.id: label.label_text for label in labels_config
        }

        for pricelist in pricelists:
            if not pricelist:
                continue

            try:
                # Usar alias si está definido, si no usar el nombre de la lista
                display_name = pricelist.price_checker_alias or pricelist.name

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

                    # Buscar etiqueta específica para esta combinación de almacén + lista de precios
                    label_text = labels_by_pricelist.get(pricelist.id, None)

                    # Crear estructura con precio y etiqueta condicional
                    prices[display_name] = {
                        "value": price_with_tax,
                        "label": label_text,
                    }

                    _logger.info(
                        f"Precio de '{display_name}': ${price_with_tax:.2f} (sin IVA: ${pricelist_price:.2f})"
                        + (f" - Etiqueta: '{label_text}'" if label_text else "")
                    )
                else:
                    # El precio no cambió, no hay regla específica para este producto
                    prices[display_name] = {"value": 0.0, "label": None}
                    _logger.info(
                        f"Sin regla específica en '{display_name}' - usando precio base: ${base_price:.2f}"
                    )

            except Exception as e:
                _logger.error(f"Error obteniendo precio de '{display_name}': {e}")
                prices[display_name] = {"value": 0.0, "label": None}

        return prices
