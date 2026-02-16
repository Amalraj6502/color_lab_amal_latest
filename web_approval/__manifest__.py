# -*- encoding: utf-8 -*-

{
    'name': 'Approval Widget',
    'version': '1.0',
    'category': 'Tools',
    'author': 'Klystron Global',
    'description': """Widget for approvals that can be used in any forms.""",
    'summary': 'Approval widgets for form views.',
    'website': 'www.klystronglobal.com',
    'images': ['static/description/icon.png'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/data.xml',
        'views/approval_template_views.xml',
        'views/approval_type_views.xml',
        'wizard/reject_comment_views.xml',
    ],
    'depends': ['base', 'mail','web'],
    'assets': {
        'web.assets_backend': [
            'web_approval/static/src/views/**/*',
        ],
    },
    'installable': True,
    'auto_install': False,
    'application': True,
    'sequence': 105,
    'license': 'AGPL-3',
}
