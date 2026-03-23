from odoo import models, fields, api
import re
import logging
from datetime import datetime
import pytz
from odoo.addons.modulo_costo_ponderado_stock.models.pricing_tools import (
    calcular_precio_debug,
    calcular_precio_mxn_debug,
)

_logger = logging.getLogger(__name__)


class StockPricelistReport(models.Model):
    _name = "stock.pricelist.report"
    _description = "Reporte de Stock y Lista de Precios"
    _auto = True

    # Variable de control - Cambie esto a False para solo registrar los stocks en logs
    _execute_normal_mode = (
        True  # True = ejecuta todo normal, False = solo registra stocks en logs
    )

    product_id = fields.Many2one("product.product", string="Producto", readonly=True)
    unit_weighted_cost = fields.Float(
        string="Costo", digits="Product Price", readonly=True
    )
    current_stock = fields.Float(string="Existencias", readonly=True)
    currency_id = fields.Many2one("res.currency", string="Moneda", readonly=True)
    currency_display = fields.Char(string="Moneda", readonly=True)
    pricelist_id = fields.Many2one(
        "product.pricelist", string="Lista de Precios", readonly=True
    )
    price = fields.Float(string="Precio", digits="Product Price", readonly=True)

    referencia = fields.Char(
        string="Referencia", compute="_compute_parsed_fields", store=True
    )
    disenador = fields.Char(
        string="Diseñador", compute="_compute_parsed_fields", store=True
    )
    descripcion = fields.Char(
        string="Descripción", compute="_compute_parsed_fields", store=True
    )
    tamano = fields.Char(string="Tamaño", compute="_compute_parsed_fields", store=True)
    genero = fields.Char(string="Genero", compute="_compute_parsed_fields", store=True)

    tipo = fields.Char(
        string="Tipo", compute="_compute_extra_fields", store=True, default="Unidad"
    )
    stock_showroom_central = fields.Float(
        string="Stock Showroom Central", compute="_compute_extra_fields", store=True
    )
    stock_showroom_obregon = fields.Float(
        string="Stock Showroom Obregón", compute="_compute_extra_fields", store=True
    )

    @api.depends("product_id.name")
    def _compute_parsed_fields(self):
        for record in self:
            referencia = disenador = descripcion = tamano = ""
            product_name = (
                record.product_id.display_name or record.product_id.name or ""
            )

            ref_match = re.search(r"\[(.*?)\]", product_name)
            if ref_match:
                referencia = ref_match.group(1).strip()

            dis_match = re.search(r"\]\s*([^-\[]+)-", product_name)
            if dis_match:
                disenador = dis_match.group(1).strip()

            desc_match = re.search(r"-\s*(.*)", product_name)
            if desc_match:
                descripcion = desc_match.group(1).strip()

            tam_match = re.search(r"(\d+\s*[Mm][Ll])", product_name)
            if tam_match:
                tamano = tam_match.group(1).replace(" ", "").upper()

            name_lower = product_name.lower()
            if "dama" in name_lower:
                genero = "DAMA"
            elif "caballero" in name_lower:
                genero = "CABALLERO"
            else:
                genero = ""

            record.referencia = referencia
            record.disenador = disenador
            record.descripcion = descripcion
            record.tamano = tamano
            record.genero = genero

    def _get_stock_by_warehouse(self, product_id, warehouse_names):
        """Obtiene el stock total de un producto en los almacenes especificados"""
        try:
            # Buscar los almacenes por nombre
            warehouses = self.env["stock.warehouse"].search(
                [("name", "in", warehouse_names)]
            )

            if not warehouses:
                _logger.warning(
                    f"No se encontraron almacenes con nombres: {warehouse_names}"
                )
                return 0.0

            # Obtener todas las ubicaciones de estos almacenes
            location_ids = []
            for warehouse in warehouses:
                # Incluir la ubicación de stock principal y todas sus hijas
                all_locations = self.env["stock.location"].search(
                    [("id", "child_of", warehouse.lot_stock_id.id)]
                )
                location_ids.extend(all_locations.ids)

            if not location_ids:
                return 0.0

            # Buscar el stock disponible en estas ubicaciones
            stock_quants = self.env["stock.quant"].search(
                [("product_id", "=", product_id), ("location_id", "in", location_ids)]
            )

            total_stock = sum(
                quant.quantity - quant.reserved_quantity for quant in stock_quants
            )

            return total_stock

        except Exception as e:
            _logger.error(
                f"Error al obtener stock para producto {product_id}: {str(e)}"
            )
            return 0.0

    def _get_warehouse_location_ids(self, warehouse_names):
        """Obtiene los IDs de ubicaciones de almacenes (para cachear)"""
        try:
            warehouses = self.env["stock.warehouse"].search(
                [("name", "in", warehouse_names)]
            )
            if not warehouses:
                _logger.warning(
                    f"No se encontraron almacenes con nombres: {warehouse_names}"
                )
                return []

            location_ids = []
            for warehouse in warehouses:
                all_locations = self.env["stock.location"].search(
                    [("id", "child_of", warehouse.lot_stock_id.id)]
                )
                location_ids.extend(all_locations.ids)

            return location_ids
        except Exception as e:
            _logger.error(f"Error al obtener ubicaciones: {str(e)}")
            return []

    def _get_bulk_stock_by_locations(self, product_ids, location_ids):
        """Obtiene stocks de múltiples productos en ubicaciones específicas (query masiva)"""
        if not location_ids or not product_ids:
            return {}

        try:
            # Query SQL optimizada para obtener todos los stocks de una vez
            query = """
                SELECT product_id, 
                       SUM(quantity - reserved_quantity) as available_qty
                FROM stock_quant
                WHERE product_id IN %s
                  AND location_id IN %s
                GROUP BY product_id
            """
            self.env.cr.execute(query, (tuple(product_ids), tuple(location_ids)))
            results = self.env.cr.fetchall()

            # Convertir a diccionario {product_id: stock}
            stock_dict = {row[0]: row[1] for row in results}

            # Asegurar que todos los productos tengan una entrada (0.0 si no hay stock)
            return {pid: stock_dict.get(pid, 0.0) for pid in product_ids}

        except Exception as e:
            _logger.error(f"Error en consulta masiva de stocks: {str(e)}")
            return {pid: 0.0 for pid in product_ids}

    @api.depends("product_id.name")
    def _compute_extra_fields(self):
        """Determina el tipo y obtiene el stock de los dos almacenes SHOWROOM"""
        for record in self:
            product = record.product_id
            tipo = ""
            stock_central = 0.0
            stock_obregon = 0.0

            if product:
                name_lower = product.display_name.lower()
                if "set de dama" in name_lower:
                    tipo = "Set de dama"
                elif "set de caballero" in name_lower:
                    tipo = "Set de caballero"
                elif "kit" in name_lower:
                    tipo = "Kit"
                elif "unidad" in name_lower:
                    tipo = "Unidad"
                elif "tester" in name_lower:
                    tipo = "Tester"
                elif "combo" in name_lower:
                    tipo = "Combo"

                # Obtener stock usando el método corregido
                stock_central = self._get_stock_by_warehouse(
                    product.id, ["SHOWROOM CENTRAL"]
                )
                stock_obregon = self._get_stock_by_warehouse(
                    product.id, ["SHOWROOM OBREGON"]
                )

            record.tipo = tipo
            record.stock_showroom_central = stock_central
            record.stock_showroom_obregon = stock_obregon

    def actualizar_precio_lista(
        self, pricelist_id, product_id, nuevo_precio, update_mode="all"
    ):
        """Actualiza el precio de un producto en una lista de precios (solo si ya existe y cambió)

        Args:
            pricelist_id (int): ID de la lista de precios
            product_id (int): ID del producto
            nuevo_precio (float): Nuevo precio a establecer
            update_mode (str): 'all' = actualizar todos, 'zero_or_negative' = solo precios <= 0

        Returns:
            dict: Resultado de la operación con 'success', 'action' y 'message'
        """
        try:
            # Buscar item existente en la lista de precios
            pricelist_item = self.env["product.pricelist.item"].search(
                [
                    ("pricelist_id", "=", pricelist_id),
                    "|",
                    "&",
                    ("applied_on", "=", "1_product"),
                    ("product_tmpl_id", "=", product_id),
                    "&",
                    ("applied_on", "=", "0_product_variant"),
                    ("product_id", "=", product_id),
                ],
                limit=1,
            )

            if pricelist_item:
                precio_actual = pricelist_item.fixed_price or 0.0

                # Validar modo de actualización
                if update_mode == "zero_or_negative" and precio_actual > 0:
                    return {
                        "success": True,
                        "action": "skipped_positive",
                        "message": f"Precio actual {precio_actual:.2f} > 0 (omitido por modo)",
                    }

                # Optimización: Solo actualizar si el precio cambió
                if abs(precio_actual - nuevo_precio) < 0.01:  # Tolerancia de 1 centavo
                    return {
                        "success": True,
                        "action": "unchanged",
                        "message": f"Precio sin cambios: ${nuevo_precio:.2f}",
                    }

                # Actualizar precio existente
                pricelist_item.write({"fixed_price": nuevo_precio})
                return {
                    "success": True,
                    "action": "updated",
                    "message": f"Precio actualizado: ${precio_actual:.2f} → ${nuevo_precio:.2f}",
                }
            else:
                # No existe el item, no hacer nada (solo actualizar, no crear)
                return {
                    "success": True,
                    "action": "skipped",
                    "message": "Producto sin precio previo en esta lista (omitido)",
                }

        except Exception as e:
            _logger.error(
                f"Error al actualizar precio para producto {product_id} en lista {pricelist_id}: {str(e)}"
            )
            return {"success": False, "error": str(e)}

    def _get_products_with_zero_or_negative_prices(self, pricelist_ids):
        """Obtiene los IDs de productos que tienen precio <= 0 en las listas especificadas

        Args:
            pricelist_ids (list): IDs de las listas de precios a consultar

        Returns:
            set: Set de product_id que tienen precio <= 0 o sin precio en las listas
        """
        if not pricelist_ids:
            return set()

        try:
            product_ids_with_zero = set()

            # Query 1: Productos con precio <= 0 aplicado por variante
            query_variant = """
                SELECT DISTINCT ppi.product_id
                FROM product_pricelist_item ppi
                WHERE ppi.pricelist_id IN %s
                  AND ppi.applied_on = '0_product_variant'
                  AND ppi.product_id IS NOT NULL
                  AND (ppi.fixed_price <= 0 OR ppi.fixed_price IS NULL)
            """
            self.env.cr.execute(query_variant, (tuple(pricelist_ids),))
            results = self.env.cr.fetchall()
            product_ids_with_zero.update(row[0] for row in results if row[0])

            # Query 2: Productos con precio <= 0 aplicado por template
            query_template = """
                SELECT DISTINCT pp.id
                FROM product_pricelist_item ppi
                INNER JOIN product_product pp ON pp.product_tmpl_id = ppi.product_tmpl_id
                WHERE ppi.pricelist_id IN %s
                  AND ppi.applied_on = '1_product'
                  AND ppi.product_tmpl_id IS NOT NULL
                  AND (ppi.fixed_price <= 0 OR ppi.fixed_price IS NULL)
            """
            self.env.cr.execute(query_template, (tuple(pricelist_ids),))
            results = self.env.cr.fetchall()
            product_ids_with_zero.update(row[0] for row in results if row[0])

            # Query 3: Productos que NO tienen ningún item en estas listas
            # (productos sin precio definido)
            all_products_query = """
                SELECT DISTINCT pp.id
                FROM product_product pp
                WHERE NOT EXISTS (
                    SELECT 1 FROM product_pricelist_item ppi
                    WHERE ppi.pricelist_id IN %s
                      AND (
                          (ppi.applied_on = '0_product_variant' AND ppi.product_id = pp.id)
                          OR (ppi.applied_on = '1_product' AND ppi.product_tmpl_id = pp.product_tmpl_id)
                      )
                )
            """
            self.env.cr.execute(all_products_query, (tuple(pricelist_ids),))
            results = self.env.cr.fetchall()
            product_ids_with_zero.update(row[0] for row in results if row[0])

            return product_ids_with_zero

        except Exception as e:
            _logger.error(f"Error al obtener productos con precio <= 0: {str(e)}")
            return set()

    def reload_report(self, pricelist_ids=None, update_mode="all"):
        """Método manual para recargar el reporte completo

        Args:
            pricelist_ids (list, optional): IDs de las listas de precios a procesar.
                                            Si es None, procesa todas las listas.
            update_mode (str): 'all' = actualizar todos los precios,
                              'zero_or_negative' = solo actualizar precios <= 0
        """
        # Modo solo logs - Solo registra los stocks en los logs
        if not self._execute_normal_mode:
            _logger.info("Modo diagnóstico: Mostrando solo stocks de Showroom")

            try:
                weighted_records = self.env["stock.weighted"].search([])

                for w in weighted_records:
                    if not w.product_id:
                        continue

                    product = w.product_id

                    # Obtener stock usando el método corregido
                    stock_central = self._get_stock_by_warehouse(
                        product.id, ["SHOWROOM CENTRAL"]
                    )
                    stock_obregon = self._get_stock_by_warehouse(
                        product.id, ["SHOWROOM OBREGON"]
                    )

                    # Registrar la información del stock en el log
                    _logger.info(f"Producto: {product.display_name}")
                    _logger.info(f"Referencia: {product.default_code or 'N/A'}")
                    _logger.info(f"Showroom Central: {stock_central}")
                    _logger.info(f"Showroom Obregón: {stock_obregon}")

                    # También registrar el stock total del sistema para comparar
                    stock_total = product.qty_available
                    _logger.info(f"Stock total en sistema: {stock_total}")
                    _logger.info("-" * 80)

                _logger.info("Modo diagnóstico: Registro de stocks completado")
                return {
                    "type": "ir.actions.client",
                    "tag": "display_notification",
                    "params": {
                        "title": "Modo Diagnóstico",
                        "message": "Stocks de Showroom registrados en consola",
                        "type": "info",
                        "sticky": False,
                    },
                }

            except Exception as e:
                _logger.error(f"Error en modo diagnóstico: {str(e)}")
                return {
                    "type": "ir.actions.client",
                    "tag": "display_notification",
                    "params": {
                        "title": "Error Diagnóstico",
                        "message": f"Error al registrar stocks: {str(e)}",
                        "type": "danger",
                        "sticky": True,
                    },
                }

        # Modo normal - Ejecuta todo como siempre (OPTIMIZADO)
        _logger.info("⚙️  Iniciando recarga del reporte...")

        total_products_initial = 0  # Inicializar para uso en except/else

        try:
            # Obtener listas de precios a procesar
            if pricelist_ids:
                pricelists = self.env["product.pricelist"].browse(pricelist_ids)
                # Eliminar solo registros de las listas seleccionadas
                existing_records = self.search([("pricelist_id", "in", pricelist_ids)])
                if existing_records:
                    existing_records.unlink()
                    _logger.info(
                        f"🗑️  Eliminados {len(existing_records)} registros de {len(pricelists)} listas seleccionadas"
                    )
            else:
                # Procesar todas las listas (comportamiento original)
                pricelists = self.env["product.pricelist"].search([])
                existing_records = self.search([])
                if existing_records:
                    existing_records.unlink()
                    _logger.info(
                        f"🗑️  Eliminados {len(existing_records)} registros existentes"
                    )

            # Obtener datos frescos desde stock.weighted
            weighted_records = self.env["stock.weighted"].search([])
            total_products_initial = len(weighted_records)

            # OPTIMIZACIÓN: Si modo es 'zero_or_negative', filtrar solo productos con precio <= 0
            if update_mode == "zero_or_negative":
                _logger.info(
                    f"🔍 Modo 'zero_or_negative': Filtrando productos con precio ≤ 0..."
                )
                product_ids_to_update = self._get_products_with_zero_or_negative_prices(
                    pricelist_ids or pricelists.ids
                )

                if product_ids_to_update:
                    # Filtrar weighted_records para solo incluir productos con precio <= 0
                    weighted_records = weighted_records.filtered(
                        lambda w: w.product_id
                        and w.product_id.id in product_ids_to_update
                    )
                    _logger.info(
                        f"✅ Filtrados: {len(weighted_records)} de {total_products_initial} productos requieren actualización "
                        f"({len(product_ids_to_update)} productos con precio ≤ 0)"
                    )
                else:
                    _logger.info(
                        "✅ No hay productos con precio ≤ 0. No se requiere actualización."
                    )
                    weighted_records = self.env["stock.weighted"]  # Lista vacía
            else:
                _logger.info(f"🔄 Modo 'all': Procesando todos los productos")

            total_products = len(weighted_records)

            _logger.info(
                f"📊 Procesando {total_products} productos × {len(pricelists)} listas = {total_products * len(pricelists)} registros"
            )

            # Mostrar las listas que se van a procesar
            pricelist_names = ", ".join([f"'{pl.name}'" for pl in pricelists[:5]])
            if len(pricelists) > 5:
                pricelist_names += f" y {len(pricelists) - 5} más"
            _logger.info(f"📋 Listas seleccionadas: {pricelist_names}")

            # OPTIMIZACIÓN 1: Cache de ubicaciones + OPTIMIZACIÓN 2: Query SQL masiva de stocks
            almacen_central_location_ids = self._get_warehouse_location_ids(
                ["ALMACEN CENTRAL"]
            )
            product_ids = [w.product_id.id for w in weighted_records if w.product_id]
            stock_cache = self._get_bulk_stock_by_locations(
                product_ids, almacen_central_location_ids
            )

            data_to_create = []
            processed = 0

            # Contadores de diagnóstico
            error_count = 0
            products_with_errors = set()
            error_details = []

            # Contadores de actualización de precios
            prices_updated = 0
            prices_unchanged = 0
            prices_skipped = 0
            prices_skipped_positive = 0
            prices_failed = 0

            for w in weighted_records:
                if not w.product_id:
                    continue

                # USAR STOCK DEL CACHE (ya no consulta la BD)
                stock_almacen_central = stock_cache.get(w.product_id.id, 0.0)

                product_has_error = False

                for pricelist in pricelists:
                    try:
                        # Usar partner de la compañía si el usuario no tiene
                        partner = (
                            self.env.user.partner_id or self.env.company.partner_id
                        )

                        price = pricelist._get_product_price(w.product_id, 1.0, partner)
                    except (
                        TypeError,
                        ZeroDivisionError,
                        ValueError,
                        AttributeError,
                    ) as e:
                        error_count += 1
                        if not product_has_error:
                            products_with_errors.add(w.product_id.id)
                            product_has_error = True
                            # Guardar solo info básica
                            error_details.append(
                                {
                                    "product": w.product_id.display_name,
                                    "default_code": w.product_id.default_code or "N/A",
                                    "pricelist": pricelist.name,
                                }
                            )
                        price = 0.0

                    # Actualizar precio en la lista de precios si es válido
                    if price >= 0:
                        # Calcular precio usando la lógica especializada de pricing_tools
                        try:
                            valores = calcular_precio_debug(
                                env=self.env, product=w.product_id, pricelist=pricelist
                            )

                            # Si la moneda es MXN, usar el cálculo específico para MXN
                            if w.currency_id and w.currency_id.name == "MXN":
                                try:
                                    valores_mxn = calcular_precio_mxn_debug(
                                        env=self.env,
                                        product=w.product_id,
                                        pricelist=pricelist,
                                    )
                                    if valores_mxn and not valores_mxn.get("error"):
                                        price = valores_mxn.get("resultado", price)
                                    else:
                                        price = valores.get("resultado", price)
                                except Exception as e_mxn:
                                    _logger.warning(
                                        f"Error en cálculo MXN para producto {w.product_id.id}: {str(e_mxn)}"
                                    )
                                    price = valores.get("resultado", price)
                            else:
                                # Usar el resultado del cálculo estándar
                                price = valores.get("resultado", price)

                        except Exception as e_calc:
                            _logger.warning(
                                f"Error al calcular precio con pricing_tools para producto {w.product_id.id}: {str(e_calc)}. Usando precio original."
                            )
                            # Si falla, mantener el precio original obtenido de _get_product_price

                        result = self.actualizar_precio_lista(
                            pricelist_id=pricelist.id,
                            product_id=w.product_id.id,
                            nuevo_precio=price,
                            update_mode=update_mode,
                        )
                        if result.get("success"):
                            action = result.get("action")
                            if action == "updated":
                                prices_updated += 1
                            elif action == "unchanged":
                                prices_unchanged += 1
                            elif action == "skipped":
                                prices_skipped += 1
                            elif action == "skipped_positive":
                                prices_skipped_positive += 1
                        else:
                            prices_failed += 1

                    data_to_create.append(
                        {
                            "product_id": w.product_id.id,
                            "unit_weighted_cost": w.unit_weighted_cost or 0.0,
                            "current_stock": stock_almacen_central,
                            "currency_id": (
                                w.currency_id.id
                                if w.currency_id
                                else self.env.company.currency_id.id
                            ),
                            "currency_display": w.currency_display or "",
                            "pricelist_id": pricelist.id,
                            "price": price or 0.0,
                        }
                    )

                processed += 1
                # Log de progreso cada 1000 productos
                if processed % 1000 == 0:
                    _logger.info(
                        f"Progreso: {processed}/{total_products} productos ({(processed/total_products)*100:.0f}%)"
                    )

            # Resumen de actualización de precios
            _logger.info(
                f"💲 Actualización de precios en listas (modo: {update_mode}):"
            )
            _logger.info(f"   ✓ {prices_updated} precios actualizados")
            _logger.info(f"   = {prices_unchanged} precios sin cambios")
            _logger.info(
                f"   ⊘ {prices_skipped} productos sin precio previo (omitidos)"
            )
            if prices_skipped_positive > 0:
                _logger.info(
                    f"   ⊙ {prices_skipped_positive} precios > 0 omitidos (modo zero_or_negative)"
                )
            if prices_failed > 0:
                _logger.warning(f"   ✗ {prices_failed} precios fallaron")

            # Resumen de errores (simplificado)
            if error_count > 0:
                _logger.warning(
                    f"⚠️  {len(products_with_errors)} productos con errores al calcular precios (precio = 0.0)"
                )
                ejemplos = ", ".join(
                    [f"[{d['default_code']}]" for d in error_details[:5]]
                )
                _logger.warning(f"   Ejemplos: {ejemplos}...")

            # OPTIMIZACIÓN 3: Crear registros en lotes (batch insert)
            if data_to_create:
                batch_size = 5000
                total_batches = (len(data_to_create) + batch_size - 1) // batch_size
                _logger.info(
                    f"Creando {len(data_to_create)} registros en {total_batches} lotes..."
                )

                for i in range(0, len(data_to_create), batch_size):
                    batch = data_to_create[i : i + batch_size]
                    self.create(batch)

                _logger.info(
                    f"✓ {len(data_to_create)} registros del reporte creados (visualización)"
                )

                # Obtener correos desde global.config
                config = self.env["global.config"].search([], limit=1)
                if config and config.email_reporte_consolidado:
                    try:
                        emails = [
                            e.strip()
                            for e in config.email_reporte_consolidado.split(",")
                            if e.strip()
                        ]
                        # Convertir a zona horaria de Ciudad de México
                        utc_now = datetime.now(pytz.UTC)
                        mexico_tz = pytz.timezone("America/Mexico_City")
                        mexico_time = utc_now.astimezone(mexico_tz)

                        timestamp = mexico_time.strftime("%d/%m/%Y %H:%M")
                        timestamp_full = mexico_time.strftime(
                            "%d de %B del %Y a las %H:%M"
                        )
                        subject = f"✓ Reporte Consolidado Generado - {timestamp}"

                        # Preparar lista de precios para el correo
                        if len(pricelists) <= 5:
                            # Si son 5 o menos, mostrar todas
                            pricelist_names_html = "<br>".join(
                                [f"• {pl.name}" for pl in pricelists]
                            )
                        else:
                            # Si son más de 5, mostrar las primeras 5 y agregar "y X más"
                            first_five = "<br>".join(
                                [f"• {pl.name}" for pl in pricelists[:5]]
                            )
                            pricelist_names_html = (
                                f"{first_five}<br>• ... y {len(pricelists) - 5} más"
                            )

                        # Preparar estadísticas para el correo
                        error_info = ""
                        if error_count > 0:
                            error_info = f"""
                            <tr>
                                <td style="padding: 12px; border-bottom: 1px solid #e0e0e0; color: #666;">Productos con errores</td>
                                <td style="padding: 12px; border-bottom: 1px solid #e0e0e0; text-align: right; font-weight: 600; color: #ff9800;">{len(products_with_errors)}</td>
                            </tr>
                            """

                        # Info adicional de modo de actualización
                        mode_info = ""
                        if prices_skipped_positive > 0:
                            mode_info = f"""
                            <tr>
                                <td style="padding: 12px; border-bottom: 1px solid #e0e0e0; color: #666;">Precios > 0 omitidos (modo)</td>
                                <td style="padding: 12px; border-bottom: 1px solid #e0e0e0; text-align: right; font-weight: 600; color: #9e9e9e;">{prices_skipped_positive:,}</td>
                            </tr>
                            """

                        body = f"""
                        <!DOCTYPE html>
                        <html>
                        <head>
                            <meta charset="UTF-8">
                            <meta name="viewport" content="width=device-width, initial-scale=1.0">
                        </head>
                        <body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background-color: #f5f5f5;">
                            <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f5f5f5; padding: 40px 20px;">
                                <tr>
                                    <td align="center">
                                        <!-- Contenedor principal -->
                                        <table width="600" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); overflow: hidden;">
                                            
                                            <!-- Header -->
                                            <tr>
                                                <td style="background-color: #f9f9f9 ; padding: 30px 40px; text-align: center;">
                                                    <h1 style="margin: 0; color: #333333; font-size: 24px; font-weight: 600; letter-spacing: -0.5px;">
                                                        ✓ Reporte Consolidado Generado
                                                    </h1>
                                                    <p style="margin: 8px 0 0 0; color: rgba(51,51,51,0.9); font-size: 14px;">
                                                        {timestamp_full}
                                                    </p>
                                                </td>
                                            </tr>
                                            
                                            <!-- Mensaje principal -->
                                            <tr>
                                                <td style="padding: 40px 40px 30px 40px;">
                                                    <p style="margin: 0 0 20px 0; color: #333; font-size: 16px; line-height: 1.6;">
                                                        El reporte consolidado de <strong>Stock y Listas de Precios</strong> ha sido procesado exitosamente.
                                                    </p>
                                                </td>
                                            </tr>
                                            
                                            <!-- Estadísticas -->
                                            <tr>
                                                <td style="padding: 0 40px 40px 40px;">
                                                    <table width="100%" cellpadding="0" cellspacing="0" style="border: 1px solid #e0e0e0; border-radius: 6px; overflow: hidden;">
                                                        <tr>
                                                            <td style="padding: 12px; border-bottom: 1px solid #e0e0e0; color: #666;">Registros generados</td>
                                                            <td style="padding: 12px; border-bottom: 1px solid #e0e0e0; text-align: right; font-weight: 600; color: #667eea;">{len(data_to_create):,}</td>
                                                        </tr>
                                                        <tr>
                                                            <td style="padding: 12px; border-bottom: 1px solid #e0e0e0; color: #666;">Productos procesados</td>
                                                            <td style="padding: 12px; border-bottom: 1px solid #e0e0e0; text-align: right; font-weight: 600; color: #333;">{total_products:,}</td>
                                                        </tr>
                                                        <tr>
                                                            <td style="padding: 12px; border-bottom: 1px solid #e0e0e0; color: #666;">Precios actualizados</td>
                                                            <td style="padding: 12px; border-bottom: 1px solid #e0e0e0; text-align: right; font-weight: 600; color: #4caf50;">{prices_updated:,}</td>
                                                        </tr>
                                                        <tr>
                                                            <td style="padding: 12px; border-bottom: 1px solid #e0e0e0; color: #666;">Precios sin cambios</td>
                                                            <td style="padding: 12px; border-bottom: 1px solid #e0e0e0; text-align: right; font-weight: 600; color: #2196f3;">{prices_unchanged:,}</td>
                                                        </tr>
                                                        <tr>
                                                            <td style="padding: 12px; border-bottom: 1px solid #e0e0e0; color: #666;">Productos omitidos</td>
                                                            <td style="padding: 12px; border-bottom: 1px solid #e0e0e0; text-align: right; font-weight: 600; color: #9e9e9e;">{prices_skipped:,}</td>
                                                        </tr>
                                                        {mode_info}
                                                        <tr>
                                                            <td style="padding: 12px; border-bottom: 1px solid #e0e0e0; color: #666; vertical-align: top;">Listas procesadas</td>
                                                            <td style="padding: 12px; border-bottom: 1px solid #e0e0e0; text-align: right; font-weight: 500; color: #333; font-size: 13px; line-height: 1.6;">
                                                                {pricelist_names_html}
                                                            </td>
                                                        </tr>
                                                        {error_info}
                                                        <tr>
                                                            <td style="padding: 12px; color: #666;">Estado</td>
                                                            <td style="padding: 12px; text-align: right;">
                                                                <span style="background-color: #4caf50; color: white; padding: 4px 12px; border-radius: 12px; font-size: 13px; font-weight: 500;">
                                                                    Completado
                                                                </span>
                                                            </td>
                                                        </tr>
                                                    </table>
                                                </td>
                                            </tr>
                                            
                                            <!-- Footer -->
                                            <tr>
                                                <td style="background-color: #f9f9f9; padding: 30px 40px; text-align: center; border-top: 1px solid #e0e0e0;">
                                                    <p style="margin: 0; color: #999; font-size: 13px; line-height: 1.6;">
                                                        Este es un mensaje automático generado por el sistema.<br>
                                                        Reporte: <strong>stock.pricelist.report</strong>
                                                    </p>
                                                </td>
                                            </tr>
                                            
                                        </table>
                                    </td>
                                </tr>
                            </table>
                        </body>
                        </html>
                        """

                        self.env["mail.mail"].create(
                            {
                                "subject": subject,
                                "body_html": body,
                                "email_to": ",".join(emails),
                            }
                        ).send()
                        _logger.info(
                            f"📧 Correo enviado a: {', '.join(emails[:3])}{'...' if len(emails) > 3 else ''}"
                        )
                    except Exception as e:
                        _logger.error(
                            f"Error al enviar correo de reporte consolidado: {str(e)}"
                        )
                else:
                    _logger.warning(
                        "No se encontró email_reporte_consolidado en global.config"
                    )

                # Mostrar notificación de éxito
                # Construir mensaje claro según lo que pasó
                if (
                    update_mode == "zero_or_negative"
                    and prices_updated == 0
                    and prices_skipped_positive > 0
                ):
                    # Caso especial: modo zero_or_negative pero todos tienen precios > 0
                    message = f"✅ Proceso completado sin cambios."
                    message += f"\n\n📊 Se revisaron {total_products} productos (de {total_products_initial} totales)"
                    message += f"\n✓ Todos ya tienen precios configurados (> 0)"
                    message += (
                        f"\n\n💡 No se requieren actualizaciones en modo 'solo ≤ 0'"
                    )
                elif prices_updated > 0:
                    # Hubo actualizaciones
                    message = f"✅ Reporte actualizado exitosamente"
                    if update_mode == "zero_or_negative":
                        message += f"\n\n📊 Productos revisados: {total_products} de {total_products_initial}"
                    else:
                        message += f"\n\n📊 Productos procesados: {total_products}"

                    message += f"\n\n💲 Actualización de precios:"
                    message += f"\n   • {prices_updated} actualizados"
                    if prices_unchanged > 0:
                        message += f"\n   • {prices_unchanged} sin cambios"
                    if prices_skipped > 0:
                        message += f"\n   • {prices_skipped} sin precio previo"
                else:
                    # No hubo actualizaciones pero puede haber otras razones
                    message = f"✅ Proceso completado"
                    if update_mode == "zero_or_negative":
                        message += f"\n\n📊 Productos revisados: {total_products} de {total_products_initial}"
                    else:
                        message += f"\n\n� Productos procesados: {total_products}"

                    if prices_unchanged > 0:
                        message += f"\n\n� Todos los precios ({prices_unchanged}) ya están actualizados"
                    elif prices_skipped > 0:
                        message += f"\n\n� {prices_skipped} productos sin precio previo en las listas"

                # Agregar advertencias si hay
                if error_count > 0:
                    message += f"\n\n⚠️ {len(products_with_errors)} productos con errores (ver logs)"
                if prices_failed > 0:
                    message += f"\n⚠️ {prices_failed} precios fallaron al actualizar"

                return {
                    "type": "ir.actions.client",
                    "tag": "display_notification",
                    "params": {
                        "title": "Reporte Recargado",
                        "message": message,
                        "type": "warning" if error_count > 0 else "success",
                        "sticky": error_count > 0,
                        "next": {"type": "ir.actions.act_window_close"},
                    },
                }
            else:
                if update_mode == "zero_or_negative" and total_products_initial > 0:
                    # Caso especial: hay productos pero ninguno con precio <= 0
                    _logger.info(
                        f"✅ Todos los productos ({total_products_initial}) ya tienen precios > 0. No se requiere actualización."
                    )
                    return {
                        "type": "ir.actions.client",
                        "tag": "display_notification",
                        "params": {
                            "title": "Sin cambios necesarios",
                            "message": f"Todos los productos ({total_products_initial}) ya tienen precios configurados (> 0).\n✅ No se requiere actualización en modo 'solo ≤ 0'.",
                            "type": "info",
                            "sticky": False,
                        },
                    }
                else:
                    _logger.warning(
                        "No se encontraron registros válidos en stock.weighted para cargar"
                    )
                    return {
                        "type": "ir.actions.client",
                        "tag": "display_notification",
                        "params": {
                            "title": "Advertencia",
                            "message": "No se encontraron datos para cargar en stock.weighted.",
                            "type": "warning",
                            "sticky": False,
                        },
                    }

        except Exception as e:
            _logger.error(f"Error crítico al recargar el reporte: {str(e)}")

            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Error",
                    "message": f"Error al recargar el reporte: {str(e)}",
                    "type": "danger",
                    "sticky": True,
                },
            }

    @api.model
    def init(self):
        """Cargar datos inicialmente al instalar/actualizar el módulo"""
        _logger.info("Inicializando datos de stock.pricelist.report...")
        # self.reload_report()
