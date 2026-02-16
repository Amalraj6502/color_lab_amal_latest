from odoo import models, fields, api


class ProductProduct(models.Model):
    _inherit = 'product.template'

    at_type = fields.Selection(
        [('lamination', 'Lamination'), ('cover', 'Cover'), ('calendar', 'Calendar'),
         ('frame', 'Frame'), ('addons', 'Addons'), ('making', 'Making')],
        string='Type')
    is_product_template_category = fields.Boolean('IS Product Template Category')


class ProductTemplate(models.Model):
    _inherit = 'product.product'

    is_addon_product = fields.Boolean('Addon Product')
    is_minibook = fields.Boolean('Is Minibook')
    at_product_template_id = fields.Many2one('product.template', 'Product Template')
    at_type = fields.Selection(
        [('lamination', 'Lamination'), ('cover', 'Cover'), ('calendar', 'Calendar'),
         ('frame', 'Frame'), ('addons', 'Addons'), ('making', 'Making')], related='at_product_template_id.at_type',
        string='Type')
    is_variant = fields.Boolean('Variant')

    total_price_with_tax = fields.Float(
        string='Total Price With Tax',
        compute='_compute_total_price_with_tax',
        store=True
    )

    @api.depends('lst_price', 'taxes_id')
    def _compute_total_price_with_tax(self):
        for product in self:
            price_unit = product.lst_price
            taxes = product.taxes_id

            # Compute taxes using Odoo's tax system
            if taxes:
                tax_data = taxes.compute_all(price_unit)
                total = tax_data.get('total_included', price_unit)
            else:
                total = price_unit

            product.total_price_with_tax = total
