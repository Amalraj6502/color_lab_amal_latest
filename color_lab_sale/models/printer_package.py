from odoo import models, fields, api


class PrinterPackage(models.Model):
    _name = 'printer.package'
    _description = 'Printer Package Configurations'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    def _default_currency_id(self):
        return self.env.user.company_id.currency_id

    name = fields.Char('Package Name', tracking=True)
    partner_ids = fields.Many2many('res.partner', 'package_partners_sale_rel', string='Partners', tracking=True)
    agent_ids = fields.Many2many('agent.form', 'package_agents_sale_rel', string='Agents', tracking=True)
    package_line_ids = fields.One2many('printer.package.line', 'package_id', string='Package Lines')
    printer_id = fields.Many2one('printer.conf', 'Printer', tracking=True)
    layouts = fields.Selection(selection=[('book', 'Book'), ('flat', 'Flat')])
    at_page = fields.Integer('Number Of Sheets', tracking=True)
    title = fields.Char('Title')
    description = fields.Text('Description', tracking=True)

    state = fields.Selection([('draft', 'Draft'), ('approve', 'Approved')], string='Status', default='draft',
                             tracking=True)
    date_start = fields.Date('Date Start', tracking=True)
    date_end = fields.Date('Date end', tracking=True)
    type = fields.Selection(
        [('photobook', 'Photobook'), ('package', 'Package'), ('print', 'Print'), ('repair', 'Repair'),
         ('reework', 'Reework'), ('laser', 'Laser')], string='Type', default='photobook')
    agent_customer_domain = fields.Binary(compute='_onchange_agent_ids')
    package_price = fields.Monetary('Package Price', compute='compute_package_price', readonly=False, store=True)
    currency_id = fields.Many2one('res.currency', string='Currency', required=True,
                                  default=lambda self: self._default_currency_id())

    at_product = fields.Many2one('at.product', string='Main Product', tracking=True)
    at_size = fields.Char('Size', related='at_product.size')
    # at_page = fields.Integer('Page')
    at_rate = fields.Float('Rate', compute='compute_at_rate', store=True)
    is_warning_required = fields.Boolean('Is Warning Required?', default=True,
                                         help='Enable if you want to show a restriction in the sale order addons configuration.',
                                         tracking=True)
    max_addon_size = fields.Integer('Max Addons Size', default=9, tracking=True)
    is_mini_book_required = fields.Boolean('Mini Book Required')

    # MINI BOOK CONFIGURATIONS

    mini_book_count = fields.Integer('Mini Book Count', default=1, tracking=True)
    mini_book_conf = fields.Many2one('mini.book.conf', 'Mini Book Configuration', tracking=True)
    mini_book_height = fields.Float('Height(cm)', tracking=True)
    mini_book_weight = fields.Float('Weight(cm)', tracking=True)
    mini_book_length = fields.Float('Length(cm)', tracking=True)
    mini_book_width = fields.Float('Width(cm)', tracking=True)
    mini_book_amount = fields.Monetary('Amount', tracking=True)
    mini_book_remarks = fields.Text('Remarks', tracking=True)
    mini_book_qty = fields.Float('Quantity', tracking=True)

    mini_total = fields.Monetary('Minibook Total', compute='compute_minitotal')

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
                })
            else:
                i.mini_book_height = False
                i.mini_book_weight = False
                i.mini_book_length = False
                i.mini_book_width = False
                i.mini_book_amount = False
                i.mini_book_remarks = False

    @api.depends('mini_book_amount', 'mini_book_qty')
    def compute_minitotal(self):
        for i in self:
            if i.mini_book_amount and i.mini_book_qty:
                i.mini_total = i.mini_book_amount * i.mini_book_qty
            else:
                i.mini_total = 0

    @api.depends('at_product', 'at_page')
    def compute_at_rate(self):
        for i in self:
            if i.at_product and i.at_page:
                i.at_rate = i.at_product.rate * i.at_page
            else:
                if i.at_product:
                    i.at_rate = i.at_product.rate
                else:
                    i.at_rate = 0

    @api.depends('package_line_ids')
    def compute_package_price(self):
        for i in self:
            if i.package_line_ids:
                i.package_price = sum(i.package_line_ids.mapped('price_subtotal'))
            else:
                i.package_price = 0

    def action_approve(self):
        self.state = 'approve'

    def reset_to_draft(self):
        self.state = 'draft'

    @api.onchange('agent_ids')
    def _onchange_agent_ids(self):
        for rec in self:
            if rec.agent_ids:
                agent_partner_ids = rec.agent_ids.mapped('partner_id.id')
                partners = self.env['res.partner'].search([
                    ('parent_id', 'in', agent_partner_ids),
                    ('is_agent_customer', '=', True)
                ])
                rec.agent_customer_domain = [('id', 'in', partners.ids)]
            else:
                rec.agent_customer_domain = [(5, 0, 0)]


class PrinterPackageLine(models.Model):
    _name = 'printer.package.line'
    _description = 'Printer Package Lines Configurations'

    at_type = fields.Selection(
        [('lamination', 'Lamination'), ('cover', 'Cover'), ('calendar', 'Calendar'),
         ('frame', 'Frame'), ('addons', 'Addons'), ('making', 'Making')],
        string='Type')
    at_product_template_id = fields.Many2one('product.template', 'Product Template')

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
