# -*- coding: utf-8 -*-

from odoo import models, fields


class MailActivityType(models.Model):
    _inherit = "mail.activity.type"

    category = fields.Selection(selection_add=[('approval', 'Approval')])
