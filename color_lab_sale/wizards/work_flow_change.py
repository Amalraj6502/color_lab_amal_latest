from odoo import fields, models, _, api
from odoo.exceptions import UserError


class WorkFlowChangeWizard(models.TransientModel):
    """Customer Analysis wizard."""

    _name = 'work.flow.change.wizard'
    _description = 'Work Flow Change Wizard'

    date = fields.Date()
    sale_order_id = fields.Many2one('sale.order', 'Sale Order')
    type = fields.Selection([('normal', 'Normal'), ('minibook', 'Minibook'), ('addons', 'Addons'), ('frame', 'Frame'),
                             ('digital', 'Digital'), ('calender', 'Calender')])
    state = fields.Selection(related='sale_order_id.state')

    @api.depends('current_category_id')
    def get_current_category_domain(self):
        for rec in self:
            if self.current_category_id:
                rec.category_domain = [
                        ('type', '=', self.current_category_id.type),
                        ('step_count', '<', self.current_category_id.step_count),
                    ]
            else:
                rec.category_domain = []

    category_domain = fields.Char(compute=get_current_category_domain)

    current_category_id = fields.Many2one('work.category', 'Current Category')
    new_category_id = fields.Many2one('work.category', 'New Category',domain=category_domain)


    reason = fields.Text('Reason')
    current_normal_order_status = fields.Many2one('operation.work.orders', 'Current Normal Order Status',
                                                  related='sale_order_id.current_normal_order_status')
    current_minibook_order_status = fields.Many2one('operation.work.orders', 'Current Minibook Order Status',
                                                    related='sale_order_id.current_minibook_order_status')
    current_addons_order_status = fields.Many2one('operation.work.orders', 'Current Addons Order Status',
                                                  related='sale_order_id.current_addons_order_status')
    work_order_id = fields.Many2one('operation.work.orders', 'Work Order')

    def action_confirm(self):
        if self.sale_order_id and self.type:
            if self.type == 'minibook' and not self.sale_order_id.sudo().is_mini_book_required:
                raise UserError('There is no current active Minibooks available')
            if self.type == 'addons' and not self.sale_order_id.sudo().is_addons:
                raise UserError('There is no current active Addons available')
            self.sale_order_id.sudo().revised_work_order(self.new_category_id, self.type)
            activity_type = self.env.ref('web_approval.mail_activity_approval')
            model = 'sale.order'
            rec_id = self.sale_order_id.id
            activitie = self.env['mail.activity'].sudo().search(
                [('activity_type_id', '=', activity_type.id), ('res_model', '=', model), ('res_id', '=', rec_id)])
            for act in activitie:
                act.unlink()
            record_id = self.sale_order_id.sudo()
            record_id.message_mail_with_source(
                "color_lab_sale.sale_work_order_change_comment_summary",
                render_values={
                    "title": _('Work Order has been changed with the following comment:'),
                    "comment": self.reason + ' - ' + self.new_category_id.name,
                },
            )
        return {'type': 'ir.actions.act_window_close'}
