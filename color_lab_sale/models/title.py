from odoo import models, fields, api


class SalesTitleConf(models.Model):
    _name = 'sales.title.conf'
    _description = 'Sales Title Conf'
    _inherit = ['mail.thread', 'mail.activity.mixin']


    name = fields.Char('Title Name', tracking=True, required=True)