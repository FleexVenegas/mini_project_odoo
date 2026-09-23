import base64

import fitz

from odoo import fields, models
from odoo.exceptions import UserError
from ..services.extractors.adventa import AdventaExtractor
from ..services.extractors.promo import PromoExtractor


class ExportQuotePdfWizard(models.TransientModel):
    _name = 'export.quote.pdf.wizard'
    _description = 'Import Sales Quotation from PDF'

    state = fields.Selection(
        selection=[
            ('upload', 'Subir PDF'),
            ('preview', 'Vista previa'),
        ],
        string='Estado',
        default='upload',
        required=True,
    )

    source_format = fields.Selection(
        selection=[
            ('adventa', 'Adventa'),
            ('promo', 'Promo'),
        ],
        string='Formato de cotización',
        required=True,
    )

    pdf_file = fields.Binary(
        string='PDF',
        required=True,
    )

    pdf_filename = fields.Char(
        string='Nombre del archivo',
    )

    # ---------------------------------------------------------
    # Datos extraídos
    # ---------------------------------------------------------

    extracted_data = fields.Json(
        string='Datos extraídos',
    )

    line_ids = fields.One2many(
        'export.quote.pdf.line',
        'wizard_id',
        string='Líneas',
    )

    subtotal = fields.Float(
        string='Subtotal',
        readonly=True,
    )

    discount = fields.Float(
        string='Descuento',
        readonly=True,
    )

    other = fields.Float(
        string='Otros',
        readonly=True,
    )

    tax = fields.Float(
        string='IVA',
        readonly=True,
    )

    total = fields.Float(
        string='Total',
        readonly=True,
    )

    # ---------------------------------------------------------
    # Procesar PDF
    # ---------------------------------------------------------

    def action_process_pdf(self):
        self.ensure_one()

        if not self.source_format:
            raise UserError(
                'Debe seleccionar el formato de la cotización.'
            )

        if not self.pdf_file:
            raise UserError(
                'Debe seleccionar un archivo PDF.'
            )

        pdf_content = base64.b64decode(
            self.pdf_file
        )

        try:
            document = fitz.open(
                stream=pdf_content,
                filetype='pdf',
            )
        except Exception as error:
            raise UserError(
                f'No fue posible abrir el PDF: {error}'
            )

        text = '\n'.join(
            page.get_text()
            for page in document
        )

        document.close()

        if not text.strip():
            raise UserError(
                'No se pudo extraer texto del PDF.'
            )

        if self.source_format == 'adventa':
            data = self._process_adventa(
                pdf_content
            )
        elif self.source_format == 'promo':
            data = self._process_promo(
                pdf_content
            )
        else:
            raise UserError(
                'Formato de cotización no soportado.'
            )

        self._load_extracted_data(data)

        self.state = 'preview'

        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }

    # ---------------------------------------------------------
    # Adventa
    # ---------------------------------------------------------

    def _process_adventa(self, pdf_content):
        extractor = AdventaExtractor()

        return extractor.extract(
            pdf_content
        )

    def _process_promo(self, pdf_content):
        extractor = PromoExtractor()
        return extractor.extract(
            pdf_content
        )

    # ---------------------------------------------------------
    # Cargar datos
    # ---------------------------------------------------------

    def _load_extracted_data(self, data):
        self.extracted_data = data

        # Eliminar líneas anteriores si se vuelve
        # a procesar el documento.
        self.line_ids.unlink()

        lines = data.get(
            'lines',
            []
        )

        line_values = []

        for line in lines:
            line_values.append({
                'wizard_id': self.id,
                'quantity': line.get(
                    'quantity',
                    0.0,
                ),
                'uom': line.get(
                    'uom'
                ),
                'adventa_sku': line.get(
                    'adventa_sku'
                ),
                'supplier_sku': line.get(
                    'supplier_sku'
                ),
                'description': line.get(
                    'description'
                ),
                'unit_price': line.get(
                    'unit_price',
                    0.0,
                ),
                'amount': line.get(
                    'amount',
                    0.0,
                ),
            })

        self.env[
            'export.quote.pdf.line'
        ].create(line_values)

        totals = data.get(
            'totals',
            {}
        )

        self.subtotal = totals.get(
            'subtotal',
            0.0,
        )

        self.discount = totals.get(
            'discount',
            0.0,
        )

        self.other = totals.get(
            'other',
            0.0,
        )

        self.tax = totals.get(
            'tax',
            0.0,
        )

        self.total = totals.get(
            'total',
            0.0,
        )

    def action_back(self):
        self.ensure_one()

        self.state = 'upload'

        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }