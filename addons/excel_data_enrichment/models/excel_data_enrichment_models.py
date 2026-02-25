import base64
import csv
from html import escape
from io import BytesIO
from zipfile import ZipFile
import xml.etree.ElementTree as ET

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ExcelDataEnrichment(models.Model):
    _name = "excel.data.enrichment"
    _description = "Modelo generado automáticamente"

    name = fields.Char(
        string="Process name",
        required=True,
        default=lambda self: "New Excel process",
    )

    excel_file = fields.Binary(
        string="Excel file",
        required=True,
    )

    excel_filename = fields.Char(
        string="Nombre del archivo",
    )

    process_type = fields.Selection(
        selection=[
            ("price_assignment", "Asignar precios desde Odoo"),
        ],
        string="Tipo de proceso",
        required=False,
        default="price_assignment",
    )

    apply_pricelist_price = fields.Boolean(
        string="Agregar precio desde una lista",
        default=True,
    )

    add_price_column = fields.Boolean(
        string="Agregar nueva columna de precio",
        default=True,
    )

    multiply_price = fields.Boolean(
        string="Multiplicar precio",
        default=False,
    )

    multiplier_column = fields.Char(
        string="Columna para multiplicar",
        help="Nombre exacto de la columna del Excel que se usará como factor.",
    )

    multiplier_value = fields.Float(
        string="Multiplicador fijo",
        default=1.0,
        help="Se aplica además del multiplicador por columna (si está definido).",
    )

    pricelist_id = fields.Many2one(
        comodel_name="product.pricelist", string="Lista de precios", required=False
    )

    detected_columns = fields.Text(
        string="Columnas detectadas",
        readonly=True,
    )

    preview_html = fields.Html(
        string="Vista previa",
        sanitize=False,
        readonly=True,
    )

    state = fields.Selection(
        selection=[
            ("draft", "Borrador"),
            ("done", "Procesado"),
        ],
        default="draft",
        string="Estado",
    )

    @api.onchange("excel_file", "excel_filename")
    def _onchange_excel_file_preview(self):
        for record in self:
            preview_vals = record._build_preview_vals()
            record.detected_columns = preview_vals["detected_columns"]
            record.preview_html = preview_vals["preview_html"]

    @api.constrains("apply_pricelist_price", "pricelist_id")
    def _check_pricelist_required(self):
        for record in self:
            if record.apply_pricelist_price and not record.pricelist_id:
                raise ValidationError(
                    "Debes seleccionar una lista de precios cuando la opción 'Agregar precio desde una lista' está activa."
                )

    @api.constrains("apply_pricelist_price", "multiply_price", "multiplier_column")
    def _check_multiplier_column_required(self):
        for record in self:
            if (
                record.apply_pricelist_price
                and record.multiply_price
                and not record.multiplier_column
            ):
                raise ValidationError(
                    "Debes indicar la columna a usar para multiplicar el precio."
                )

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._refresh_preview_persisted()
        return records

    def write(self, vals):
        result = super().write(vals)
        if not self.env.context.get("skip_preview_refresh") and (
            "excel_file" in vals or "excel_filename" in vals
        ):
            self._refresh_preview_persisted()
        return result

    def action_refresh_preview(self):
        self._refresh_preview_persisted()
        return True

    def _refresh_preview_persisted(self):
        for record in self:
            preview_vals = record._build_preview_vals()
            super(
                ExcelDataEnrichment,
                record.with_context(skip_preview_refresh=True),
            ).write(preview_vals)

    def _build_preview_vals(self):
        self.ensure_one()

        if not self.excel_file:
            return {
                "detected_columns": False,
                "preview_html": False,
            }

        try:
            raw_content = base64.b64decode(self.excel_file)
            rows = self._extract_preview_rows(raw_content, max_rows=8, max_columns=8)
            if not rows:
                return {
                    "detected_columns": "No se encontraron filas en el archivo.",
                    "preview_html": "<p>No hay datos para previsualizar.</p>",
                }

            header_row = rows[0] or []
            header_cells = [
                str(cell).strip() if cell is not None else "" for cell in header_row
            ]
            non_empty_headers = [col for col in header_cells if col]

            detected_columns = (
                "Columnas detectadas: " + ", ".join(non_empty_headers)
                if non_empty_headers
                else "No se detectaron nombres de columnas en la primera fila."
            )

            preview_rows_html = []
            max_columns = 8
            for row in rows:
                cells = list(row or [])[:max_columns]
                if len(cells) < max_columns:
                    cells.extend([""] * (max_columns - len(cells)))
                rendered_cells = "".join(
                    f"<td>{escape('' if cell is None else str(cell))}</td>"
                    for cell in cells
                )
                preview_rows_html.append(f"<tr>{rendered_cells}</tr>")

            preview_html = (
                "<div><p>Vista previa de las primeras 8 filas y 8 columnas.</p>"
                "<table class='table table-sm table-bordered'>"
                f"<tbody>{''.join(preview_rows_html)}</tbody></table></div>"
            )

            return {
                "detected_columns": detected_columns,
                "preview_html": preview_html,
            }
        except Exception as error:
            return {
                "detected_columns": "No fue posible leer el archivo.",
                "preview_html": (
                    "<p>No se pudo generar la vista previa. "
                    f"Detalle: {escape(str(error))}</p>"
                ),
            }

    def _extract_preview_rows(self, raw_content, max_rows=8, max_columns=8):
        filename = (self.excel_filename or "").lower()
        if filename.endswith(".csv"):
            return self._extract_csv_rows(
                raw_content, max_rows=max_rows, max_columns=max_columns
            )
        return self._extract_xlsx_rows(
            raw_content, max_rows=max_rows, max_columns=max_columns
        )

    def _extract_csv_rows(self, raw_content, max_rows=8, max_columns=8):
        decoded = raw_content.decode("utf-8", errors="replace")
        reader = csv.reader(decoded.splitlines())
        result = []

        for row in reader:
            if len(result) >= max_rows:
                break
            clean_row = [
                "" if cell is None else str(cell) for cell in row[:max_columns]
            ]
            if len(clean_row) < max_columns:
                clean_row.extend([""] * (max_columns - len(clean_row)))
            result.append(clean_row)

        return result

    def _extract_xlsx_rows(self, raw_content, max_rows=8, max_columns=8):
        with ZipFile(BytesIO(raw_content), "r") as zip_file:
            shared_strings = self._extract_shared_strings(zip_file)
            sheet_path = self._get_first_sheet_path(zip_file)
            if not sheet_path:
                return []

            sheet_xml = zip_file.read(sheet_path)
            root = ET.fromstring(sheet_xml)

            namespaces = {
                "main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
            }
            rows = []

            for row_element in root.findall(".//main:sheetData/main:row", namespaces):
                if len(rows) >= max_rows:
                    break

                current_row = [""] * max_columns
                for cell in row_element.findall("main:c", namespaces):
                    cell_ref = cell.get("r", "")
                    column_index = self._column_index_from_ref(cell_ref)
                    if column_index is None or column_index >= max_columns:
                        continue

                    cell_type = cell.get("t")
                    value = ""

                    if cell_type == "inlineStr":
                        inline_text = cell.find("main:is/main:t", namespaces)
                        value = (
                            inline_text.text
                            if inline_text is not None and inline_text.text
                            else ""
                        )
                    else:
                        value_node = cell.find("main:v", namespaces)
                        raw_value = (
                            value_node.text
                            if value_node is not None and value_node.text
                            else ""
                        )
                        if cell_type == "s" and raw_value.isdigit():
                            shared_index = int(raw_value)
                            if 0 <= shared_index < len(shared_strings):
                                value = shared_strings[shared_index]
                            else:
                                value = raw_value
                        else:
                            value = raw_value

                    current_row[column_index] = "" if value is None else str(value)

                rows.append(current_row)

            return rows

    def _extract_shared_strings(self, zip_file):
        shared_strings_path = "xl/sharedStrings.xml"
        if shared_strings_path not in zip_file.namelist():
            return []

        content = zip_file.read(shared_strings_path)
        root = ET.fromstring(content)
        namespace = {
            "main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
        }
        values = []

        for si_element in root.findall("main:si", namespace):
            text_parts = [
                text_node.text or ""
                for text_node in si_element.findall(".//main:t", namespace)
            ]
            values.append("".join(text_parts))

        return values

    def _get_first_sheet_path(self, zip_file):
        sheet_candidates = sorted(
            path
            for path in zip_file.namelist()
            if path.startswith("xl/worksheets/sheet") and path.endswith(".xml")
        )
        return sheet_candidates[0] if sheet_candidates else None

    def _column_index_from_ref(self, cell_ref):
        letters = "".join(char for char in cell_ref if char.isalpha())
        if not letters:
            return None

        index = 0
        for char in letters.upper():
            index = index * 26 + (ord(char) - ord("A") + 1)
        return index - 1
