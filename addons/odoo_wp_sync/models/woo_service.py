"""
Servicio HTTP centralizado para la integración con WooCommerce.

Toda comunicación HTTP con la API de WooCommerce (REST v3) y la API
de WordPress (wp/v2/media) pasa por este servicio.  Los modelos de
negocio (woo.product, odoo.wp.sync, etc.) NUNCA importan ni usan
la librería ``requests`` directamente.
"""

import base64
import logging

import requests

from odoo import models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

_WC_PAGE_SIZE = 100  # máximo permitido por la API de WooCommerce


class WooService(models.AbstractModel):
    _name = "woo.service"
    _description = "WooCommerce HTTP Integration Service"

    # ── Configuración ────────────────────────────────────────────────────────

    def _get_config(self, instance=None):
        """
        Obtiene las credenciales de conexión a WooCommerce.

        Prioridad:
          1. Instancia explícita (recomendado para multi-instancia).
          2. Instancia por defecto.
          3. Parámetros legacy de ir.config_parameter.
        """
        if instance:
            return instance.get_api_credentials()

        default_instance = self.env["woo.instance"].get_default_instance()
        if default_instance:
            return default_instance.get_api_credentials()

        # Fallback: parámetros legacy (compatibilidad)
        params = self.env["ir.config_parameter"].sudo()
        url = params.get_param("odoo_wp_sync.wp_url")
        ck = params.get_param("odoo_wp_sync.wp_ck")
        cs = params.get_param("odoo_wp_sync.wp_cs")

        if url and ck and cs:
            return {
                "url": url,
                "consumer_key": ck,
                "consumer_secret": cs,
            }

        raise UserError(
            _(
                "No hay instancia WooCommerce configurada. "
                "Crea una en Configuración → Instancias WooCommerce."
            )
        )

    # ── HTTP genérico (WooCommerce REST v3) ──────────────────────────────────

    def _request(self, endpoint, method="GET", data=None, instance=None, timeout=15):
        """
        Ejecuta una petición HTTP contra la WC REST API v3.

        Args:
            endpoint: ruta relativa (ej. ``orders``, ``products/123``)
            method: GET | POST | PUT | DELETE
            data: payload dict (para POST/PUT)
            instance: registro ``woo.instance`` (usa default si no se indica)
            timeout: segundos de timeout (default 15)

        Returns:
            dict | list: JSON de respuesta

        Raises:
            Exception: errores de API o de conexión
        """
        config = self._get_config(instance)
        url = f"{config['url']}/wp-json/wc/v3/{endpoint}"

        try:
            response = requests.request(
                method,
                url,
                auth=(config["consumer_key"], config["consumer_secret"]),
                json=data,
                timeout=timeout,
            )

            if response.status_code in (200, 201):
                return response.json()

            # Parsear error
            try:
                error = response.json()
                message = error.get("message", "Error desconocido")
            except Exception:
                message = response.text

            raise Exception(f"[{response.status_code}] {message}")

        except requests.exceptions.RequestException as e:
            raise Exception(f"Error de conexión: {str(e)}")

    # ── Conexión ─────────────────────────────────────────────────────────────

    def test_connection(self, instance):
        """
        Prueba la conexión con la API de WooCommerce.

        Returns:
            dict con claves:
              - ``success``: bool
              - ``status_code``: int (solo si hubo respuesta HTTP)
              - ``response``: requests.Response (solo si hubo respuesta HTTP)
              - ``error``: str tipo de error (``timeout``, ``connection``, ``unexpected``)
              - ``message``: str detalle del error
        """
        try:
            response = requests.get(
                f"{instance.wp_url}/wp-json/wc/v3/system_status",
                auth=(instance.consumer_key, instance.consumer_secret),
                timeout=10,
            )
            return {
                "success": response.status_code == 200,
                "status_code": response.status_code,
                "response": response,
            }
        except requests.exceptions.Timeout:
            return {"success": False, "error": "timeout"}
        except requests.exceptions.ConnectionError:
            return {"success": False, "error": "connection"}
        except Exception as e:
            return {"success": False, "error": "unexpected", "message": str(e)}

    # ── Media (WordPress REST v2) ────────────────────────────────────────────

    def upload_image(self, instance, image_b64, product_ref="new"):
        """
        Sube una imagen binaria (base64) al Media Library de WordPress.

        Args:
            instance: registro ``woo.instance``
            image_b64: contenido de la imagen codificado en base64
            product_ref: referencia para el nombre del archivo (woo_id o ``new``)

        Returns:
            tuple(int|None, str): ``(media_id, src_url)`` o ``(None, '')`` si falla
        """
        if not image_b64:
            return None, ""

        image_data = base64.b64decode(image_b64)

        # Detectar MIME por magic bytes
        if image_data[:4] == b"\x89PNG":
            mime, ext = "image/png", "png"
        elif image_data[:2] == b"\xff\xd8":
            mime, ext = "image/jpeg", "jpg"
        elif image_data[:4] == b"GIF8":
            mime, ext = "image/gif", "gif"
        elif image_data[:4] == b"RIFF" and image_data[8:12] == b"WEBP":
            mime, ext = "image/webp", "webp"
        else:
            mime, ext = "image/jpeg", "jpg"

        filename = f"woo_product_{product_ref}.{ext}"
        config = self._get_config(instance)
        url = f"{config['url']}/wp-json/wp/v2/media"

        try:
            response = requests.post(
                url,
                auth=(config["consumer_key"], config["consumer_secret"]),
                headers={
                    "Content-Disposition": f'attachment; filename="{filename}"',
                    "Content-Type": mime,
                },
                data=image_data,
                timeout=30,
            )
            if response.status_code in (200, 201):
                media = response.json()
                return media.get("id"), media.get("source_url", "")
            _logger.warning(
                "WP Media upload returned %s: %s",
                response.status_code,
                response.text[:300],
            )
        except Exception as exc:
            _logger.warning("Error uploading image to WordPress: %s", str(exc))

        return None, ""

    # ── Productos ────────────────────────────────────────────────────────────

    def create_product(self, instance, payload):
        """Crea un producto en WooCommerce (POST ``products``)."""
        return self._request(
            endpoint="products",
            method="POST",
            data=payload,
            instance=instance,
        )

    def update_product(self, instance, woo_id, payload):
        """Actualiza un producto en WooCommerce (PUT ``products/{id}``)."""
        return self._request(
            endpoint=f"products/{woo_id}",
            method="PUT",
            data=payload,
            instance=instance,
        )

    def fetch_products(self, instance):
        """
        Obtiene todos los productos de WooCommerce con paginación automática.

        Returns:
            list[dict]: lista completa de productos WooCommerce
        """
        all_products = []
        page = 1

        while True:
            endpoint = (
                f"products?per_page={_WC_PAGE_SIZE}&page={page}"
                f"&orderby=id&order=asc&status=any"
            )
            batch = self._request(endpoint=endpoint, instance=instance)
            if not batch:
                break
            all_products.extend(batch)
            if len(batch) < _WC_PAGE_SIZE:
                break
            page += 1

        _logger.info(
            "Fetched %d products from WooCommerce instance '%s'",
            len(all_products),
            instance.name,
        )
        return all_products

    # ── Pedidos ──────────────────────────────────────────────────────────────

    def fetch_orders(self, instance, params):
        """
        Obtiene pedidos de WooCommerce con paginación automática.

        Args:
            instance: registro ``woo.instance``
            params: dict con parámetros de query (``per_page``, ``status``, …)

        Returns:
            list[dict]: lista de pedidos WooCommerce
        """
        param_string = "&".join([f"{k}={v}" for k, v in params.items()])
        base_endpoint = f"orders?{param_string}"
        all_orders = []
        page = 1
        max_pages = 100

        while page <= max_pages:
            endpoint = f"{base_endpoint}&page={page}"
            orders = self._request(endpoint=endpoint, instance=instance)
            if not orders:
                break
            all_orders.extend(orders)
            if len(orders) < params.get("per_page", 50):
                break
            page += 1

        _logger.info(
            "Fetched %d orders from instance '%s' in %d page(s)",
            len(all_orders),
            instance.name,
            page,
        )
        return all_orders

    def update_order_status(self, instance, wc_order_id, new_status):
        """
        Actualiza el estado de un pedido en WooCommerce.

        Args:
            instance: registro ``woo.instance``
            wc_order_id: ID del pedido en WooCommerce
            new_status: nuevo estado (``pending``, ``processing``, ``completed``, …)

        Returns:
            dict: respuesta JSON de WooCommerce
        """
        return self._request(
            endpoint=f"orders/{wc_order_id}",
            method="PUT",
            data={"status": new_status},
            instance=instance,
        )

    # ── Categorías ───────────────────────────────────────────────────────────

    def fetch_categories(self, instance):
        """
        Obtiene todas las categorías de WooCommerce con paginación automática.

        Returns:
            list[dict]: lista completa de categorías WooCommerce
              Cada item tiene: id, name, slug, parent (id del padre, 0 si raíz)
        """
        all_categories = []
        page = 1

        while True:
            batch = self._request(
                endpoint=f"products/categories?per_page={_WC_PAGE_SIZE}&page={page}&orderby=id&order=asc",
                instance=instance,
            )
            if not batch:
                break
            all_categories.extend(batch)
            if len(batch) < _WC_PAGE_SIZE:
                break
            page += 1

        _logger.info(
            "Fetched %d categories from WooCommerce instance '%s'",
            len(all_categories),
            instance.name,
        )
        return all_categories

    # ── Marcas ───────────────────────────────────────────────────────────────

    def fetch_brands(self, instance):
        """
        Obtiene todas las marcas de WooCommerce con paginación automática.

        Compatible con los endpoints más comunes:
          - ``/wc/v3/products/brands`` (Perfect WooCommerce Brands)
          - ``/wc/v3/brands`` (WooCommerce Brands oficial)

        Returns:
            list[dict] | []: lista de marcas, o lista vacía si el plugin no está activo.
        """
        all_brands = []
        page = 1

        # Intentar con el endpoint más común (Perfect WooCommerce Brands / oficial)
        try:
            while True:
                batch = self._request(
                    endpoint=f"products/brands?per_page={_WC_PAGE_SIZE}&page={page}",
                    instance=instance,
                )
                if not batch:
                    break
                all_brands.extend(batch)
                if len(batch) < _WC_PAGE_SIZE:
                    break
                page += 1
        except Exception:
            # El plugin de marcas no está instalado o usa otro endpoint
            _logger.info(
                "No brand plugin found for instance '%s' (endpoint products/brands not available).",
                instance.name,
            )

        _logger.info(
            "Fetched %d brands from WooCommerce instance '%s'",
            len(all_brands),
            instance.name,
        )
        return all_brands
