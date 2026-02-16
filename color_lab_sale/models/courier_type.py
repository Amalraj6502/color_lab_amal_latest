from odoo import models, fields, api


class CourierTypeConf(models.Model):
    _name = 'courier.type.conf'
    _description = 'Courier Type Conf'
    _inherit = ['mail.thread', 'mail.activity.mixin']


    name = fields.Char('Courier Type Name', tracking=True, required=True)