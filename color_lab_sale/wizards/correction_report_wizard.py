from odoo import models, fields
from odoo.exceptions import UserError


class CorrectionWorkOrderReportWizard(models.TransientModel):
    _name = 'correction.work.order.report.wizard'
    _description = 'Correction Work Order Employee-wise Report Wizard'

    start_date = fields.Date(string="Start Date", required=True)
    end_date = fields.Date(string="End Date")

    user_ids = fields.Many2many(
        'res.users',
        string="Employees",
        domain=lambda self: [
            ('groups_id', 'in', self.env.ref('color_lab_sale.group_correction_users').id)
        ]
    )

    minibook_required = fields.Boolean(string="Mini Book Required")
    sale_order_id = fields.Many2one('sale.order', string="Sale Order")

    def action_print_report(self):
        self.ensure_one()
        category_ids = [self.env.ref('color_lab_sale.correction_normal').id]

        if self.minibook_required:
            category_ids.append(
                self.env.ref('color_lab_sale.correction_minibook').id
            )
        domain = [
            ('work_category_id', 'in', category_ids),
            ('completion_date', '>=', self.start_date),
            ('state', 'in', ('2_in_progress', '3_done')),
        ]

        if self.end_date:
            domain.append(('completion_date', '<=', self.end_date))
            if self.start_date > self.end_date:
                raise UserError("Start Date must be earlier than End Date.")

        if self.user_ids:
            domain.append(('assigned_to', 'in', self.user_ids.ids))

        # if self.minibook_required:
        #     domain.append((
        #         'work_category_id',
        #         '=',
        #         self.env.ref('color_lab_sale.correction_minibook').id
        #     ))
        print(domain,"DOMAINNN")
        work_orders = self.env['operation.work.orders'].sudo().search(
            domain,
            order='assigned_to, completion_date'
        )
        print(work_orders, 'WORK ORDER REPORT')
        return self.env.ref(
            'color_lab_sale.action_correction_work_order_report'
        ).with_context(
            start_date=self.start_date,
            end_date=self.end_date,
            work_order_ids=work_orders.ids,
        ).report_action(self)
