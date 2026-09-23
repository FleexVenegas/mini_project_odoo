import re

import fitz


class AdventaExtractor:

    def extract(self, pdf_content):
        """
        Punto de entrada principal.

        Recibe:
            pdf_content: bytes del PDF

        Devuelve:
            {
                'source_format': 'adventa',
                'lines': [...],
                'totals': {...},
            }
        """

        text = self._extract_text(pdf_content)

        if not text.strip():
            raise ValueError(
                'No se pudo extraer texto del PDF.'
            )

        text = self._clean_document(text)

        lines = self._extract_products(text)

        totals = self._extract_totals(
            text,
            lines,
        )

        return {
            'source_format': 'adventa',
            'lines': lines,
            'totals': totals,
        }

    # =========================================================
    # PDF
    # =========================================================

    # def _extract_text(self, pdf_content):
    #     document = fitz.open(
    #         stream=pdf_content,
    #         filetype='pdf',
    #     )

    #     pages = []

    #     try:
    #         for page in document:
    #             pages.append(
    #                 page.get_text()
    #             )
    #     finally:
    #         document.close()

    #     return '\n'.join(pages)

    def _extract_text(self, pdf_content):
        document = fitz.open(
            stream=pdf_content,
            filetype='pdf',
        )

        pages = []

        try:
            for page_number, page in enumerate(document, start=1):

                page_text = page.get_text()

                print(
                    f'\n========== PÁGINA {page_number} =========='
                )

                print(page_text)

                print(
                    f'========== FIN PÁGINA {page_number} ==========\n'
                )

                pages.append(page_text)

        finally:
            document.close()

        return '\n'.join(pages)

    # =========================================================
    # LIMPIEZA
    # =========================================================

    def _clean_document(self, text):
        """
        Limpia encabezados y pies de página repetidos.
        """

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

            if self._is_page_footer(normalized):
                continue

            cleaned.append(line)

        return '\n'.join(cleaned)

    def _normalize_text(self, text):
        """
        Normaliza espacios y mayúsculas para
        facilitar las comparaciones.
        """

        text = ' '.join(
            text.split()
        )

        return text.lower().strip()

    # =========================================================
    # HEADERS
    # =========================================================

    def _is_header(self, line):
        headers = {
            'cantidad / quantity',
            'um / um',
            'sku adventa / sku adventa',
            'descripción / description',
            'descripcion / description',
            "sku proveedor / supplier's sku",
            'precio unitario / unit price',
            'importe / amount',
        }

        return line in headers

    # =========================================================
    # FOOTERS
    # =========================================================

    def _is_page_footer(self, line):
        """
        Detecta textos como:

            Página 1 de 9
            Página 2 de 9
            Page 1 of 9
        """

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

        pattern = re.compile(
            r'(?P<quantity>[\d,]+(?:\.\d+)?)\s+'
            r'(?P<uom>[A-Za-zÁÉÍÓÚáéíóú]+)\s+'
            r'(?P<adventa_sku>\d+)\s+'
        )

        matches = list(
            pattern.finditer(text)
        )

        products = []

        for index, match in enumerate(matches):

            start = match.end()

            if index + 1 < len(matches):
                end = matches[index + 1].start()
            else:
                end = len(text)

            block = text[start:end].strip()

            line_data = self._extract_line_data(
                block
            )

            if not line_data:
                continue

            products.append({
                'quantity': self._to_float(
                    match.group('quantity')
                ),
                'uom': match.group('uom'),
                'adventa_sku': match.group(
                    'adventa_sku'
                ),
                **line_data,
            })

        return products

    # =========================================================
    # PRODUCT DATA
    # =========================================================

    def _extract_line_data(self, block):

        parts = [
            part.strip()
            for part in block.splitlines()
            if part.strip()
        ]

        if not parts:
            return None

        supplier_index = None

        for index, part in enumerate(parts):

            if (
                part.isdigit()
                and len(part) >= 3
            ):
                supplier_index = index

        if supplier_index is None:
            return None

        supplier_sku = parts[
            supplier_index
        ]

        description_parts = parts[
            :supplier_index
        ]

        description = ' '.join(
            description_parts
        )

        remaining = parts[
            supplier_index + 1:
        ]

        money_pattern = re.compile(
            r'^\d{1,3}(?:,\d{3})*(?:\.\d{2})$'
        )

        money_values = [
            value
            for value in remaining
            if money_pattern.match(value)
        ]

        if len(money_values) < 2:
            return None

        unit_price = self._to_float(
            money_values[0]
        )

        amount = self._to_float(
            money_values[1]
        )

        return {
            'description': description,
            'supplier_sku': supplier_sku,
            'unit_price': unit_price,
            'amount': amount,
        }

    # =========================================================
    # TOTALS
    # =========================================================

    def _extract_totals(self, text, products):

        money_pattern = re.compile(
            r'(?<!\d)'
            r'\d{1,3}(?:,\d{3})*(?:\.\d{2})'
            r'(?!\d)'
        )

        values = [
            self._to_float(value)
            for value in money_pattern.findall(text)
        ]

        calculated_subtotal = round(
            sum(
                line['amount']
                for line in products
            ),
            2,
        )

        subtotal_index = None

        for index, value in enumerate(values):

            if abs(
                value - calculated_subtotal
            ) < 0.01:

                subtotal_index = index
                break

        if subtotal_index is None:

            return {
                'subtotal': calculated_subtotal,
                'discount': 0.0,
                'other': 0.0,
                'tax': 0.0,
                'total': 0.0,
            }

        remaining = values[
            subtotal_index + 1:
        ]

        discount = (
            remaining[0]
            if len(remaining) >= 1
            else 0.0
        )

        other = (
            remaining[1]
            if len(remaining) >= 2
            else 0.0
        )

        tax = (
            remaining[2]
            if len(remaining) >= 3
            else 0.0
        )

        total = (
            remaining[3]
            if len(remaining) >= 4
            else 0.0
        )

        return {
            'subtotal': calculated_subtotal,
            'discount': discount,
            'other': other,
            'tax': tax,
            'total': total,
        }

    # =========================================================
    # HELPERS
    # =========================================================

    def _to_float(self, value):

        if value is None:
            return 0.0

        value = str(value).strip()

        value = value.replace(
            ',',
            '',
        )

        try:
            return float(value)

        except (TypeError, ValueError):
            return 0.0