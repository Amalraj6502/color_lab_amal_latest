# -*- coding: utf-8 -*-

from odoo import models, fields


class MiniBook(models.Model):
    _name = 'mini.book.conf'
    _description = 'Mini Book Configuration'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Name')
    height = fields.Float('Height(cm)')
    weight = fields.Float('Weight(cm)')
    length = fields.Float('Length(cm)')
    width = fields.Float('Width(cm)')
    amount = fields.Monetary('Amount')
    remarks = fields.Text('Remarks')
    currency_id = fields.Many2one(
        comodel_name='res.currency',
        string="Currency",
        readonly=False,
        required=True,
        default=lambda self: self.env.company.currency_id,
    )