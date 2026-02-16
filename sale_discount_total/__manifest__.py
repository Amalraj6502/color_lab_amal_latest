# -*- coding: utf-8 -*-
{
    'name': 'Sale Discount on Total Amount',
    'version': '18.0.1.1.0',
    'category': 'Sales Management',
    'summary': "Discount on Total in Sale and Invoice With Discount Limit "
               "and Approval",
    'description': "This module is designed to manage discounts on the total "
                   "amount in sales. It will include features to apply "
                   "discounts either as a specific amount or a percentage. "
                   "This module will enhance the functionality of Odoo's sales "
                   "module, allowing users to easily manage and apply discounts"
                   " to sales orders based on their requirements.",
    'author': 'Cybrosys Techno Solutions',
    'company': 'Cybrosys Techno Solutions',
    'maintainer': 'Cybrosys Techno Solutions',
    'website': "https://www.cybrosys.com",
    'depends': ['sale_management', 'account',],
    'data': [
        'views/res_config_settings_views.xml',
        # 'views/sale_order_views.xml',
        'views/account_move_views.xml',
        'views/account_move_templates.xml',
        # 'views/sale_order_templates.xml',
    ],
    'images': ['static/description/banner.png'],
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
