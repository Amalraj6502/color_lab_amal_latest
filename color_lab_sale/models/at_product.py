from odoo import models, fields, api


class ATProduct(models.Model):
    _name = 'at.product'
    _description = 'Product AT'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="Product Name", required=True)
    size = fields.Char("Size")
    rate = fields.Float('Rate')
    # page = fields.Integer('Page')
    company_id = fields.Many2one('res.company', string="Company")
    parent_id = fields.Many2one('at.product', 'Parent Product')
    printer_id = fields.Many2one('printer.conf', 'Printer')

    @api.depends('name', 'size', 'rate')
    def _compute_display_name(self):
        for i in self:
            if i.name and i.size and i.rate:
                i.display_name = f'{i.name} - ({i.size}) - ({i.printer_id.name}) - ({i.rate})'
