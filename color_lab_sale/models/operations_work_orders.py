from odoo import models, fields, _, api
from odoo.exceptions import ValidationError

SELECTION_STATES = [
    ('1_draft', 'Draft'),
    ('2_in_progress', 'In Progress'),
    ('3_done', 'Done'),
    ('hold', 'Hold'),
    ('cancel', 'Cancel')
]


# HERE IT WILL STORE THE STATUS AND SALE ORDER ID WITH THE WORK ORDER DETAIL WISE
class OperationWorkOrders(models.Model):
    _name = 'operation.work.orders'
    _description = 'Operation Work Order'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Name')
    state = fields.Selection(SELECTION_STATES, string='Status', default='1_draft', index='btree_not_null',
                             tracking=True, group_expand='_group_expand_states', )
    sale_order_id = fields.Many2one('sale.order', 'Sale Order')
    work_category_id = fields.Many2one('work.category', 'Category')
    work_category_type = fields.Selection(related='work_category_id.type')
    previous_work_order_id = fields.Many2one('operation.work.orders', 'Previous Operation Work Orders')
    date = fields.Date('Date', default=fields.Date.today())
    color = fields.Integer('Color Index', default=0)
    priority = fields.Selection([('0', 'Very Low'), ('1', 'Low'), ('2', 'Normal'), ('3', 'High')], string='Priority')
    user_id = fields.Many2one('res.users', 'User')
    section = fields.Integer('Section Count', copy=False)
    batch_number = fields.Integer(string="Batch Number", default=1)
    processed_date = fields.Date('Batch Processed Date')
    active = fields.Boolean(default=True, help="Set active to false to hide the record without removing it.")
    printer_id = fields.Many2one('printer.conf', 'Printer')
    approve_count = fields.Integer('Approve Count', default=0)
    current_batch = fields.Boolean('Is Current Batch', default=False)
    group_ids = fields.Many2many(
        'res.groups',
        'operation_work_order_group_rel',
        'work_order_id',
        'group_id',
        string='Allowed Groups'
    )
    assigned_to = fields.Many2one('res.users', 'Assigned User', tracking=True)
    completion_date = fields.Date('Completion Date')
    is_step_bypass = fields.Boolean('IS Step Bypassed?', related='work_category_id.is_step_bypass',
                                    help='Used in case of correction as per requirement in the second stage.. This will help to properly bypass the record creation of the loop to keep the continuity flow of other records intact, both need to be completed and only then will it allow the creation of the next stage.')

    def _do_reject(self, category):
        self.message_post(body='Rework Or Changes in Flow..\nNew Work Flow Begins With:' + category,
                          subject="Rework Or Changes in Flow")
        self.state = 'cancel'

    def notify_users(self, users):
        self.activity_unlink(['color_lab_sale.work_order_issued_activity_type'])
        for user in users:
            self.activity_schedule('color_lab_sale.work_order_issued_activity_type', note=user.name, user_id=user.id)
        return True

    # def update_current_batch(self):
    #     current_batches = self.env['operation.work.orders'].search(
    #         [('current_batch', '=', True)])
    #     if not current_batches:
    #         batch_initial = self.env['operation.work.orders'].search(
    #             [('batch_number', '=', 1)])
    #         for i in batch_initial:
    #             i.current_batch = True
    #     batch_groups = {}
    #     batches = self.env['operation.work.orders'].search(
    #         [('current_batch', '=', True)])
    #
    #     for record in batches:
    #         if record.batch_number not in batch_groups:
    #             batch_groups[record.batch_number] = []
    #         batch_groups[record.batch_number].append(record)
    #
    #     for batch_number, records in batch_groups.items():
    #
    #         if all(record.state in ['1_draft', '2_in_progress'] for record in records):
    #             for record in records:
    #                 record.current_batch = True
    #                 print(f"Batch {batch_number} is the current batch.")
    #         if len(records) == 5 and all(
    #                 record.state == '3_done' for record in records):  # Ensure there are exactly 5 records per batch
    #             # After marking current batch as done, assign the next batch as current
    #             self.assign_next_batch(batch_number + 1)

    def update_current_batch(self, category_id, update_batch):
        current_batch_len = self.env['operation.work.orders'].sudo().search_count(
            [('current_batch', '=', True), ('work_category_id', '=', category_id.id), ('state', '!=', '3_done')])
        if current_batch_len >= 5:
            current_batch = False
        else:
            current_batch = True
        if update_batch:
            current_batch_pending = self.env['operation.work.orders'].sudo().search(
                [('current_batch', '=', False), ('work_category_id', '=', category_id.id)], limit=1, order='date asc')
            if current_batch_pending:
                current_batch_pending.sudo().write({'current_batch': True})
        else:
            return current_batch

    def assign_next_batch(self, current_batch_number):
        """
        Assign the next available batch with all 5 records either in draft or in progress
        to be the current batch once the previous one is done.
        """

        records = self.env['operation.work.orders'].search([('batch_number', '=', current_batch_number)])
        if all(record.state in ['1_draft', '2_in_progress'] for record in records):
            for record in records:
                record.current_batch = True

    def _group_expand_states(self, states, domain):
        return [state[0] for state in SELECTION_STATES]

    # def action_in_progress(self):
    #     actions = []
    #     sale_orders = set()
    #
    #     for i in self:
    #         if i.state == '1_draft':
    #             i.state = '2_in_progress'
    #             # if self.sale_order_id:
    #             #     if self.sale_order_id.is_
    #             if i.work_category_id.is_work_print and i.sale_order_id:
    #                 sale_orders.add(i.sale_order_id.id)
    #
    #     # Handle report download AFTER processing all records
    #     for so_id in sale_orders:
    #         so = self.env['sale.order'].sudo().browse(so_id)
    #         action = so.sudo().download_report()
    #         if action:
    #             actions.append(action)
    #
    #     # Return correct response
    #     if len(actions) == 1:
    #         return actions[0]
    #     elif len(actions) > 1:
    #         return actions

    def action_in_progress(self):
        actions = []
        sale_orders = set()

        for record in self:
            if record.state != '1_draft':
                continue

            record.state = '2_in_progress'
            sale_order = record.sale_order_id
            if not sale_order:
                continue

            if record.work_category_id.is_work_print:
                sale_orders.add(sale_order.id)

            if sale_order.sudo().is_mini_book_required:
                minibook_orders = self.env['operation.work.orders'].sudo().search([
                    ('sale_order_id', '=', sale_order.id),
                    ('work_category_id.type', '=', 'minibook'),('work_category_id','=',self.env.ref('color_lab_sale.correction_minibook').id),
                    ('state', '=', '1_draft'),
                ])
                for minibook in minibook_orders:
                    minibook.action_in_progress()

        for so_id in sale_orders:
            so = self.env['sale.order'].browse(so_id).sudo()
            action = so.with_user(self.env.ref("base.user_admin")).download_report()
            if action:
                actions.append(action)

        # Return proper action response
        if len(actions) == 1:
            return actions[0]
        elif len(actions) > 1:
            return actions

        return True

    def download_report_sale(self):
        so = self.env['sale.order'].sudo().browse(self.sale_order_id.id)
        action = so.sudo().download_report()
        if action:
            return action

    def open_sale_order(self):
        return {
            'name': _('Sale Order'),
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'view_mode': 'form',
            'target': 'current',
            'views': [[False, 'form']],
            'domain': [('sale_order_id', '=', self.sale_order_id.id)],
            'res_id': self.sale_order_id.id,
            'context': {'create': False, 'edit': False, 'delete': False}
        }

    def show_next_batch(self, latest_batch):
        if latest_batch:
            next_batch = latest_batch + 1
            records = self.search([('batch_number', '=', next_batch), ('active', '=', False)])
            if records:
                records.update({
                    'active': True,
                    'processed_date': fields.Date.today()
                })

    def action_mark_as_done(self):
        actions = []
        sale_orders_to_download = set()

        def fetch_latest_batch():
            latest_batch = self.env['operation.work.orders'].sudo().search([], order='batch_number desc', limit=1)
            latest_batch_number = latest_batch.batch_number if latest_batch else 0

            if latest_batch:
                records_in_latest_batch = self.env['operation.work.orders'].sudo().search_count(
                    [('batch_number', '=', latest_batch_number)])
                if records_in_latest_batch < 5:
                    current_batch = latest_batch_number
                    return current_batch
                else:
                    current_batch = latest_batch_number + 1
                    return current_batch

            else:
                current_batch = 1
                return current_batch

        for i in self:
            if i.state == '2_in_progress':
                i.state = '3_done'
                i.completion_date = fields.Date.today()
                max_approve_count = self.sudo().search(
                    [('sale_order_id', '=', i.sale_order_id.id), ('work_category_type', '=', self.work_category_type)],
                    order='approve_count desc', limit=1
                ).approve_count
                if max_approve_count:
                    i.approve_count = max_approve_count + 1
                else:
                    i.approve_count = 1

                current_step = self.work_category_id.step_count
                if current_step != 0:
                    next_step = current_step + 1
                    work_category_ids = self.env['work.category'].sudo().search(
                        [('type', '=', i.work_category_id.type), ('step_count', '=', next_step),
                         ('is_common_step', '=', False)])
                    other_work_category_ids = self.env['work.category'].sudo().search(
                        [('type', '=', i.work_category_id.type), ('section', '=', 0),
                         ('is_common_step', '=', True)])

                    existing_running_work_order_ids = self.sudo().search(
                        [('sale_order_id', '=', i.sale_order_id.id),
                         ('work_category_type', '=', i.work_category_id.type),
                         ('state', '!=', '3_done')])
                    existing_running_work_order_len = len(
                        existing_running_work_order_ids.filtered(lambda x: not x.work_category_id.is_common_step))

                    # if existing_running_work_order_len:
                    if existing_running_work_order_len == 0 and not self.is_step_bypass:
                        for categ in work_category_ids:
                            current_batch = self.update_current_batch(category_id=categ, update_batch=False)
                            operation_work_order = self.env['operation.work.orders'].sudo().create({
                                'sale_order_id': i.sale_order_id.id,
                                'work_category_id': categ.id,
                                'name': f'{i.sale_order_id.name} - {categ.name} - {categ.type} - {categ.step_count}',
                                'section': categ.section,
                                'current_batch': current_batch,
                                'group_ids': categ.group_ids,
                                'batch_number': fetch_latest_batch(),
                                # Note: We are not using batch number for now (Keeping for incase of future works)
                                'state': '1_draft',
                            })
                            if categ.is_work_print:
                                sale_orders_to_download.add(i.sale_order_id.id)
                    else:
                        work_category_ids = self.env['work.category'].sudo().search(
                            [('type', '=', i.work_category_id.type), ('step_count', '=', next_step),
                             ('is_common_step', '=', False), ('section', '=', self.section)])
                        for categ in work_category_ids:
                            current_batch = self.update_current_batch(category_id=categ, update_batch=False)
                            operation_work_order = self.env['operation.work.orders'].sudo().create({
                                'sale_order_id': i.sale_order_id.id,
                                'work_category_id': categ.id,
                                'name': f'{i.sale_order_id.name} - {categ.name} - {categ.type} - {categ.step_count}',
                                'section': categ.section,
                                'current_batch': current_batch,
                                'group_ids': categ.group_ids,
                                'batch_number': fetch_latest_batch(),
                                # Note: We are not using batch number for now (Keeping for incase of future works)
                                'state': '1_draft',
                            })
                            if categ.is_work_print:
                                sale_orders_to_download.add(i.sale_order_id.id)
                    if other_work_category_ids:
                        for categ in other_work_category_ids:
                            current_batch = self.update_current_batch(category_id=categ, update_batch=False)
                            # Get all common step IDs for this category
                            common_step_ids = categ.common_step_ids.ids
                            if categ.is_work_print:
                                sale_orders_to_download.add(i.sale_order_id.id)
                            # Fetch all work orders linked to these common steps for the same sale order
                            linked_work_orders = self.env['operation.work.orders'].sudo().search([
                                ('work_category_id', 'in', common_step_ids),
                                ('sale_order_id', '=', i.sale_order_id.id),
                            ])


                            # Ensure that ALL common steps exist in the system and are done
                            required_steps_done = len(common_step_ids) == len(linked_work_orders) and all(
                                work_order.state == '3_done' for work_order in linked_work_orders
                            )

                            # Check if the work order already exists before creating a new one
                            existing_work_order = self.env['operation.work.orders'].sudo().search([
                                ('sale_order_id', '=', i.sale_order_id.id),
                                ('work_category_id', '=', categ.id)
                            ], limit=1)

                            if required_steps_done and not existing_work_order:
                                operation_work_order = self.env['operation.work.orders'].sudo().create({
                                    'sale_order_id': i.sale_order_id.id,
                                    'work_category_id': categ.id,
                                    'name': f'{i.sale_order_id.name} - {categ.name} - {categ.type} - {categ.step_count}',
                                    'section': categ.section,
                                    'batch_number': fetch_latest_batch(),
                                    # Note: We are not using batch number for now (Keeping for incase of future works)
                                    'current_batch': current_batch,
                                    'group_ids': categ.group_ids,
                                    'state': '1_draft',
                                })

                i.sudo().update_current_batch(category_id=self.work_category_id,
                                              update_batch=True)  # Call the function to check pending records and update current batch
            if i.sale_order_id.sudo().is_mini_book_required and not self.env.context.get('is_mini'):
                minibook_orders = self.env['operation.work.orders'].sudo().search([
                    ('sale_order_id', '=', i.sale_order_id.id),
                    ('work_category_id.type', '=', 'minibook'),
                    ('work_category_id', '=', self.env.ref('color_lab_sale.correction_minibook').id),
                    ('state', '=', '2_in_progress'),
                ])
                for minibook in minibook_orders:
                    minibook.with_context(is_mini=True).action_mark_as_done()

        # Collect unique report actions for download
        for so_id in sale_orders_to_download:
            so = self.env['sale.order'].sudo().browse(so_id)
            report_action = so.with_user(self.env.ref("base.user_admin")).download_report()
            actions.append(report_action)
        if not sale_orders_to_download:
            return {
                'effect': {
                    'fadeout': 'slow',
                    'message': 'Job Done',
                    'type': 'rainbow_man',
                }
            }
        return actions if len(actions) > 1 else actions[0] if actions else False

    @api.onchange('state')
    @api.constrains('state')
    def onchange_status(self):
        for i in self:
            if i.state == '2_in_progress':
                i.assigned_to = self.env.user.id
            if i.state == '3_done':
                i.action_mark_as_done()


    def revise_order_flow(self):
        return {
            'name': _('Work Order Change'),
            'type': 'ir.actions.act_window',
            'res_model': 'work.flow.change.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_sale_order_id': self.sale_order_id.id,
                        'default_work_order_id': self.id,
                        'default_date': fields.Date.today(),
                        'default_type': self.work_category_id.type,
                        'default_current_category_id': self.work_category_id.id,
                        }
        }

    def write(self, vals):
        if 'state' in vals:
            for rec in self:
                # If record is already Done → block any state change
                if rec.state == '3_done' and vals.get('state') != '3_done':
                    raise ValidationError(
                        "Once the record is marked as Done, it cannot be moved back."
                    )

        return super().write(vals)


