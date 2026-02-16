{
    'name': 'ReadOnly Product Template Access',
    'version': '18.0.1.0.0',
    'category': 'Sales',
    'summary': 'Restrict users to Read-Only access for Product Templates',
    'description': """
        This module creates a security group 'Product Read-Only'.
        Users in this group will only have Read/View access to product templates.
        They will be restricted from creating, writing (editing), or deleting products.
    """,
    'author': 'Amal',
    'depends': ['base', 'product', 'sale'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/sale_order_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
