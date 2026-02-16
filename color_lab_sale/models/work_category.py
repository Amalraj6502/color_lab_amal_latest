from odoo import models, fields, api


# USING FOR CORRECTION, LAMINATION ETC..
class WorkCategory(models.Model):
    _name = 'work.category'
    _description = 'Work Category'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="Name", required=True)
    type = fields.Selection([('normal', 'Normal'), ('minibook', 'Mini Book'), ('addons', 'Addons'), ('frame', 'Frame'),
                             ('digital', 'Digital Print'), ('calender', 'Calender')], string='Type',
                            default='normal')
    step_count = fields.Integer('Step Count', help='Level Based count to manage the workflow')
    display_name = fields.Char(string='Display Name', compute='_compute_display_name')
    previous_step = fields.Many2one('work.category', 'Previous Step', help='Setting up for managing previous step')
    is_common_step = fields.Boolean('Common Step', help='Enable this if it is a common step in the workflow')
    common_step_ids = fields.Many2many(
        'work.category',
        'common_steps_custom_work_category_rel',
        'work_category_id',
        'common_step_id',
        string='Common Steps', help='Common steps related to this work category'
    )
    section = fields.Integer('Section', copy=False, help='Vertical Section related to this work category')
    is_work_print = fields.Boolean('Is Work Print',
                                   help='Used in case of need to generate report at the end of the stage')
    group_ids = fields.Many2many(
        'res.groups',
        string='Allowed User Groups',
        help='Allowed User Groups related to this work category. This will helps to hide the records on the basis of groups'
    )
    is_step_bypass = fields.Boolean('Is Step Bypass',
                                    help='Used in case of correction as per requirement in the second stage.. This will help to properly bypass the record creation of the loop to keep the continuity flow of other records intact, both need to be completed and only then will it allow the creation of the next stage.')

    @api.depends('name', 'step_count')
    def _compute_display_name(self):
        for order in self:
            name = order.name
            step_count = order.step_count
            type = dict(order._fields['type'].selection).get(order.type)
            if name and step_count:
                name = f'{step_count} - {name} - {type}'
            order.display_name = name
