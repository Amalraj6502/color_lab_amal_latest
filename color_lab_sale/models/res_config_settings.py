# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    emboss_rate = fields.Float(string='Emboss Rate',
                               help='Set Emboss Rate to calculate the emboss amount in sales',
                               config_parameter='color_lab_sale.emboss_rate')
