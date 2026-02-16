from datetime import datetime
from datetime import timedelta, date
from itertools import groupby

from lxml import etree
from odoo.addons.web_approval.models.approval_mixin import _APPROVAL_STATES

from odoo import models, fields, api, _, Command
from odoo.exceptions import UserError, ValidationError, AccessError
from odoo.tools import float_round


class SaleOrderInherit(models.Model):
    _name = 'sale.order'
    _inherit = ['sale.order', 'mail.activity.mixin', 'approval.mixin', 'approval.template']

    agent_id = fields.Many2one('agent.form', 'Agent', domain=[('state', '=', 'confirm')], tracking=True,
                               default=lambda self: self.env.user.partner_id.agent_id)
    approval_state = fields.Selection(string='Approval Status', selection=_APPROVAL_STATES, required=False, copy=False,
                                      is_approval_state=True, tracking=True)
    is_approver = fields.Boolean(compute='compute_is_approver')
    is_approval_required = fields.Boolean('Is Approval Required')
    # due_status = fields.Selection(selection=[('normal', 'Normal'), ('overdue', 'Overdue')], string='Due Status')
    # due_amount = fields.Monetary('Due Amount')

    due_status = fields.Selection(selection=[('normal', 'Normal'), ('overdue', 'Overdue')], string='Due Status',
                                  compute="_compute_due_status")
    due_amount = fields.Monetary('Due Amount', compute="_compute_due_status")

    due_agent_status = fields.Selection(selection=[('normal', 'Normal'), ('overdue', 'Overdue')],
                                        string='Agent Due Status',
                                        compute="_compute_agent_due_status")
    due_agent_amount = fields.Monetary('Agent Due Amount', compute="_compute_agent_due_status")

    printer_id = fields.Many2one('printer.conf', 'Printer', tracking=True)
    layouts = fields.Selection(selection=[('book', 'Book'), ('flat', 'Flat')])
    number_of_sheets = fields.Integer('Number Of Sheets', tracking=True)
    title = fields.Char('Title', tracking=True)
    description = fields.Text('Description', tracking=True)
    package_id = fields.Many2one('printer.package', 'Package', tracking=True)
    is_mini_book_required = fields.Boolean('Mini Book Required')
    service_id = fields.Many2one('printer.service', 'Service', tracking=True)
    service_code = fields.Char(related='service_id.code')

    # MINI BOOK CONFIGURATIONS
    mini_book_count = fields.Integer('Mini Book Count', default=1, tracking=True)
    mini_book_conf = fields.Many2one('mini.book.conf', 'Mini Book Configuration', tracking=True)
    mini_book_height = fields.Float('Height(cm)', tracking=True)
    mini_book_weight = fields.Float('Weight(cm)', tracking=True)
    mini_book_length = fields.Float('Length(cm)', tracking=True)
    mini_book_width = fields.Float('Width(cm)', tracking=True)
    # mini_book_amount = fields.Monetary('Amount', tracking=True)
    mini_book_amount = fields.Monetary(
        'Amount',
        tracking=True
    )

    mini_book_remarks = fields.Text('Remarks', tracking=True)
    mini_book_qty = fields.Float('Quantity', tracking=True, default=1)

    mini_total = fields.Monetary('Minibook Total', compute='compute_minitotal')

    # ADDONS PRODUCT CONFIGURATIONS
    is_addons = fields.Boolean('Is Addons')
    addons_line_ids = fields.One2many('addons.conf', 'order_id', 'Addons Lines')

    sale_confirm_date = fields.Datetime(
        string="Sale Confirm Date",
        help="Shows the confirmation datetime"
    )

    validity_date = fields.Date(
        string='Expiration',
        default=lambda self: date.today() + timedelta(days=15)
    )

    quote_ref = fields.Char()

    normal_order_types = fields.Selection(
        [('correction', 'Correction Form'), ('printing', 'Printing'), ('window_cut', 'Window Cut'),
         ('lamination', 'Lamination/PIN'), ('cake', 'Cake')], 'Normal Order Type Status', tracking=True)

    minibook_order_status = fields.Selection(
        [('pending', 'Pending'), ('in_progress', 'In Progress'), ('Completed', 'Completed')], tracking=True)
    minibook_order_types = fields.Selection(
        [('correction', 'Correction Form'), ('printing', 'Printing'), ('window_cut', 'Window Cut'),
         ('lamination', 'Lamination/PIN'), ('cake', 'Cake')], 'Normal Order Type Status', tracking=True)

    rejection_by = fields.Many2one('res.users', string='Rejected By')
    rejection_date = fields.Datetime(string='Rejection Date')
    rejection_message = fields.Html(string="Rejection Info", compute="_compute_rejection_message", store=True)
    is_rejected = fields.Boolean(string="Is Rejected", default=False)

    approver_name = fields.Char(string=' Approver Name')
    is_first_approved = fields.Boolean(string='First Approval Done', default=False)

    at_rate_total = fields.Float(string="AT Rate Total", compute="_compute_at_rate_total", store=True)

    # @api.depends('mini_book_conf', 'is_mini_book_required')
    # def _compute_mini_book_amount(self):
    #     for rec in self:
    #         if rec.mini_book_conf and rec.is_mini_book_required:
    #             rec.mini_book_amount = rec.mini_book_conf.amount
    #         else:
    #             rec.mini_book_amount = 0.0

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        res = super()._onchange_partner_id()

        if self.partner_id and not self.partner_id.property_payment_term_id:
            payment_term = self.env['account.payment.term'].search(
                [('name', '=', '7 Days')], limit=1
            )
            if payment_term:
                self.payment_term_id = payment_term.id
        return res

    @api.depends('at_page', 'at_rate')
    def _compute_at_rate_total(self):
        for rec in self:
            page_total = rec.at_page * rec.at_rate
            tax_add = page_total * 18
            tax_total = tax_add / 100
            rec.at_rate_total = page_total + tax_total

    @api.depends('rejection_by', 'rejection_date')
    def _compute_rejection_message(self):
        for rec in self:
            if rec.rejection_by and rec.rejection_date:
                rec.rejection_message = f"""
                    <p style="color:red;font-weight:bold;">
                        Rejected By <b>{rec.rejection_by.name}</b> on 
                        <b>{fields.Datetime.to_string(rec.rejection_date)}</b>.
                    </p>
                    """
            else:
                rec.rejection_message = False

    @api.depends('mini_book_amount', 'mini_book_qty')
    def compute_minitotal(self):
        for i in self:
            if i.mini_book_amount and i.mini_book_qty:
                if i.package_loaded:
                    if i.package_id.mini_book_conf:
                        if not i.package_id.mini_book_conf.id == i.mini_book_conf.id:
                            if i.mini_book_amount > i.package_id.mini_book_amount:
                                i.mini_total = i.mini_book_amount - i.package_id.mini_book_amount
                            else:
                                i.mini_total = 0
                        else:
                            i.mini_total = i.mini_book_amount * i.mini_book_qty
                    else:
                        i.mini_total = i.mini_book_amount * i.mini_book_qty
                else:
                    i.mini_total = i.mini_book_amount * i.mini_book_qty
            else:
                i.mini_total = 0

    @api.onchange('agent_id')
    def onchange_agent_id(self):
        for i in self:
            if not i.agent_id:
                i.partner_id = False

    @api.depends('agent_id')
    def compute_customers_from_agent(self):
        for rec in self:
            if rec.agent_id:
                partners = self.env['res.partner'].search(
                    [('parent_id', '=', self.agent_id.partner_id.id), ('is_agent_customer', '=', True)])
                rec.agent_customer_domain = [('id', 'in', partners.ids)]
            else:
                rec.agent_customer_domain = []

    agent_customer_domain = fields.Char(compute='compute_customers_from_agent')
    service_domain = fields.Char(compute='compute_printer_service')
    minibook_lines = fields.Many2many('sale.order.line', 'minibook_lines_rel', string='Minibook Lines')
    is_emboss_cover = fields.Boolean('Emboss Cover Required?', tracking=True)
    is_emboss_box = fields.Boolean('Emboss Box Required?', tracking=True)
    is_emboss_print = fields.Boolean('Emboss Print Required?', tracking=True)
    emboss_cover = fields.Selection([('250', '250'), ('500', '500'), ('750', '750'), ('1000', '1000')],
                                    string='EMBOSS COVER', tracking=True)
    emboss_box = fields.Selection([('250', '250'), ('500', '500'), ('750', '750'), ('1000', '1000')],
                                  string='EMBOSS BOX', tracking=True)
    # emboss_print = fields.Selection([('250', '250'), ('500', '500'), ('750', '750'), ('1000', '1000')],
    #                                 string='EMBOSS PRINT', tracking=True)

    emboss_print = fields.Selection([('singleleaf', 'Single Leaf')],
                                    string='EMBOSS PRINT', tracking=True)
    emboss_print_qty = fields.Float('Emboss Print Qty', default=1.00)
    emboss_print_rate = fields.Float('Emboss Print Rate', compute='compute_emboss_rate', store=True)
    emboss_print_total = fields.Float('Emboss Print Total', compute='compute_emboss_rate')

    emboss_cover_description = fields.Char('Emboss Cover Description', tracking=True)
    emboss_box_description = fields.Char('Emboss Box Description', tracking=True)
    emboss_print_description = fields.Char('Emboss Print Description', tracking=True)

    # Adjust field names and labels for clarity
    current_normal_order_status = fields.Many2one('operation.work.orders', 'Current Normal Order Status',
                                                  compute='compute_normal_order_status')
    current_minibook_order_status = fields.Many2one('operation.work.orders', 'Current Minibook Order Status',
                                                    compute='compute_normal_order_status')
    current_addons_order_status = fields.Many2one('operation.work.orders', 'Current Addons Order Status',
                                                  compute='compute_normal_order_status')
    show_order_status_section = fields.Boolean(compute='_compute_show_order_status_section')
    at_product = fields.Many2one('at.product', string='Main Product', tracking=True)
    at_size = fields.Char('Size', related='at_product.size')
    at_page = fields.Integer('Page', tracking=True, default=1)
    at_rate = fields.Float('Rate', related='at_product.rate')
    at_total = fields.Float('Main Product Total', compute='compute_at_rate')
    addons_total = fields.Float('Main Product Total', compute='compute_addons_total')
    grand_total = fields.Monetary('Grand Total', compute='compute_grand_total')
    is_frame = fields.Boolean('Is Frame')
    is_digital = fields.Boolean('Is Digital')
    is_calender = fields.Boolean('Is Calender')
    work_type = fields.Selection([('normal', 'Normal'), ('other', 'Other')],
                                 string='Work Type', default='normal')
    work_title = fields.Many2one('sales.title.conf', string='Work Title', tracking=True)
    work_description = fields.Text('Work Description', tracking=True)
    courier_type = fields.Many2one('courier.type.conf', string='Courier Type', tracking=True)

    max_addon_size = fields.Integer('Max Addons Size', related='package_id.max_addon_size')
    agent_commission = fields.Monetary(string="Agent Commission", compute="_compute_agent_commission")
    at_special_description = fields.Text('Description')
    order_line_total = fields.Monetary('Order Lines Total', compute='compute_order_line_total')

    package_loaded = fields.Boolean(string="Package Loaded", default=False)
    quotation_number = fields.Char('Quotation Number',
                                   help='This will helps to check if the quotation number needed in reporting purpose')

    is_final_approved = fields.Boolean(string='Final Approval Done', default=False)
    all_due_customer = fields.Monetary('Draft Due Customer', compute='_compute_due_status')
    all_due_agent = fields.Monetary('Draft Due Amount Agent', compute='_compute_agent_due_status')
    all_due_customer_status = fields.Selection(selection=[('normal', 'Normal'), ('overdue', 'Overdue')],
                                               string='Draft Due Customer Status',
                                               compute="_compute_due_status")
    all_due_agent_status = fields.Selection(selection=[('normal', 'Normal'), ('overdue', 'Overdue')],
                                            string='Draft Due Agent Status', store=True,
                                            compute="_compute_due_status")
    check_order_group = fields.Boolean(string="check User Group", compute='compute_check_order_user', copy=False)
    check_admin_group = fields.Boolean(string="check User Group for Admin", compute='check_access_admin', copy=False)

    at_rate_total_report = fields.Float(string="AT Rate Total", compute="_compute_at_rate_total_report", store=True,
                                        digits=(12, 2))

    def action_download_list_report(self):
        return self.env.ref('alukkas_reports.action_sale_order_list_view_filter').report_action(self)

    @api.depends('at_rate')
    def _compute_at_rate_total_report(self):
        for rec in self:
            # page_total = rec.at_page * rec.at_rate
            rate_add = rec.at_rate * 18
            rate_total = rate_add / 100
            rec.at_rate_total_report = rec.at_rate + rate_total

    @api.depends('user_id')
    @api.depends_context('uid')
    def compute_check_order_user(self):
        is_order_group = not self.env.is_admin() and self.env.user.has_group(
            'color_lab_sale.group_order_users')
        for record in self:
            record.check_order_group = bool(is_order_group)

    @api.depends('user_id')
    @api.depends_context('uid')
    def check_access_admin(self):
        is_order_group = self.env.is_admin() or self.env.user.has_group(
            'base.group_erp_manager')
        for record in self:
            record.check_admin_group = bool(is_order_group)

    @api.depends_context('uid')
    def _compute_show_order_status_section(self):
        is_allowed = self.env.is_admin() or self.env.user.id == 57
        for record in self:
            record.show_order_status_section = is_allowed

    @api.model
    def get_view(self, view_id=None, view_type='form', **options):
        res = super(SaleOrderInherit, self).get_view(view_id, view_type)
        if view_type in ['list', 'form']:
            user = self.env.user
            has_access = user.has_group('color_lab_sale.group_order_users') or \
                         user.has_group('color_lab_sale.group_order_agent_users')

            if not has_access:
                doc = etree.XML(res['arch'])
                for node in doc.xpath("//list"):
                    node.set('create', '0')
                for node in doc.xpath("//form"):
                    node.set('create', '0')
                res['arch'] = etree.tostring(doc)
        return res

    def download_report(self):
        return self.env.ref('alukkas_reports.action_normal_credit_note_custom_report').sudo().report_action(self.sudo())

    def download_report_quotation(self):
        return self.env.ref('alukkas_reports.action_sale_order_new_view_report').sudo().report_action(self.sudo())

    @api.constrains('order_line', 'at_page')
    def _check_page_restriction(self):
        for order in self:
            type_quantities = {}
            # if not order.package_id:
            if order.order_line and order.at_page > 0:
                for line in order.order_line:
                    at_type = line.at_type
                    type_quantities[at_type] = type_quantities.get(at_type, 0) + line.product_uom_qty

                for at_type, total_qty in type_quantities.items():
                    if total_qty > order.at_page:
                        raise ValidationError(
                            f"Total quantity for type {at_type} exceeds the allowed pages ({order.at_page}).")

    @api.depends('addons_line_ids', 'addons_line_ids.price_subtotal')
    def compute_addons_total(self):
        for i in self:
            i.addons_total = sum(line.price_subtotal for line in i.addons_line_ids)

    @api.depends('partner_id')
    def _compute_due_status(self):
        for order in self:
            total_due = 0.0
            total_due_with_draft = 0.0
            overdue = False
            draft_overdue = False
            if order.partner_id:
                invoices_without_draft = self.env['account.move'].search([
                    ('partner_id', '=', order.partner_id.id),
                    ('state', '=', 'posted'),
                    ('payment_state', 'in', ['not_paid', 'partial'])
                ])
                invoices_with_draft = self.env['account.move'].search([
                    ('partner_id', '=', order.partner_id.id),
                    ('state', 'in', ('posted', 'draft')),
                ])
                if invoices_without_draft:
                    for inv in invoices_without_draft:
                        total_due += inv.amount_residual
                        if inv.invoice_date_due and inv.invoice_date_due < fields.Date.today():
                            overdue = True
                if invoices_with_draft:
                    for inv in invoices_with_draft:
                        total_due_with_draft += inv.amount_residual
                        if inv.invoice_date_due and inv.invoice_date_due < fields.Date.today():
                            draft_overdue = True
            order.all_due_customer = total_due_with_draft
            order.due_amount = total_due
            order.due_status = 'overdue' if overdue else 'normal'
            order.all_due_customer_status = 'overdue' if draft_overdue else 'normal'

    @api.depends('agent_id')
    def _compute_agent_due_status(self):
        for order in self:
            total_due = 0.0
            total_due_with_draft = 0.0
            overdue = False
            draft_overdue = False

            if order.agent_id:
                invoices_without_draft = self.env['account.move'].search([
                    ('agent_id', '=', order.agent_id.id),
                    ('state', '=', 'posted'),
                    ('payment_state', 'in', ['not_paid', 'partial'])
                ])
                # print(invoice)
                invoices_with_draft = self.env['account.move'].search([
                    ('agent_id', '=', order.agent_id.id),
                    ('state', 'in', ('posted', 'draft')),
                ])
                if invoices_without_draft:
                    for inv in invoices_without_draft:
                        total_due += inv.amount_residual
                        if inv.invoice_date_due and inv.invoice_date_due < fields.Date.today():
                            overdue = True
                if invoices_with_draft:
                    for inv in invoices_with_draft:
                        total_due_with_draft += inv.amount_residual
                        if inv.invoice_date_due and inv.invoice_date_due < fields.Date.today():
                            draft_overdue = True
            order.all_due_agent = total_due_with_draft
            order.due_agent_amount = total_due
            order.due_agent_status = 'overdue' if overdue else 'normal'
            order.all_due_agent_status = 'overdue' if draft_overdue else 'normal'

    @api.depends('agent_id', 'printer_id', 'amount_total')
    def _compute_agent_commission(self):
        for order in self:
            commission = 0.0
            if order.agent_id and order.printer_id:
                commission_line = self.env['commission.conf'].search([
                    ('agent_id', '=', order.agent_id.id),
                    ('printer_id', '=', order.printer_id.id)
                ], limit=1)

                if commission_line:
                    commission = (commission_line.commission_percentage / 100) * order.amount_total

            order.agent_commission = commission

    @api.constrains('max_addon_size', 'package_id', 'at_page')
    @api.onchange('package_id', 'max_addon_size', 'at_page')
    def check_constrain_addons(self):
        for i in self:
            if i.at_page and i.package_id and i.service_id.code in ('package', 'photobook'):
                if i.package_id.is_warning_required:
                    if i.at_page > (i.package_id.max_addon_size + i.package_id.at_page):
                        raise UserError(
                            'You cannot add more than the maximum addons assigned in this package.\n'
                            'Current Allowed Addon Size: %s\nCurrent Selected Addons: %s' %
                            ((i.max_addon_size + i.package_id.at_page), i.at_page)
                        )

    # @api.depends('is_emboss_print', 'emboss_print_qty', 'emboss_print')
    # def compute_emboss_rate(self):
    #     for i in self:
    #         if i.is_emboss_print:
    #             emboss_rate = self.env['ir.config_parameter'].sudo().get_param('color_lab_sale.emboss_rate')
    #             i.emboss_print_rate = float(emboss_rate)
    #             if i.emboss_print_qty > 1:
    #                 i.emboss_print_total = (float(emboss_rate) * i.emboss_print_qty)
    #             else:
    #                 i.emboss_print_total = float(emboss_rate)
    #         else:
    #             i.emboss_print_rate = 0.00
    #             i.emboss_print_total = 0.00

    @api.depends('is_emboss_print', 'emboss_print_qty', 'emboss_print')
    def compute_emboss_rate(self):
        for i in self:
            if i.is_emboss_print and i.emboss_print:
                emboss_rate = self.env['ir.config_parameter'].sudo().get_param('color_lab_sale.emboss_rate')
                i.emboss_print_rate = float(emboss_rate) * i.emboss_print_qty
                if i.emboss_print_qty > 1:
                    i.emboss_print_total = (float(emboss_rate) * i.emboss_print_qty)
                else:
                    i.emboss_print_total = float(emboss_rate)
            else:
                i.emboss_print_rate = 0.00
                i.emboss_print_total = 0.00

    @api.depends('at_product', 'at_page')
    def compute_at_rate(self):
        for i in self:
            if i.at_product and i.at_page:
                i.at_total = i.at_product.rate * i.at_page
            else:
                if i.at_product:
                    i.at_total = i.at_product.rate
                else:
                    i.at_total = 0

    @api.depends('order_line.price_subtotal')
    def compute_order_line_total(self):
        for record in self:
            record.order_line_total = sum(line.price_subtotal for line in record.order_line)

    @api.onchange('work_type')
    def onchange_work_type(self):
        for i in self:
            if i.work_type == 'other':
                i.mini_book_conf = False
                i.is_mini_book_required = False
                i.is_addons = False

    # Compute Normal Order Status
    @api.depends()
    def compute_normal_order_status(self):
        for i in self:
            work_orders = self.env['operation.work.orders'].sudo().search(
                [('sale_order_id', '=', i.id), ('work_category_type', '=', 'normal')], order='approve_count desc',
                limit=1
            )
            mini_work_orders = self.env['operation.work.orders'].sudo().search(
                [('sale_order_id', '=', i.id), ('work_category_type', '=', 'minibook')], order='approve_count desc',
                limit=1
            )
            addons_work_orders = self.env['operation.work.orders'].sudo().search(
                [('sale_order_id', '=', i.id), ('work_category_type', '=', 'addons')], order='approve_count desc',
                limit=1
            )
            if work_orders:
                i.current_normal_order_status = work_orders.id
            else:
                i.current_normal_order_status = False
            if mini_work_orders:
                i.current_minibook_order_status = mini_work_orders.id
            else:
                i.current_minibook_order_status = False
            if addons_work_orders:
                i.current_addons_order_status = addons_work_orders.id
            else:
                i.current_addons_order_status = False


    def open_assigned_work_order(self):
        return {
            'name': _('Operations Work Order Details'),
            'type': 'ir.actions.act_window',
            'res_model': 'operation.work.orders',
            'view_mode': 'kanban,list',
            'target': 'current',
            'domain': [('sale_order_id', '=', self.id)],
            'context': {'create': False, 'edit': False, 'delete': False}
        }

    def open_work_order_change(self):
        return {
            'name': _('Work Order Change'),
            'type': 'ir.actions.act_window',
            'res_model': 'work.flow.change.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_sale_order_id': self.id,
                        'default_date': fields.Date.today()}
        }

    @api.onchange('mini_book_conf', 'is_mini_book_required')
    def onchange_mini_book_conf(self):
        for i in self:
            if i.mini_book_conf and i.is_mini_book_required:
                i.update({
                    'mini_book_height': i.mini_book_conf.height,
                    'mini_book_weight': i.mini_book_conf.weight,
                    'mini_book_length': i.mini_book_conf.length,
                    'mini_book_width': i.mini_book_conf.width,
                    'mini_book_amount': i.mini_book_conf.amount,
                    'mini_book_remarks': i.mini_book_conf.remarks,
                    'mini_book_qty': i.mini_book_qty or 1,
                })
            else:
                i.mini_book_height = False
                i.mini_book_weight = False
                i.mini_book_length = False
                i.mini_book_width = False
                # i.mini_book_amount = False
                i.mini_book_remarks = False
                if not i.mini_book_qty:
                    i.mini_book_qty = 1

    def compute_is_approver(self):
        for rec in self:
            rec.is_approver = rec.show_approval_buttons()

    def _create_work_orders_from_step(self, start_step, work_type):
        def fetch_latest_batch():
            latest_batch = self.env['operation.work.orders'].search(
                [], order='batch_number desc', limit=1
            )
            latest_batch_number = latest_batch.batch_number if latest_batch else 0

            if latest_batch:
                count = self.env['operation.work.orders'].search_count(
                    [('batch_number', '=', latest_batch_number)]
                )
                return latest_batch_number if count < 5 else latest_batch_number + 1
            return 1

        work_categories = self.env['work.category'].sudo().search([
            ('type', '=', work_type),
            ('step_count', '>=', start_step),
            ('is_common_step', '=', False),
        ], order='step_count asc')

        for category in work_categories:
            current_batch_len = self.env['operation.work.orders'].search_count([
                ('current_batch', '=', True),
                ('work_category_id', '=', category.id),
                ('state', '=', '1_draft'),
            ])
            current_batch = current_batch_len < 5

            work_order = self.env['operation.work.orders'].sudo().create({
                'sale_order_id': self.id,
                'work_category_id': category.id,
                'name': f'{self.name} - {category.name} - {category.type} - {category.step_count}',
                'section': category.section,
                'batch_number': fetch_latest_batch(),
                'current_batch': current_batch,
                'group_ids': category.group_ids,
                'printer_id': self.printer_id.id,
            })

            work_order.sudo().notify_users(self.printer_id.user_ids)

    def revised_work_order(self, category_id, work_type):
        start_step = category_id.step_count

        running_orders = self.env['operation.work.orders'].search([
            ('sale_order_id', '=', self.id),
            ('state', '!=', '3_done'),
            ('work_category_id.step_count', '>=', start_step),
        ])

        for order in running_orders:
            order._do_reject(f"Workflow revised from step {start_step}")

        self._create_work_orders_from_step(start_step, work_type)

    # def revised_work_order(self, category_id, type):
    #     running_records = self.env['operation.work.orders'].search(
    #         [('sale_order_id', '=', self.id), ('state', '!=', '3_done')])
    #     for i in running_records:
    #         i._do_reject(category_id.name)
    #
    #     def fetch_latest_batch():
    #         latest_batch = self.env['operation.work.orders'].search([], order='batch_number desc', limit=1)
    #         latest_batch_number = latest_batch.batch_number if latest_batch else 0
    #
    #         if latest_batch:
    #             records_in_latest_batch = self.env['operation.work.orders'].search_count(
    #                 [('batch_number', '=', latest_batch_number)])
    #             if records_in_latest_batch < 5:
    #                 current_batch = latest_batch_number
    #                 return current_batch
    #             else:
    #                 current_batch = latest_batch_number + 1
    #                 return current_batch
    #
    #         else:
    #             current_batch = 1
    #             return current_batch
    #
    #     if type == 'normal':
    #         work_category_ids = self.env['work.category'].browse(category_id.id)
    #         for work_category in work_category_ids:
    #             work_order_id = self.env['operation.work.orders'].create({
    #                 'sale_order_id': self.id,
    #                 'work_category_id': work_category.id,
    #                 'name': f'RE/{self.name} - {work_category.name} - {work_category.type} - {work_category.step_count}',
    #                 'section': work_category.section,
    #                 'batch_number': fetch_latest_batch(),
    #                 # 'active': active,
    #                 'printer_id': self.printer_id.id,
    #             })
    #             work_order_id.notify_users(self.printer_id.user_ids)
    #             work_order_id.update_current_batch()
    #
    #     if type == 'minibook':
    #         work_category_ids = self.env['work.category'].browse(category_id.id)
    #
    #         for work_category in work_category_ids:
    #             work_order_id = self.env['operation.work.orders'].create({
    #                 'sale_order_id': self.id,
    #                 'work_category_id': work_category.id,
    #                 'name': f'RE/{self.name} - {work_category.name} - {work_category.type} - {work_category.step_count}',
    #                 'section': work_category.section,
    #                 'batch_number': fetch_latest_batch(),
    #                 # 'active': active,
    #                 'printer_id': self.printer_id.id,
    #             })
    #             work_order_id.notify_users(self.printer_id.user_ids)
    #             work_order_id.update_current_batch()
    #
    #     if type == 'addons':
    #         work_category_ids = self.env['work.category'].browse(category_id.id)
    #
    #         for work_category in work_category_ids:
    #             work_order_id = self.env['operation.work.orders'].create({
    #                 'sale_order_id': self.id,
    #                 'work_category_id': work_category.id,
    #                 'name': f'RE/{self.name} - {work_category.name} - {work_category.type} - {work_category.step_count}',
    #                 'section': work_category.section,
    #                 'batch_number': fetch_latest_batch(),
    #                 # 'active': active,
    #                 'printer_id': self.printer_id.id,
    #             })
    #             work_order_id.notify_users(self.printer_id.user_ids)
    #             work_order_id.update_current_batch()

    def approve(self):
        """Use this method to approve the request at any point"""
        res = super().approve()
        self.env.flush_all()
        for record in self:
            if record.work_type != 'other':
                continue
            allowed_types = set()
            if record.is_frame:
                allowed_types.add('frame')
            if record.is_digital:
                allowed_types.add('digital')
            if record.is_calender:
                allowed_types.add('calendar')

            if not allowed_types:
                raise UserError(
                    "Please enable at least one work type (Frame, Digital, or Calendar)."
                )
            invalid_lines = record.order_line.filtered(
                lambda l: l.at_type not in allowed_types
            )
            if invalid_lines:
                raise UserError(
                    "Invalid order lines detected.\n\n"
                    f"Allowed line types: {', '.join(sorted(allowed_types))}\n"
                    "Please remove other line types before proceeding."
                )
        if self.is_done:
            self.quotation_number = self.name
            current_year = datetime.today().strftime('%y')
            current_month = datetime.today().strftime('%m')

            prefix = ''
            if self.printer_id:
                printer = self.printer_id
                if printer and printer.sequence_prefix:
                    prefix = printer.sequence_prefix

            seq_code = 'sale.order'
            sequence_obj = self.env['ir.sequence'].with_company(self.company_id)
            next_sequence = sequence_obj.next_by_code(seq_code)
            sequence_number = next_sequence[-4:]

            # self.name = f"{prefix}{current_year}{current_month}{sequence_number}"
            self.quote_ref = self.name
            self.name = f"{prefix}{current_year}{current_month}{sequence_number}"
            self.action_confirm()
            self._create_invoices()

        def fetch_latest_batch():
            latest_batch = self.env['operation.work.orders'].search([], order='batch_number desc', limit=1)
            latest_batch_number = latest_batch.batch_number if latest_batch else 0

            if latest_batch:
                records_in_latest_batch = self.env['operation.work.orders'].search_count(
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

        if self.is_done and self.order_line:
            if not self.is_frame and not self.is_digital and not self.is_calender:
                work_category_ids = self.env['work.category'].sudo().search(
                    [('type', '=', 'normal'), ('step_count', '=', 1),
                     ('is_common_step', '=', False)])

                for work_category in work_category_ids:
                    current_batch_len = self.env['operation.work.orders'].search_count(
                        [('current_batch', '=', True), ('work_category_id', '=', work_category.id),('state','=','1_draft')])
                    if current_batch_len >= 5:
                        current_batch = False
                    else:
                        current_batch = True
                    work_order_id = self.env['operation.work.orders'].sudo().create({
                        'sale_order_id': self.id,
                        'work_category_id': work_category.id,
                        'name': f'{self.name} - {work_category.name} - {work_category.type} - {work_category.step_count}',
                        'section': work_category.section,
                        'batch_number': fetch_latest_batch(),
                        # Note: We are not using batch number for now (Keeping for incase of future works)
                        'current_batch': current_batch,
                        'group_ids': work_category.group_ids,
                        # 'active': active,
                        'printer_id': self.printer_id.id,
                    })
                    work_order_id.sudo().notify_users(self.printer_id.user_ids)
                    # work_order_id.sudo().update_current_batch()

                if self.mini_book_conf and self.is_mini_book_required:
                    work_category_ids = self.env['work.category'].sudo().search(
                        [('type', '=', 'minibook'), ('step_count', '=', 1), ('is_common_step', '=', False)])

                    for work_category in work_category_ids:
                        current_batch_len = self.env['operation.work.orders'].search_count(
                            [('current_batch', '=', True), ('work_category_id', '=', work_category.id)])
                        if current_batch_len >= 5:
                            current_batch = False
                        else:
                            current_batch = True
                        work_order_id = self.env['operation.work.orders'].sudo().create({
                            'sale_order_id': self.id,
                            'work_category_id': work_category.id,
                            'name': f'{self.name} - {work_category.name} - {work_category.type} - {work_category.step_count}',
                            'section': work_category.section,
                            'batch_number': fetch_latest_batch(),
                            # Note: We are not using batch number for now (Keeping for incase of future works)
                            'current_batch': current_batch,
                            'group_ids': work_category.group_ids,

                            # 'active': active,
                            'printer_id': self.printer_id.id,
                        })
                        work_order_id.sudo().notify_users(self.printer_id.user_ids)
                        # work_order_id.sudo().update_current_batch()

                if self.is_addons:
                    work_category_ids = self.env['work.category'].sudo().search(
                        [('type', '=', 'addons'), ('step_count', '=', 1), ('is_common_step', '=', False)])

                    for work_category in work_category_ids:
                        current_batch_len = self.env['operation.work.orders'].search_count(
                            [('current_batch', '=', True), ('work_category_id', '=', work_category.id)])
                        if current_batch_len >= 5:
                            current_batch = False
                        else:
                            current_batch = True
                        work_order_id = self.env['operation.work.orders'].sudo().create({
                            'sale_order_id': self.id,
                            'work_category_id': work_category.id,
                            'name': f'{self.name} - {work_category.name} - {work_category.type} - {work_category.step_count}',
                            'section': work_category.section,
                            'batch_number': fetch_latest_batch(),
                            # Note: We are not using batch number for now (Keeping for incase of future works)
                            'current_batch': current_batch,
                            'group_ids': work_category.group_ids,
                            # 'active': active,
                            'printer_id': self.printer_id.id,
                        })
                        work_order_id.sudo().notify_users(self.printer_id.user_ids)
                        # work_order_id.sudo().update_current_batch()
            else:
                if self.is_frame:
                    work_category_ids = self.env['work.category'].sudo().search(
                        [('type', '=', 'frame'), ('step_count', '=', 1), ('is_common_step', '=', False)])

                    for work_category in work_category_ids:
                        current_batch_len = self.env['operation.work.orders'].search_count(
                            [('current_batch', '=', True), ('work_category_id', '=', work_category.id)])
                        if current_batch_len >= 5:
                            current_batch = False
                        else:
                            current_batch = True
                        work_order_id = self.env['operation.work.orders'].sudo().create({
                            'sale_order_id': self.id,
                            'work_category_id': work_category.id,
                            'name': f'{self.name} - {work_category.name} - {work_category.type} - {work_category.step_count}',
                            'section': work_category.section,
                            'batch_number': fetch_latest_batch(),
                            # Note: We are not using batch number for now (Keeping for incase of future works)
                            'current_batch': current_batch,
                            'group_ids': work_category.group_ids,
                            # 'active': active,
                            'printer_id': self.printer_id.id,
                        })
                        work_order_id.sudo().notify_users(self.printer_id.user_ids)
                        # work_order_id.sudo().update_current_batch()
                if self.is_digital:
                    work_category_ids = self.env['work.category'].sudo().search(
                        [('type', '=', 'digital'), ('step_count', '=', 1), ('is_common_step', '=', False)])

                    for work_category in work_category_ids:
                        current_batch_len = self.env['operation.work.orders'].search_count(
                            [('current_batch', '=', True), ('work_category_id', '=', work_category.id)])
                        if current_batch_len >= 5:
                            current_batch = False
                        else:
                            current_batch = True
                        work_order_id = self.env['operation.work.orders'].sudo().create({
                            'sale_order_id': self.id,
                            'work_category_id': work_category.id,
                            'name': f'{self.name} - {work_category.name} - {work_category.type} - {work_category.step_count}',
                            'section': work_category.section,
                            'batch_number': fetch_latest_batch(),
                            # Note: We are not using batch number for now (Keeping for incase of future works)
                            'current_batch': current_batch,
                            'group_ids': work_category.group_ids,
                            # 'active': active,
                            'printer_id': self.printer_id.id,
                        })
                        work_order_id.sudo().notify_users(self.printer_id.user_ids)
                        # work_order_id.sudo().update_current_batch()
                if self.is_calender:
                    work_category_ids = self.env['work.category'].sudo().search(
                        [('type', '=', 'calender'), ('step_count', '=', 1), ('is_common_step', '=', False)])

                    for work_category in work_category_ids:
                        current_batch_len = self.env['operation.work.orders'].search_count(
                            [('current_batch', '=', True), ('work_category_id', '=', work_category.id)])
                        if current_batch_len >= 5:
                            current_batch = False
                        else:
                            current_batch = True
                        work_order_id = self.env['operation.work.orders'].sudo().create({
                            'sale_order_id': self.id,
                            'work_category_id': work_category.id,
                            'name': f'{self.name} - {work_category.name} - {work_category.type} - {work_category.step_count}',
                            'section': work_category.section,
                            'batch_number': fetch_latest_batch(),
                            # Note: We are not using batch number for now (Keeping for incase of future works)
                            'current_batch': current_batch,
                            'group_ids': work_category.group_ids,
                            # 'active': active,
                            'printer_id': self.printer_id.id,
                        })
                        work_order_id.sudo().notify_users(self.printer_id.user_ids)
        return res

    @api.depends('printer_id')
    @api.onchange('printer_id')
    def compute_printer_service(self):
        for rec in self:
            if rec.printer_id:
                service_ids = rec.printer_id.service_ids
                rec.service_domain = [('id', 'in', service_ids.ids)]
            else:
                rec.service_id = False
                rec.service_domain = False

    @api.model_create_multi
    def create(self, vals_list):
        """Override create method to generate a custom sequence number"""
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'sale.quotation.sequence') or _('New')
        orders = super(SaleOrderInherit, self).create(vals_list)
        # for order in orders:
        #     order.onchange_is_minibook()
        return orders

    @api.onchange('mini_book_count')
    def onchange_mini_book_count(self):
        """Update the quantity of the MiniBook product line when mini_book_count changes"""
        for order in self:
            if order.minibook_lines:
                # Find the MiniBook product line (excluding the section line)
                minibook_product_line = order.minibook_lines.filtered(
                    lambda line: line.product_id == self.env.ref('color_lab_sale.product_minibook')
                )
                if minibook_product_line:
                    minibook_product_line.product_uom_qty = order.mini_book_count

    @api.onchange('mini_book_amount')
    def onchange_mini_book_price(self):
        """Update the price of the MiniBook product line when mini_book_price changes"""
        for order in self:
            if order.minibook_lines:
                # Find the MiniBook product line (excluding the section line)
                minibook_product_line = order.minibook_lines.filtered(
                    lambda line: line.product_id == self.env.ref('color_lab_sale.product_minibook')
                )
                if minibook_product_line:
                    minibook_product_line.price_unit = order.mini_book_amount

    def button_load_package(self):
        for order in self:
            if order.package_id:
                lines = []
                order.order_line = [(5, 0, 0)]
                for line in order.package_id.package_line_ids:
                    lines.append((0, 0, {
                        "at_type": line.at_type,
                        "at_product_template_id": line.at_product_template_id.id,
                        "product_id": line.product_id.id,
                        'name': line.name,
                        "order_id": order.id,
                        "product_uom_qty": line.product_uom_qty,
                        "product_uom": line.product_uom.id,
                        "price_unit": line.price_unit,
                        "package_id": line.package_id.id,
                        "package_line_id": line.id,
                        "product_price_user": line.price_unit
                    }))
                order.write({
                    'order_line': lines,
                    'title': order.package_id.title,
                    'description': order.package_id.description,
                    # 'layouts': order.package_id.layouts,
                    'at_product': order.package_id.at_product.id,
                    'at_rate': order.package_id.at_rate,
                    'at_page': order.package_id.at_page,
                    # 'number_of_sheets': order.package_id.number_of_sheets,
                    'package_loaded': True,

                    'is_mini_book_required': order.package_id.is_mini_book_required,
                    'mini_book_height': order.package_id.mini_book_height if order.package_id.is_mini_book_required else False,
                    'mini_book_weight': order.package_id.mini_book_weight if order.package_id.is_mini_book_required else False,
                    'mini_book_length': order.package_id.mini_book_length if order.package_id.is_mini_book_required else False,
                    'mini_book_width': order.package_id.mini_book_width if order.package_id.is_mini_book_required else False,
                    'mini_book_amount': order.package_id.mini_book_amount if order.package_id.is_mini_book_required else False,
                    'mini_book_remarks': order.package_id.mini_book_remarks if order.package_id.is_mini_book_required else False,
                    'mini_book_conf': order.package_id.mini_book_conf if order.package_id.is_mini_book_required else False,
                    'mini_book_qty': order.package_id.mini_book_qty if order.package_id.is_mini_book_required else False,
                    'mini_book_count': order.package_id.mini_book_count if order.package_id.is_mini_book_required else False,

                })
                self.order_line._onchange_split_percentage()
            elif not order.package_id:
                order.order_line = [(5, 0, 0)]
                order.package_loaded = False

    @api.depends('order_line.price_subtotal', 'currency_id', 'company_id', 'at_total', 'emboss_print_total')
    def _compute_amounts(self):
        AccountTax = self.env['account.tax']
        for order in self:
            # Standard order lines computation
            order_lines = order.order_line.filtered(lambda x: not x.display_type)
            base_lines = [line._prepare_base_line_for_taxes_computation() for line in order_lines]
            base_lines += order._add_base_lines_for_early_payment_discount()
            # CUSTOM CHANGE DYNAMICALLY ADDED THE OTHER BALANCES ON THE INITIAL LINE OF EVERY SALE ORDER LINE
            if base_lines:
                base_lines[0].update({
                    'price_unit': base_lines[0].get(
                        'price_unit') + order.at_total + order.mini_total + order.emboss_print_total
                })
            # Combine both standard lines and additional charges
            all_base_lines = base_lines
            # Standard tax computation
            AccountTax._add_tax_details_in_base_lines(all_base_lines, order.company_id)
            AccountTax._round_base_lines_tax_details(all_base_lines, order.company_id)
            tax_totals = AccountTax._get_tax_totals_summary(
                base_lines=all_base_lines,
                currency=order.currency_id or order.company_id.currency_id,
                company=order.company_id,
            )

            # Update order totals
            order.amount_untaxed = tax_totals['base_amount_currency']
            order.amount_tax = tax_totals['tax_amount_currency']
            order.amount_total = tax_totals['total_amount_currency']

    @api.depends_context('lang')
    @api.depends('order_line.price_subtotal', 'currency_id', 'company_id')
    def _compute_tax_totals(self):
        AccountTax = self.env['account.tax']
        for order in self:
            order_lines = order.order_line.filtered(lambda x: not x.display_type)
            base_lines = [line._prepare_base_line_for_taxes_computation() for line in order_lines]
            # CUSTOM CHANGE DYNAMICALLY ADDED THE OTHER BALANCES ON THE INITIAL LINE OF EVERY SALE ORDER LINE
            if base_lines:
                base_lines[0].update({
                    'price_unit': base_lines[0].get(
                        'price_unit') + order.at_total + order.mini_total + order.emboss_print_total
                })
            AccountTax._add_tax_details_in_base_lines(base_lines, order.company_id)
            AccountTax._round_base_lines_tax_details(base_lines, order.company_id)
            order.tax_totals = AccountTax._get_tax_totals_summary(
                base_lines=base_lines,
                currency=order.currency_id or order.company_id.currency_id,
                company=order.company_id,
            )

    def _prepare_custom_total_lines(self, type=False, **optional_values):
        """ Prepare the values to create a new down payment section.

        :param dict optional_values: any parameter that should be added to the returned down payment section
        :return: `account.move.line` creation values
        :rtype: dict
        """
        self.ensure_one()
        if type == 'minibook':
            product_id = self.env.ref('color_lab_sale.product_minibook').id
            quantity = self.mini_book_qty
            price = self.mini_book_amount
            uom = self.env.ref('uom.product_uom_unit').id
            name = f'Main Product - {self.mini_book_conf.name}'

        elif type == 'emboss':
            product_id = self.env.ref('color_lab_sale.product_emboss').id
            quantity = self.emboss_print_qty
            price = self.emboss_print_rate
            uom = self.env.ref('uom.product_uom_unit').id
            name = f'Emboss - {self.emboss_print}'

        elif type == 'main_product':
            product_id = self.env.ref('color_lab_sale.product_main_product').id
            quantity = self.at_page
            price = self.at_rate
            uom = self.env.ref('uom.product_uom_unit').id
            name = f'Main Product - {self.at_product.name}'
        else:
            product_id = False
            quantity = 0
            price = 0
            uom = False
            name = False

        context = {'lang': self.partner_id.lang}
        custom_section_line = {
            'display_type': 'product',
            'name': name,
            'product_id': product_id,
            'product_uom_id': uom,
            'quantity': quantity,
            'price_unit': price,
            **optional_values
        }
        del context
        return custom_section_line

    def _prepare_invoice(self):
        res = super()._prepare_invoice()
        print(res, "RESSSSSS")
        res.update({
            'agent_id': self.agent_id.id
        })
        return res

    def _create_invoices(self, grouped=False, final=False, date=None):
        """ Create invoice(s) for the given Sales Order(s).

        :param bool grouped: if True, invoices are grouped by SO id.
            If False, invoices are grouped by keys returned by :meth:`_get_invoice_grouping_keys`
        :param bool final: if True, refunds will be generated if necessary
        :param date: unused parameter
        :returns: created invoices
        :rtype: `account.move` recordset
        :raises: UserError if one of the orders has no invoiceable lines.
        """
        if not self.env['account.move'].has_access('create'):
            try:
                self.check_access('write')
            except AccessError:
                return self.env['account.move']

        # 1) Create invoices.
        invoice_vals_list = []
        invoice_item_sequence = 0  # Incremental sequencing to keep the lines order on the invoice.
        for order in self:
            if order.partner_invoice_id.lang:
                order = order.with_context(lang=order.partner_invoice_id.lang)
            order = order.with_company(order.company_id)

            invoice_vals = order._prepare_invoice()
            invoiceable_lines = order._get_invoiceable_lines(final)

            if not any(not line.display_type for line in invoiceable_lines):
                continue

            invoice_line_vals = []
            down_payment_section_added = False

            # NEWLY ADDED METHOD TO ADD SOME MORE LINES IN THE INVOICEABLE LINES FOR MANAGING THE CUSTOM TOTALS
            # THE ADDED VALUES ARE MINIBOOK, EMBOSS, MAIN PRODUCT

            if order.is_mini_book_required:
                invoice_line_vals.append(
                    Command.create(
                        order._prepare_custom_total_lines(type='minibook', sequence=invoice_item_sequence)
                    ),
                )
            if order.is_emboss_print:
                invoice_line_vals.append(
                    Command.create(
                        order._prepare_custom_total_lines(type='emboss', sequence=invoice_item_sequence)
                    ),
                )
            if order.at_product:
                invoice_line_vals.append(
                    Command.create(
                        order._prepare_custom_total_lines(type='main_product', sequence=invoice_item_sequence)
                    ),
                )
            if order.is_addons:
                for line in order.addons_line_ids:
                    invoice_line_vals.append(
                        Command.create(
                            line._prepare_invoice_line(sequence=invoice_item_sequence)
                        ),
                    )

            # HERE ENDS THE CUSTOMIZATION PART

            for line in invoiceable_lines:
                if not down_payment_section_added and line.is_downpayment:
                    # Create a dedicated section for the down payments
                    # (put at the end of the invoiceable_lines)
                    invoice_line_vals.append(
                        Command.create(
                            order._prepare_down_payment_section_line(sequence=invoice_item_sequence)
                        ),
                    )
                    down_payment_section_added = True
                    invoice_item_sequence += 1

                invoice_line_vals.append(
                    Command.create(
                        line._prepare_invoice_line(sequence=invoice_item_sequence)
                    ),
                )
                invoice_item_sequence += 1

            invoice_vals['invoice_line_ids'] += invoice_line_vals
            invoice_vals_list.append(invoice_vals)

        if not invoice_vals_list and self._context.get('raise_if_nothing_to_invoice', True):
            raise UserError(self._nothing_to_invoice_error_message())

        # 2) Manage 'grouped' parameter: group by (partner_id, currency_id).
        if not grouped:
            new_invoice_vals_list = []
            invoice_grouping_keys = self._get_invoice_grouping_keys()
            invoice_vals_list = sorted(
                invoice_vals_list,
                key=lambda x: [
                    x.get(grouping_key) for grouping_key in invoice_grouping_keys
                ]
            )
            for _grouping_keys, invoices in groupby(invoice_vals_list,
                                                    key=lambda x: [x.get(grouping_key) for grouping_key in
                                                                   invoice_grouping_keys]):
                origins = set()
                payment_refs = set()
                refs = set()
                ref_invoice_vals = None
                for invoice_vals in invoices:
                    if not ref_invoice_vals:
                        ref_invoice_vals = invoice_vals
                    else:
                        ref_invoice_vals['invoice_line_ids'] += invoice_vals['invoice_line_ids']
                    origins.add(invoice_vals['invoice_origin'])
                    payment_refs.add(invoice_vals['payment_reference'])
                    refs.add(invoice_vals['ref'])
                ref_invoice_vals.update({
                    'ref': ', '.join(refs)[:2000],
                    'invoice_origin': ', '.join(origins),
                    'payment_reference': len(payment_refs) == 1 and payment_refs.pop() or False,
                })
                new_invoice_vals_list.append(ref_invoice_vals)
            invoice_vals_list = new_invoice_vals_list

        # 3) Create invoices.

        # As part of the invoice creation, we make sure the sequence of multiple SO do not interfere
        # in a single invoice. Example:
        # SO 1:
        # - Section A (sequence: 10)
        # - Product A (sequence: 11)
        # SO 2:
        # - Section B (sequence: 10)
        # - Product B (sequence: 11)
        #
        # If SO 1 & 2 are grouped in the same invoice, the result will be:
        # - Section A (sequence: 10)
        # - Section B (sequence: 10)
        # - Product A (sequence: 11)
        # - Product B (sequence: 11)
        #
        # Resequencing should be safe, however we resequence only if there are less invoices than
        # orders, meaning a grouping might have been done. This could also mean that only a part
        # of the selected SO are invoiceable, but resequencing in this case shouldn't be an issue.
        if len(invoice_vals_list) < len(self):
            SaleOrderLine = self.env['sale.order.line']
            for invoice in invoice_vals_list:
                sequence = 1
                for line in invoice['invoice_line_ids']:
                    line[2]['sequence'] = SaleOrderLine._get_invoice_line_sequence(new=sequence,
                                                                                   old=line[2]['sequence'])
                    sequence += 1

        moves = self._create_account_invoices(invoice_vals_list, final)

        # 4) Some moves might actually be refunds: convert them if the total amount is negative
        # We do this after the moves have been created since we need taxes, etc. to know if the total
        # is actually negative or not
        if final and (moves_to_switch := moves.sudo().filtered(lambda m: m.amount_total < 0)):
            with self.env.protecting([moves._fields['team_id']], moves_to_switch):
                moves_to_switch.action_switch_move_type()
                self.invoice_ids._set_reversed_entry(moves_to_switch)

        for move in moves:
            if final:
                # Downpayment might have been determined by a fixed amount set by the user.
                # This amount is tax included. This can lead to rounding issues.
                # E.g. a user wants a 100€ DP on a product with 21% tax.
                # 100 / 1.21 = 82.64, 82.64 * 1,21 = 99.99
                # This is already corrected by adding/removing the missing cents on the DP invoice,
                # but must also be accounted for on the final invoice.

                delta_amount = 0
                for order_line in self.order_line:
                    if not order_line.is_downpayment:
                        continue
                    inv_amt = order_amt = 0
                    for invoice_line in order_line.invoice_lines:
                        sign = 1 if invoice_line.move_id.is_inbound() else -1
                        if invoice_line.move_id == move:
                            inv_amt += invoice_line.price_total * sign
                        elif invoice_line.move_id.state != 'cancel':  # filter out canceled dp lines
                            order_amt += invoice_line.price_total * sign
                    if inv_amt and order_amt:
                        # if not inv_amt, this order line is not related to current move
                        # if no order_amt, dp order line was not invoiced
                        delta_amount += inv_amt + order_amt

                if not move.currency_id.is_zero(delta_amount):
                    receivable_line = move.line_ids.filtered(
                        lambda aml: aml.account_id.account_type == 'asset_receivable')[:1]
                    product_lines = move.line_ids.filtered(
                        lambda aml: aml.display_type == 'product' and aml.is_downpayment)
                    tax_lines = move.line_ids.filtered(
                        lambda aml: aml.tax_line_id.amount_type not in (False, 'fixed'))
                    if tax_lines and product_lines and receivable_line:
                        line_commands = [Command.update(receivable_line.id, {
                            'amount_currency': receivable_line.amount_currency + delta_amount,
                        })]
                        delta_sign = 1 if delta_amount > 0 else -1
                        for lines, attr, sign in (
                                (product_lines, 'price_total', -1 if move.is_inbound() else 1),
                                (tax_lines, 'amount_currency', 1),
                        ):
                            remaining = delta_amount
                            lines_len = len(lines)
                            for line in lines:
                                if move.currency_id.compare_amounts(remaining, 0) != delta_sign:
                                    break
                                amt = delta_sign * max(
                                    move.currency_id.rounding,
                                    abs(move.currency_id.round(remaining / lines_len)),
                                )
                                remaining -= amt
                                line_commands.append(Command.update(line.id, {attr: line[attr] + amt * sign}))
                        move.line_ids = line_commands

            move.message_post_with_source(
                'mail.message_origin_link',
                render_values={'self': move, 'origin': move.line_ids.sale_line_ids.order_id},
                subtype_xmlid='mail.mt_note',
            )
        return moves

    # @api.onchange('order_line', 'order_line.product_uom_qty', 'order_line.product_id')
    # def _onchange_order_line_recalculate_package(self):
    #     """Recalculate manual line adjustments dynamically.
    #     - Rebalances only if new manual lines added or adjusted lines changed.
    #     - Keeps stable values for previously balanced lines.
    #     """
    #     if not self.package_id:
    #         return
    #
    #     order_lines = self.order_line
    #     package_lines = self.package_id.package_line_ids
    #
    #     # 1️⃣ Calculate total removed value from package lines
    #     package_price_map = {pl.product_id.id: pl.price_unit for pl in package_lines}
    #     existing_product_ids = order_lines.mapped('product_id.id')
    #
    #     removed_cost_total = sum(
    #         price for pid, price in package_price_map.items()
    #         if pid not in existing_product_ids
    #     )
    #
    #     if not removed_cost_total:
    #         for ln in order_lines.filtered(lambda l: not l.package_line_id):
    #             ln.manual_adjusted = False
    #         return
    #
    #     manual_lines = order_lines.filtered(lambda l: not l.package_line_id)
    #     if not manual_lines:
    #         return
    #
    #     # 3️⃣ Split manual lines into already adjusted and new/unadjusted
    #     adjusted_lines = manual_lines.filtered(lambda l: l.manual_adjusted)
    #     print(adjusted_lines,"ADJ")
    #     unadjusted_lines = manual_lines - adjusted_lines
    #     print(unadjusted_lines,"UNADDDDD")
    #
    #     # 4️⃣ Detect if any adjusted line was changed (qty or product)
    #     recalculated_adjusted_lines = adjusted_lines.filtered(
    #         lambda l: l._origin and (
    #                 l.product_uom_qty != l._origin.product_uom_qty or
    #                 l.product_id != l._origin.product_id
    #         )
    #     )
    #     print(recalculated_adjusted_lines,"asdasdad")
    #     # If some adjusted lines changed, unmark them for recalculation
    #     if recalculated_adjusted_lines:
    #         recalculated_adjusted_lines.manual_adjusted = False
    #         unadjusted_lines |= recalculated_adjusted_lines
    #         adjusted_lines -= recalculated_adjusted_lines
    #
    #     # 5️⃣ Compute how much cost is already allocated to adjusted lines
    #     already_allocated_cost = sum(
    #         (l.product_id.lst_price - l.price_unit) * l.product_uom_qty
    #         for l in adjusted_lines
    #     )
    #
    #     remaining_to_allocate = max(removed_cost_total - already_allocated_cost, 0.0)
    #     if remaining_to_allocate <= 0 or not unadjusted_lines:
    #         return
    #     print(remaining_to_allocate,"REMAINNN")
    #     # 6️⃣ Compute proportional allocation for unadjusted lines only
    #     unadjusted_original_totals = {
    #         ln.id: float_round(ln.product_id.lst_price * ln.product_uom_qty, 2)
    #         for ln in unadjusted_lines
    #     }
    #
    #     total_unadjusted_original = sum(unadjusted_original_totals.values())
    #     if total_unadjusted_original <= 0:
    #         return
    #
    #     remaining_balance = float_round(remaining_to_allocate, 2)
    #
    #     for i, ln in enumerate(unadjusted_lines, start=1):
    #         if remaining_balance <= 0:
    #             break
    #
    #         orig_total = unadjusted_original_totals[ln.id]
    #         proportion = orig_total / total_unadjusted_original
    #         line_adjustment = float_round(remaining_to_allocate * proportion, 2)
    #         line_adjustment = min(line_adjustment, remaining_balance)
    #
    #         unit_adjustment = line_adjustment / ln.product_uom_qty if ln.product_uom_qty > 0 else 0
    #         new_price_unit = max(ln.product_id.lst_price - unit_adjustment, 0)
    #
    #         ln.price_unit = new_price_unit
    #         ln.manual_adjusted = True
    #
    #         remaining_balance -= line_adjustment
    #         print(f"[PackageAdjust] Line {i}: price={ln.price_unit}, balance={remaining_balance}")
    #
    #     if remaining_balance > 0:
    #         print("⚠️ Remaining balance %s unallocated", remaining_balance)

    @api.onchange('order_line', 'order_line.product_uom_qty', 'order_line.product_id')
    def _onchange_order_line_recalculate_package(self):
        """Recalculate manual line adjustments dynamically.
        - Rebalances only if new manual lines added, adjusted lines changed, or adjusted lines removed.
        - Keeps stable values for previously balanced lines.
        """
        if not self.package_id:
            for line in self.order_line.filtered(lambda l: not l.package_line_id):
                line.manual_adjusted = False
                line.manual_discount_allocated = 0.0
                line.price_unit = line.product_id.lst_price
            return

        order_lines = self.order_line
        package_lines = self.package_id.package_line_ids

        package_price_map = {pl.product_id.id: pl.price_unit for pl in package_lines}
        current_product_ids = order_lines.mapped('product_id.id')

        removed_credit = sum(
            price for pid, price in package_price_map.items()
            if pid not in current_product_ids
        )
        removed_credit = float_round(removed_credit, 2)

        if removed_credit <= 0:
            for line in order_lines.filtered(lambda l: not l.package_line_id):
                line.manual_adjusted = False
                line.manual_discount_allocated = 0.0
                line.price_unit = line.product_id.lst_price
            return

        manual_lines = order_lines.filtered(lambda l: not l.package_line_id)
        if not manual_lines:
            return

        previously_adjusted = manual_lines.filtered('manual_adjusted')
        changed_or_removed = previously_adjusted.filtered(
            lambda l: l._origin and (
                    l.product_uom_qty != l._origin.product_uom_qty or
                    l.product_id != l._origin.product_id
            )
        )

        if changed_or_removed:
            for line in manual_lines:
                line.manual_adjusted = False
                line.manual_discount_allocated = 0.0

        remaining_credit = removed_credit

        for line in manual_lines:
            if line.manual_adjusted and remaining_credit <= 0.01:
                continue

            line.manual_discount_allocated = 0.0
            line.manual_adjusted = False

            list_subtotal = float_round(line.product_id.lst_price * line.product_uom_qty, 2)
            if list_subtotal <= 0:
                continue

            can_absorb = min(list_subtotal, remaining_credit)
            if can_absorb <= 0:
                break

            line.manual_discount_allocated = can_absorb
            line.manual_adjusted = True

            unit_discount = can_absorb / line.product_uom_qty if line.product_uom_qty else 0
            line.price_unit = max(line.product_id.lst_price - unit_discount, 0.0)

            remaining_credit -= can_absorb
            remaining_credit = float_round(remaining_credit, 2)

            if remaining_credit <= 0.01:
                break

        if remaining_credit > 0.01:
            print(f"[PackageAdjust] Warning: ₹{remaining_credit} credit left unabsorbed (precision)")


class SaleOrderLineInherit(models.Model):
    _inherit = 'sale.order.line'

    package_id = fields.Many2one('printer.package', 'Package')
    package_line_id = fields.Many2one('printer.package.line', 'Package')
    remarks = fields.Text('Remarks')
    at_type = fields.Selection(
        [('lamination', 'Lamination'), ('cover', 'Cover'), ('calendar', 'Calendar'),
         ('frame', 'Frame'), ('addons', 'Addons'), ('making', 'Making')],
        string='Type')
    check_order_group = fields.Boolean(related='order_id.check_order_group')
    package_at_type = fields.Selection(related='package_line_id.at_type')
    manual_adjusted = fields.Boolean('Manual Adjusted Line', default=False)
    product_price_user = fields.Float(string='Product Price', default=0.0)

    ######################################################################################################################

    manual_discount_allocated = fields.Float(
        string="Allocated Package Discount (Total)",
        default=0.0,
        help="Total monetary discount allocated from removed package items"
    )

    #####################################################################################################################@

    @api.onchange('product_id')
    def _onchange_block_product_open(self):
        if self.product_id:
            raise UserError(
                "Product selection is restricted. Please contact the administrator."
            )


    @api.constrains('at_type')
    def _check_package_line_at_type(self):
        for line in self:
            if line.package_line_id and line.package_line_id.at_type == 'making':
                if line._origin and line.package_line_id.at_type != line.at_type:
                    raise UserError("You cannot change the 'making' line type once it is set.")

    # @api.onchange('at_type')
    # def onchange_type(self):
    #     for i in self:
    #         if not i.at_type:
    #             self.at_product_template_id = False
    #             self.product_id = False
    #             self.product_uom_qty = False

    @api.depends('at_type')
    def get_product_tmpl(self):
        for rec in self:
            if rec.at_type:
                prod = self.env['product.product'].search([('at_type', '=', rec.at_type)])
                prod_ids = list(set(prod.mapped('at_product_template_id').ids))
                rec.at_template_domain = [('id', 'in', prod_ids)]
            else:
                rec.at_template_domain = []

    at_template_domain = fields.Char(compute=get_product_tmpl)

    at_product_template_id = fields.Many2one('product.template', 'Product Template', domain=get_product_tmpl)
    package_split_percentage = fields.Float(
        'Split Percentage',
        compute='_compute_split_percentage',
        inverse='_inverse_split_percentage',
        store=True
    )
    actual_package_price = fields.Float(related='package_line_id.price_unit', string='Actual Package Rate')

    @api.depends('package_id', 'package_line_id', 'order_id.order_line.package_line_id')
    def _compute_split_percentage(self):
        for line in self:
            if line.package_id and line.package_line_id:
                package_lines = line.order_id.order_line.filtered(
                    lambda l: l.package_id == line.package_id and l.package_line_id
                )
                if package_lines:
                    line.package_split_percentage = 100.0 / len(package_lines)
                else:
                    line.package_split_percentage = 0
            else:
                line.package_split_percentage = 0

    def _inverse_split_percentage(self):
        """Allow manual percentage override with validation"""
        for line in self:
            if line.package_id and line.package_line_id and line.package_split_percentage:
                continue

    def _prepare_base_line_for_taxes_computation(self, **kwargs):
        """ Convert the current record to a dictionary in order to use the generic taxes computation method
        defined on account.tax.

        :return: A python dictionary.
        """
        self.ensure_one()
        return self.env['account.tax']._prepare_base_line_for_taxes_computation(
            self,
            **{
                'tax_ids': self.tax_id,
                'quantity': self.product_uom_qty if not self.package_id else 1,
                'partner_id': self.order_id.partner_id,
                'currency_id': self.order_id.currency_id or self.order_id.company_id.currency_id,
                'rate': self.order_id.currency_rate,
                **kwargs,
            },
        )

    @api.onchange('package_split_percentage')
    def _onchange_split_percentage(self):
        self._compute_price_from_package()

    @api.depends('package_id.package_price', 'package_split_percentage')
    def _compute_price_from_package(self):
        for line in self:
            if line.package_id and line.package_line_id:
                line.price_unit = line.package_id.package_price * (line.package_split_percentage / 100.0)

    @api.onchange('at_type')
    def onchange_at_type(self):
        for i in self:
            if i.at_type:
                i.at_product_template_id = False
                i.product_id = False
                i.name = False

    @api.onchange('product_id')
    def onchange_product_amount(self):
        if self.product_id:
            self.update({
                'product_price_user': self.price_unit
            })

    def unlink(self):
        affected_data = {}
        for line in self:
            if line.at_type == 'making' and line.package_id:
                raise UserError('You Cannot Delete Making Type lines')

            if line.package_id:
                if line.package_id not in affected_data:
                    affected_data[line.package_id] = line.order_id

            if line.manual_adjusted or line.package_line_id:
                line.order_id._onchange_order_line_recalculate_package()

            manual_lines = self.search([('order_id', '=', line.order_id.id), ('manual_adjusted', '=', True)])
            if line.package_line_id and manual_lines:
                raise UserError('Please Remove all the manual entered lines before deleting the package line again..')

        result = super().unlink()

        for package, order in affected_data.items():
            remaining_lines = self.env['sale.order.line'].search([
                ('order_id', '=', order.id),
                ('package_id', '=', package.id),
                ('id', 'not in', self.ids)
            ])

            if remaining_lines:
                new_percent = 100.0 / len(remaining_lines)

                new_percent = round(new_percent, 2)

                remaining_lines.write({'package_split_percentage': new_percent})

                for line in remaining_lines:
                    line._compute_price_from_package()
                    line.price_subtotal = round(line.price_subtotal, 2)  # Round price
                    line.price_total = round(line.price_total, 2)  # Round total

                total_percentage = sum(line.package_split_percentage for line in remaining_lines)
                if total_percentage != 100.0:
                    last_line = remaining_lines[-1]
                    last_line.write({'package_split_percentage': round(
                        100.0 - (total_percentage - last_line.package_split_percentage), 2)})
                    last_line._compute_price_from_package()

            return result


class AddonsConf(models.Model):
    _name = 'addons.conf'
    _description = 'Addons Configuration'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    order_id = fields.Many2one('sale.order', 'Sale')
    product_id = fields.Many2one(
        comodel_name='product.product',
        string="Product",
        change_default=True, ondelete='restrict', index='btree_not_null',
        domain="[('sale_ok', '=', True)]")

    product_template_id = fields.Many2one(
        string="Product Template",
        comodel_name='product.template',
        compute='_compute_product_template_id',
        readonly=False,
        search='_search_product_template_id',
        # previously related='product_id.product_tmpl_id'
        # not anymore since the field must be considered editable for product configurator logic
        # without modifying the related product_id when updated.
        domain=[('sale_ok', '=', True)])

    name = fields.Text(
        string="Description", required=True)

    product_uom_qty = fields.Float(
        string="Quantity",
        digits='Product Unit of Measure', default=1.0,
    )
    product_uom_category_id = fields.Many2one(related='product_id.uom_id.category_id', depends=['product_id'])

    product_uom = fields.Many2one(
        comodel_name='uom.uom',
        string="Unit of Measure",
        compute='_compute_product_uom',
        store=True, readonly=False, precompute=True, ondelete='restrict',
        domain="[('category_id', '=', product_uom_category_id)]")

    price_unit = fields.Float(
        string="Unit Price",
        related='product_id.list_price',
        digits='Product Price',
        store=True, readonly=False, required=True)

    price_subtotal = fields.Monetary(
        string="Subtotal",
        compute='compute_subtotal',
        store=True)

    currency_id = fields.Many2one(
        comodel_name='res.currency',
        string="Currency",
        required=True,
        default=lambda self: self.env.company.currency_id,
    )
    package_id = fields.Many2one('printer.package', 'Printer Package')

    @api.depends('product_id')
    def _compute_product_uom(self):
        for line in self:
            if not line.product_uom or (line.product_id.uom_id.id != line.product_uom.id):
                line.product_uom = line.product_id.uom_id

    @api.depends('product_uom_qty', 'price_unit')
    def compute_subtotal(self):
        for i in self:
            if i.product_uom_qty and i.price_unit:
                i.price_subtotal = i.product_uom_qty * i.price_unit

    @api.depends('product_id')
    def _compute_product_template_id(self):
        for line in self:
            line.product_template_id = line.product_id.product_tmpl_id

    def _search_product_template_id(self, operator, value):
        return [('product_id.product_tmpl_id', operator, value)]

    @api.onchange('product_id')
    def onchange_product_id(self):
        for i in self:
            if i.product_id:
                i.name = i.product_id.name

    def _prepare_invoice_line(self, **optional_values):
        """Prepare the values to create the new invoice line for a sales order line.

        :param optional_values: any parameter that should be added to the returned invoice line
        :rtype: dict
        """
        self.ensure_one()
        res = {
            'display_type': 'product',
            'name': self.env['account.move.line']._get_journal_items_full_name(self.name, self.product_id.display_name),
            'product_id': self.product_id.id,
            'product_uom_id': self.product_uom.id,
            'quantity': self.product_uom_qty,
            'price_unit': self.price_unit,
        }
        return res
