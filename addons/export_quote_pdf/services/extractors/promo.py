import re

import fitz


class PromoExtractor:
    """
    Extractor para cotizaciones/formato Promo.

    Estructura esperada:

        CANTIDAD
        TIPO
        FECHA ENTREGA

        U.M.
        NO.PARTE
        UPC
        PRECIO UNITARIO
        IMPORTE

    El supplier_sku será:

        NO.PARTE
        o UPC si NO.PARTE no existe.
    """

    SOURCE_FORMAT = 'promo'

    def extract(self, pdf_content):
        text = self._extract_text(pdf_content)

        if not text.strip():
            raise ValueError(
                'No se pudo extraer texto del PDF.'
            )

        text = self._clean_document(text)

        lines = self._extract_products(text)

        if not lines:
            raise ValueError(
                'No se pudieron detectar productos '
                'en el PDF de Promo.'
            )

        totals = self._extract_totals(
            text,
            lines,
        )

        return {
            'source_format': self.SOURCE_FORMAT,
            'lines': lines,
            'totals': totals,
        }

    # =========================================================
    # PDF
    # =========================================================

    def _extract_text(self, pdf_content):
        document = fitz.open(
            stream=pdf_content,
            filetype='pdf',
        )

        pages = []

        try:
            for page in document:
                pages.append(
                    page.get_text()
                )
        finally:
            document.close()

        return '\n'.join(pages)

    # =========================================================
    # CLEAN
    # =========================================================

    def _clean_document(self, text):
        lines = text.splitlines()

        cleaned = []

        for line in lines:
            line = line.strip()

            if not line:
                continue

            normalized = self._normalize_text(
                line
            )

            if self._is_header(normalized):
                continue

            if self._is_footer(normalized):
                continue

            cleaned.append(line)

        return '\n'.join(cleaned)

    def _normalize_text(self, text):
        return ' '.join(
            text.split()
        ).lower().strip()

    # =========================================================
    # HEADERS
    # =========================================================

    def _is_header(self, line):
        headers = [
            'articulo',
            'cant.',
            'cant',
            'ed.',
            'fecha ent.',
            'umd',
            'um',
            'no.parte',
            'no. parte',
            'upc',
            'c.u.',
            'importe',
        ]

        return line in headers

    # =========================================================
    # FOOTERS
    # =========================================================

    def _is_footer(self, line):
        patterns = [
            r'^página\s+\d+\s+de\s+\d+$',
            r'^pagina\s+\d+\s+de\s+\d+$',
            r'^page\s+\d+\s+of\s+\d+$',
        ]

        return any(
            re.match(pattern, line)
            for pattern in patterns
        )

    # =========================================================
    # PRODUCTS
    # =========================================================

    def _extract_products(self, text):
        """
        Detecta los productos utilizando la línea
        que contiene:

            PZA SKU UPC PRECIO IMPORTE
        """

        lines = text.splitlines()

        products = []

        for index, line in enumerate(lines):

            parsed = self._parse_product_footer(
                line
            )

            if not parsed:
                continue

            quantity = self._find_quantity(
                lines,
                index,
            )

            if quantity is None:
                continue

            description = self._find_description(
                lines,
                index,
            )

            products.append({
                'quantity': quantity['quantity'],
                'uom': parsed['uom'],
                'supplier_sku': parsed[
                    'supplier_sku'
                ],
                'description': description,
                'unit_price': parsed[
                    'unit_price'
                ],
                'amount': parsed['amount'],
            })

        return products

    # =========================================================
    # PRODUCT FOOTER
    # =========================================================

    def _parse_product_footer(self, line):
        """
        Ejemplo:

        PZA 1252 8011003993826
        1,459.0000 4,377.0000
        """

        pattern = re.compile(
            r'^(?P<uom>[A-Za-z]+)\s+'
            r'(?P<part_number>\d+)?\s*'
            r'(?P<upc>\d+)?\s+'
            r'(?P<unit_price>\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s+'
            r'(?P<amount>\d{1,3}(?:,\d{3})*(?:\.\d+)?)$'
        )

        match = pattern.match(
            line.strip()
        )

        if not match:
            return None

        part_number = (
            match.group('part_number')
            or ''
        ).strip()

        upc = (
            match.group('upc')
            or ''
        ).strip()

        supplier_sku = (
            part_number
            if part_number
            else upc
        )

        if not supplier_sku:
            return None

        return {
            'uom': match.group('uom'),
            'part_number': part_number,
            'upc': upc,
            'supplier_sku': supplier_sku,
            'unit_price': self._to_float(
                match.group('unit_price')
            ),
            'amount': self._to_float(
                match.group('amount')
            ),
        }

    # =========================================================
    # QUANTITY
    # =========================================================

    def _find_quantity(self, lines, product_index):
        """
        Busca hacia arriba una línea como:

            3 N 17/08/2026

        """

        pattern = re.compile(
            r'^(?P<quantity>\d+(?:[.,]\d+)?)\s+'
            r'(?P<type>[A-Za-z]+)\s+'
            r'(?P<date>\d{2}/\d{2}/\d{4})'
        )

        # Buscamos únicamente dentro de las últimas
        # líneas anteriores al footer del producto.
        start = max(
            0,
            product_index - 10,
        )

        for index in range(
            product_index - 1,
            start - 1,
            -1,
        ):

            match = pattern.match(
                lines[index].strip()
            )

            if not match:
                continue

            return {
                'quantity': self._to_float(
                    match.group('quantity')
                ),
            }

        return None

    # =========================================================
    # DESCRIPTION
    # =========================================================

    def _find_description(self, lines, product_index):
        """
        Recupera la descripción ubicada antes
        de la cantidad del producto.

        Ignora:

            Detalle del producto
            CLAVE SAT
            notas y detalles técnicos
        """

        start = max(
            0,
            product_index - 30,
        )

        candidates = []

        for index in range(
            start,
            product_index,
        ):

            line = lines[index].strip()

            if not line:
                continue

            normalized = self._normalize_text(
                line
            )

            if self._is_description_noise(
                normalized
            ):
                continue

            if self._is_quantity_line(
                line
            ):
                candidates = []

            else:
                candidates.append(line)

        return self._build_description(
            candidates
        )

    def _is_description_noise(self, line):
        noise = [
            'detalle del producto:',
            'clave sat:',
        ]

        return any(
            line.startswith(value)
            for value in noise
        )

    def _is_quantity_line(self, line):
        pattern = re.compile(
            r'^\d+(?:[.,]\d+)?\s+[A-Za-z]+\s+'
            r'\d{2}/\d{2}/\d{4}'
        )

        return bool(
            pattern.match(line)
        )

    def _build_description(self, candidates):
        """
        De momento conserva únicamente las primeras
        líneas comerciales de la descripción.

        Evita incorporar:
            notas
            clave SAT
            detalles técnicos
        """

        result = []

        for line in candidates:

            normalized = self._normalize_text(
                line
            )

            if normalized.startswith(
                'detalle del producto'
            ):
                break

            if normalized.startswith(
                'clave sat'
            ):
                break

            result.append(line)

        return ' '.join(result).strip()

    # =========================================================
    # TOTALS
    # =========================================================

    def _extract_totals(self, text, products):
        """
        Primero calculamos el subtotal a partir
        de las líneas.

        Posteriormente podremos agregar la extracción
        específica de impuestos/totales cuando tengamos
        un PDF completo de Promo.
        """

        subtotal = round(
            sum(
                line['amount']
                for line in products
            ),
            2,
        )

        return {
            'subtotal': subtotal,
            'discount': 0.0,
            'other': 0.0,
            'tax': 0.0,
            'total': subtotal,
        }

    # =========================================================
    # HELPERS
    # =========================================================

    def _to_float(self, value):
        if value is None:
            return 0.0

        value = str(value).strip()
        value = value.replace(',', '')

        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0