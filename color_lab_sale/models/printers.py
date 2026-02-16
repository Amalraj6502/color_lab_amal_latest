from odoo import models, fields, api


class PrintConf(models.Model):
    _name = 'printer.conf'
    _description = 'Print Machine Configuration'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Printer Name', required=True)
    model_no = fields.Char('Model No')
    brand_id = fields.Many2one('product.brand', 'Brand')
    service_ids = fields.Many2many('printer.service', 'print_machine_services_rel', string='Services')
    image_printer = fields.Binary()
    image_1920 = fields.Image(string="Image", max_width=1920, max_height=1920)
    remarks = fields.Text('Remarks')
    active = fields.Boolean('Active', default=True)
    user_id = fields.Many2one(
        'res.users',
        string='User',
        default=lambda self: self.env.user)
    color = fields.Integer(string='Color Index', default=0)
    user_ids = fields.Many2many('res.users','user_printer_activity_rel',string='Allocated Users')
    sequence_prefix = fields.Char('Sequence Prefix')


    @api.onchange('brand_id')
    def onchange_brand_id(self):
        for i in self:
            if i.brand_id and i.brand_id.image_1920:
                i.image_printer = i.brand_id.image_1920


class PrintServices(models.Model):
    _name = 'printer.service'

    name = fields.Char('Name')
    code = fields.Char('Code')
