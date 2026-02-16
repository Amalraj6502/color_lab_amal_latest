{
    "name": "Alukkas Reports",
    "version": "18.0",
    "category": "  ",
    "summary": " Alukkas Reports ",
    "author": "Amal",
    "license": "AGPL-3",
    "depends": ['base','sale'],
    "data": [
        'report/sale_details_action.xml',
        'report/sale_alukkas_template.xml',
        'report/sale_order_report_new_list.xml',
        'report/sale_order_list_filter_report.xml',




    ],

'assets': {
    'web.report_assets_common': [
        'alukkas_reports/static/src/img/alukklogo.png',
    ],
},


    "installable": True,
    "auto_install": False,
}