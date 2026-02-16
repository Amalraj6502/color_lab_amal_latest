import base64

from odoo import models, fields, api
from odoo.tools.misc import file_open


class ProductBrand(models.Model):
    _name = 'product.brand'
    _description = 'Brand'
    _inherit = ['mail.thread', 'mail.activity.mixin']


    name = fields.Char(string="Brand name", required=True)
    code = fields.Char("Code")
    remarks = fields.Text("Remarks")
    company_id = fields.Many2one('res.company', string="Company")
    image_1920 = fields.Image()
