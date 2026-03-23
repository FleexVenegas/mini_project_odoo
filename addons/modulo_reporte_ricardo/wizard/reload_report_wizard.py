from odoo import models, fields, api


class ReloadReportWizard(models.TransientModel):
    _name = "reload.report.wizard"
    _description = "Asistente para Recargar Reporte Consolidado"

    pricelist_ids = fields.Many2many(
        "product.pricelist",
        string="Listas de Precios",
        help="Selecciona las listas de precios a procesar. Si no seleccionas ninguna, se procesarán todas.",
    )

    process_all = fields.Boolean(
        string="Procesar todas las listas",
        default=False,
        help="Marcar para procesar todas las listas de precios disponibles",
    )

    update_mode = fields.Selection(
        [
            ("all", "Actualizar todos los precios"),
            ("zero_or_negative", "Solo actualizar precios ≤ 0"),
        ],
        string="Modo de actualización",
        default="all",
        required=True,
        help="Selecciona qué precios actualizar:\n"
        "• Todos: Actualiza todos los productos (puede ser lento)\n"
        "• Solo ≤ 0: Solo actualiza productos sin precio o con precio negativo (más rápido)",
    )

    total_pricelists = fields.Integer(
        string="Total de listas disponibles",
        compute="_compute_total_pricelists",
        store=False,
    )

    estimated_records = fields.Integer(
        string="Registros estimados", compute="_compute_estimated_records", store=False
    )

    can_generate = fields.Boolean(
        string="Puede generar",
        compute="_compute_can_generate",
        store=False,
        help="Indica si se puede generar el reporte (requiere seleccionar al menos una opción)",
    )

    @api.depends("pricelist_ids", "process_all")
    def _compute_can_generate(self):
        """Determina si se puede generar el reporte"""
        for wizard in self:
            wizard.can_generate = wizard.process_all or bool(wizard.pricelist_ids)

    @api.depends("pricelist_ids", "process_all")
    def _compute_estimated_records(self):
        """Calcula los registros estimados a generar"""
        for wizard in self:
            total_products = self.env["stock.weighted"].search_count([])

            if wizard.process_all:
                total_pricelists = self.env["product.pricelist"].search_count([])
            else:
                total_pricelists = len(wizard.pricelist_ids)

            wizard.estimated_records = (
                total_products * total_pricelists if total_pricelists > 0 else 0
            )

    @api.depends("process_all")
    def _compute_total_pricelists(self):
        """Calcula el total de listas de precios disponibles"""
        for wizard in self:
            wizard.total_pricelists = self.env["product.pricelist"].search_count([])

    @api.onchange("process_all")
    def _onchange_process_all(self):
        """Limpia la selección cuando se marca procesar todas"""
        if self.process_all:
            self.pricelist_ids = [(5, 0, 0)]  # Limpia la selección

    @api.onchange("pricelist_ids")
    def _onchange_pricelist_ids(self):
        """Desmarca 'procesar todas' cuando se seleccionan listas específicas"""
        if self.pricelist_ids:
            self.process_all = False

    def action_reload_report(self):
        """Ejecuta la recarga del reporte con las listas seleccionadas"""
        self.ensure_one()

        # Determinar qué listas procesar
        if self.process_all:
            pricelist_ids = self.env["product.pricelist"].search([]).ids
        elif self.pricelist_ids:
            pricelist_ids = self.pricelist_ids.ids
        else:
            # Si no hay selección, procesar todas (comportamiento por defecto)
            pricelist_ids = self.env["product.pricelist"].search([]).ids

        # Llamar al método de recarga con las listas seleccionadas y el modo de actualización
        report_model = self.env["stock.pricelist.report"]
        return report_model.reload_report(
            pricelist_ids=pricelist_ids, update_mode=self.update_mode
        )
