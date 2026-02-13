# -*- coding: utf-8 -*-
from odoo import models, fields

class LlaveroPasswordWizard(models.TransientModel):
    _name = 'llavero.password.wizard'
    _description = 'Wizard para copiar la contraseña desencriptada'

    password_visible = fields.Char(string="Contraseña", readonly=True)
