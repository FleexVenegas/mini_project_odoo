# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class ConfirmationWizard(models.TransientModel):
    """Wizard genérico de confirmación que puede ejecutar cualquier método"""

    _name = "confirmation.wizard"
    _description = "Wizard Genérico de Confirmación"

    title = fields.Char(string="Título", default="Confirmación")

    description = fields.Html(
        string="Descripción", default="¿Está seguro de continuar con esta acción?"
    )

    description_text = fields.Char(
        string="Descripción Texto",
        help="Texto plano que se convertirá automáticamente a HTML",
    )

    model_name = fields.Char(string="Modelo", help="Nombre técnico del modelo")

    method_name = fields.Char(string="Método", help="Nombre del método a ejecutar")

    record_id = fields.Integer(
        string="ID del Registro",
        help="ID del registro sobre el cual ejecutar el método (opcional)",
    )

    record_ids = fields.Char(
        string="IDs de Registros",
        help="IDs de múltiples registros separados por comas (opcional)",
    )

    context_data = fields.Text(
        string="Contexto adicional", help="Datos de contexto en formato JSON (opcional)"
    )

    @staticmethod
    def _format_description(text):
        """
        Convierte texto plano a HTML con formato básico
        Detecta saltos de línea y los convierte en <br/>
        """
        if not text:
            return "¿Está seguro de continuar con esta acción?"

        # Si ya es HTML (contiene tags), devolverlo tal cual
        if "<" in text and ">" in text:
            return text

        # Convertir saltos de línea a <br/>
        text = text.replace("\n", "<br/>")

        return text

    @api.model
    def create_confirmation(
        self,
        model_name,
        method_name,
        title=None,
        description=None,
        record_id=None,
        record_ids=None,
        context_data=None,
        dialog_size="medium",
    ):
        """
        Método helper para crear fácilmente un wizard de confirmación

        :param model_name: Nombre del modelo (ej: 'odoo.wp.sync')
        :param method_name: Nombre del método a ejecutar (ej: 'action_sync')
        :param title: Título del wizard (opcional)
        :param description: Texto plano que se convertirá a HTML (opcional)
        :param record_id: ID del registro específico (opcional, para un solo registro)
        :param record_ids: Lista de IDs de registros (opcional, para múltiples registros)
        :param context_data: Datos adicionales de contexto (opcional)
        :param dialog_size: Tamaño del wizard: 'small', 'medium', 'large', 'extra-large' (default: 'medium')
        :return: Action para abrir el wizard
        """
        # Convertir texto plano a HTML con formato
        description_html = self._format_description(
            description or "¿Está seguro de continuar con esta acción?"
        )

        vals = {
            "title": title or "Confirmación",
            "description": description_html,
            "model_name": model_name,
            "method_name": method_name,
            "context_data": context_data,
        }

        # Agregar record_id o record_ids según corresponda
        if record_ids:
            # Convertir lista a string separado por comas
            if isinstance(record_ids, list):
                vals["record_ids"] = ",".join(map(str, record_ids))
            else:
                vals["record_ids"] = str(record_ids)
        elif record_id:
            vals["record_id"] = record_id

        wizard = self.create(vals)

        # Mapeo de tamaños
        size_classes = {
            "small": "modal-sm",  # ~300px
            "medium": "modal-md",  # ~500px (default)
            "large": "modal-lg",  # ~800px
            "extra-large": "modal-xl",  # ~1140px
        }

        return {
            "name": title or "Confirmación",
            "type": "ir.actions.act_window",
            "res_model": "confirmation.wizard",
            "view_mode": "form",
            "res_id": wizard.id,
            "target": "new",
            "context": {"dialog_size": size_classes.get(dialog_size, "modal-md")},
        }

    def action_confirm(self):
        """Ejecuta el método especificado cuando el usuario confirma"""
        self.ensure_one()

        if not self.model_name or not self.method_name:
            raise UserError(_("No se ha especificado el modelo o método a ejecutar."))

        try:
            # Obtener el modelo
            model = self.env[self.model_name]

            # Determinar si hay registros específicos
            if self.record_ids:
                # Múltiples registros
                ids = [
                    int(id_str)
                    for id_str in self.record_ids.split(",")
                    if id_str.strip()
                ]
                record = model.browse(ids)
                if not record:
                    raise UserError(_("Los registros especificados no existen."))
            elif self.record_id:
                # Un solo registro
                record = model.browse(self.record_id)
                if not record.exists():
                    raise UserError(_("El registro especificado no existe."))
            else:
                # Sin registro específico (método del modelo)
                record = model

            # Verificar que el método existe
            if not hasattr(record, self.method_name):
                raise UserError(
                    _('El método "%s" no existe en el modelo "%s".')
                    % (self.method_name, self.model_name)
                )

            # Preparar contexto adicional si existe
            context = dict(self.env.context)
            if self.context_data:
                import json

                try:
                    extra_context = json.loads(self.context_data)
                    context.update(extra_context)
                except:
                    pass

            # Ejecutar el método
            _logger.info(
                f"Ejecutando método {self.method_name} en modelo {self.model_name} con {len(record) if hasattr(record, '__len__') else 1} registro(s)..."
            )
            method = getattr(record, self.method_name)
            result = method()

            # Si el método retorna una acción, devolverla
            if isinstance(result, dict) and result.get("type"):
                return result

            # Si no, cerrar el wizard
            return {"type": "ir.actions.act_window_close"}

        except Exception as e:
            _logger.error(f"Error durante la ejecución: {str(e)}")
            raise UserError(_("Error durante la ejecución: %s") % str(e))

    def action_cancel(self):
        """Cancela el wizard sin hacer cambios"""
        return {"type": "ir.actions.act_window_close"}
