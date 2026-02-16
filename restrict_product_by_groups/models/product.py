# -*- coding: utf-8 -*-
from odoo import models, api, _
from odoo.exceptions import AccessError

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model_create_multi
    def create(self, vals_list):
        if self.env.user.has_group('restrict_product_by_groups.group_product_read_only'):
            raise AccessError(_("You have Read-Only access. You cannot create products."))
        return super(ProductTemplate, self).create(vals_list)

    def write(self, vals):
        if self.env.user.has_group('restrict_product_by_groups.group_product_read_only'):
            raise AccessError(_("You have Read-Only access. You cannot edit products."))
        return super(ProductTemplate, self).write(vals)

    def unlink(self):
        if self.env.user.has_group('restrict_product_by_groups.group_product_read_only'):
            raise AccessError(_("You have Read-Only access. You cannot delete products."))
        return super(ProductTemplate, self).unlink()


    def read(self, fields=None, load='_classic_read'):
        if self.env.user.has_group('restrict_product_by_groups.group_product_read_only'):
            raise AccessError(_("You have restricted access. You cannot read products."))
        return super(ProductTemplate, self).read(fields=fields, load=load)

class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.model_create_multi
    def create(self, vals_list):
        if self.env.user.has_group('restrict_product_by_groups.group_product_read_only'):
            raise AccessError(_("You have Read-Only access. You cannot create products."))
        return super(ProductProduct, self).create(vals_list)

    def write(self, vals):
        if self.env.user.has_group('restrict_product_by_groups.group_product_read_only'):
            raise AccessError(_("You have Read-Only access. You cannot edit products."))
        return super(ProductProduct, self).write(vals)

    def unlink(self):
        if self.env.user.has_group('restrict_product_by_groups.group_product_read_only'):
            raise AccessError(_("You have Read-Only access. You cannot delete products."))
        return super(ProductProduct, self).unlink()

    def read(self, fields=None, load='_classic_read'):
        if self.env.user.has_group('restrict_product_by_groups.group_product_read_only'):
            raise AccessError(_("You have restricted access. You cannot read products."))
        return super(ProductProduct, self).read(fields=fields, load=load)
