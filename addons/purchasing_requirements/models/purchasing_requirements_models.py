from odoo import models, fields, api


class PurchasingRequirements(models.Model):
    _name = "purchasing.requirements"
    _description = "Purchase Requisition"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _rec_name = "name"

    name = fields.Char(
        string="Reference",
        required=True,
        copy=False,
        readonly=True,
        default="New",
        tracking=False,
    )
    
    requested_by = fields.Many2one(
        "res.users",
        string="Requested By",
        required=True,
        help="User who requested the purchase requisition",
        tracking=True,
    )
    department_id = fields.Many2one(
        "hr.department",
        string="Department",
        help="Department associated with the purchase requisition",
        tracking=True,
    )
    requirement_date = fields.Datetime(
        string="Requisition Date",
        default=fields.Datetime.now,
        help="Date when the purchase requisition was created",
        tracking=True,
    )

    # --- One2many relation for multiple products ---
    line_ids = fields.One2many(
        "purchasing.requirements.line",
        "requirement_id",
        string="Products",
        help="List of products requested in this requisition",
        tracking=False,
    )

    # --- Computed fields for totals ---
    total_cost = fields.Float(
        string="Estimated Total",
        compute="_compute_total_cost",
        store=True,
        help="Total sum of all products",
        tracking=False,
    )

    # --- Campos antiguos (mantener para compatibilidad o migración) ---
    product_name = fields.Char(
        string="Product Name (Deprecated)",
        help="Name of the product to be purchased",
    )

    quantity = fields.Float(
        string="Quantity (Deprecated)",
        help="Quantity of the product to be purchased",
    )

    uom_id = fields.Many2one(
        "uom.uom",
        string="Unit of Measure (Deprecated)",
        help="Unit of measure for the product quantity",
    )

    cost = fields.Float(
        string="Cost (Deprecated)",
        help="Estimated cost of the product",
    )

    @api.depends("line_ids.subtotal")
    def _compute_total_cost(self):
        for rec in self:
            rec.total_cost = sum(rec.line_ids.mapped("subtotal"))

    @api.model_create_multi
    def create(self, vals_list):
        """Genera el folio consecutivo al crear el registro"""
        for vals in vals_list:
            if vals.get("name", "Nuevo") == "Nuevo":
                # Genera el folio consecutivo usando secuencia
                vals["name"] = (
                    self.env["ir.sequence"].next_by_code("purchasing.requirements")
                    or "RC0001"
                )
        return super(PurchasingRequirements, self).create(vals_list)

    def write(self, vals):
        """Sobrescribe write para disparar actualización del preview al guardar"""
        result = super(PurchasingRequirements, self).write(vals)
        # El tracking de Odoo ya se encarga de notificar cambios
        # El frontend escuchará los cambios a través del modelo
        return result

    # --- Nuevo campo calculado que devuelve la URL del reporte HTML/PDF ---
    report_url = fields.Char(
        string="Report URL", compute="_compute_report_url", readonly=True
    )

    def _compute_report_url(self):
        for rec in self:
            if rec.id:
                # URL HTML (útil para ver la plantilla en HTML)
                html_url = (
                    "/report/html/purchasing_requirements.report_purchasing_requirements_template/%s"
                    % rec.id
                )
                # URL PDF (útil para imprimir / descargar)
                pdf_url = (
                    "/report/pdf/purchasing_requirements.report_purchasing_requirements_template/%s"
                    % rec.id
                )
                rec.report_url = html_url  # por defecto ponemos la vista HTML
            else:
                rec.report_url = False

    # --- Acción para abrir la vista en una nueva pestaña (HTML) ---
    def action_preview_report(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_url",
            "url": self.report_url,
            "target": "new",
        }

    # (Opcional) acción para abrir el PDF directamente
    def action_preview_report_pdf(self):
        self.ensure_one()
        pdf = (
            "/report/pdf/purchasing_requirements.report_purchasing_requirements_template/%s"
            % self.id
        )
        return {
            "type": "ir.actions.act_url",
            "url": pdf,
            "target": "new",
        }

    def _get_report_values(self, docids, data=None):
        docs = self.sudo().browse(docids)

        # Forzar contexto de compañía del registro
        company = docs.company_id or self.env.company

        return {
            "doc_ids": docs.ids,
            "doc_model": self._name,
            "docs": docs,
            "company": company,
            "company_id": company.id,
        }
