# -*- coding: utf-8 -*-
import base64

from odoo import models, fields, api, tools
from odoo.exceptions import UserError
from odoo.tools.misc import file_open


@api.model
def _lang_get(self):
    return self.env['res.lang'].get_installed()


class AgentCustomerForm(models.Model):
    _name = 'agent.customer.form'
    _description = 'Agent Customer'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'avatar.mixin']

    @api.model
    def _default_image(self):
        return base64.b64encode(file_open('color_lab_sale/static/img/agent.jpg', 'rb').read())

    def _default_category(self):
        return self.env['res.partner.category'].browse(self._context.get('category_id'))

    name = fields.Char('Agent Name')
    # agent_type = fields.Selection(
    #     selection=[('commission_agent', 'Commission Agent'), ('staff_agent', 'Staff Agent'), ('branch', 'Branch')])
    street = fields.Char()
    street2 = fields.Char()
    zip = fields.Char(change_default=True)
    city = fields.Char()
    state_id = fields.Many2one("res.country.state", string='State', ondelete='restrict',
                               domain="[('country_id', '=?', country_id)]")
    country_id = fields.Many2one('res.country', string='Country', ondelete='restrict')
    country_code = fields.Char(related='country_id.code', string="Country Code")
    partner_latitude = fields.Float(string='Geo Latitude', digits=(10, 7))
    partner_longitude = fields.Float(string='Geo Longitude', digits=(10, 7))
    email = fields.Char()
    email_formatted = fields.Char(
        'Formatted Email', compute='_compute_email_formatted',
        help='Format email address "Name <email@domain>"')
    phone = fields.Char()
    mobile = fields.Char()
    image_1920 = fields.Image(default=_default_image)
    vat = fields.Char(string='Tax ID', index=True,
                      help="The Tax Identification Number. Values here will be validated based on the country format. You can use '/' to indicate that the partner is not subject to tax.")

    category_id = fields.Many2many('res.partner.category', column1='partner_id',
                                   column2='category_id', string='Tags', default=_default_category)
    lang = fields.Selection(_lang_get, string='Language',
                            help="All the emails and documents sent to this contact will be translated in this language.")
    title = fields.Many2one('res.partner.title')
    website = fields.Char('Website Link')
    partner_id = fields.Many2one('res.partner', 'Partner')
    company_id = fields.Many2one('res.company', required=True, readonly=True, default=lambda self: self.env.company)
    color = fields.Integer(string='Color Index', default=0)
    parent_id = fields.Many2one('agent.form', string='Agent Form ID', index=True)
    parent_name = fields.Char(related='parent_id.name', readonly=True, string='Parent name')
    active = fields.Boolean('Active', default=True)
    type = fields.Selection(
        [('customer', 'Customer'),
         ('other', 'Other Address'),
         ], string='Address Type',
        default='customer')
    comment = fields.Html(string='Notes')
    user_id = fields.Many2one(
        'res.users', string='User Name',
        help='The internal user in charge of this customer.')
    state = fields.Selection([('draft', 'Draft'), ('confirm', 'Confirm')], string='Status', default='draft',
                             index='btree_not_null',
                             tracking=True)

    def action_confirm(self):
        if not self.partner_id and self.parent_id.partner_id.id:
            new_partner_id = self.env['res.partner'].sudo().create({
                'is_company': False,
                'type': 'contact',
                'name': self.name,
                'email': self.email,
                'phone': self.phone,
                'mobile': self.mobile,
                'street': self.street,
                'street2': self.street2,
                'zip': self.zip,
                'city': self.city,
                'state_id': self.state_id.id,
                'country_id': self.country_id.id,
                'partner_latitude': self.partner_latitude,
                'email': self.email,
                'image_1920': self.image_1920,
                'vat': self.vat,
                'category_id': self.category_id.id,
                'lang': self.lang,
                'title': self.title.id,
                'website': self.website,
                'parent_id': self.parent_id.partner_id.id,
                'comment': self.comment,
                'agent_customer_id': self.id,
                'agent_id': self.parent_id.id,
                'is_agent_customer': True,
                'customer_rank': 1,
            })
            self.partner_id = new_partner_id.id
            self.state = 'confirm'
        else:
            raise UserError('Please confirm the agent first')

    def show_partner(self):
        action = {
            'name': 'Customer Reference',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'res.partner',
            'res_id': self.partner_id.id,
            'target': 'current'
        }
        return action

    @api.depends('name', 'email')
    def _compute_email_formatted(self):
        """ Compute formatted email for partner, using formataddr. Be defensive
        in computation, notably

          * double format: if email already holds a formatted email like
            'Name' <email@domain.com> we should not use it as it to compute
            email formatted like "Name <'Name' <email@domain.com>>";
          * multi emails: sometimes this field is used to hold several addresses
            like email1@domain.com, email2@domain.com. We currently let this value
            untouched, but remove any formatting from multi emails;
          * invalid email: if something is wrong, keep it in email_formatted as
            this eases management and understanding of failures at mail.mail,
            mail.notification and mailing.trace level;
          * void email: email_formatted is False, as we cannot do anything with
            it;
        """
        self.email_formatted = False
        for partner in self:
            emails_normalized = tools.email_normalize_all(partner.email)
            if emails_normalized:
                # note: multi-email input leads to invalid email like "Name" <email1, email2>
                # but this is current behavior in Odoo 14+ and some servers allow it
                partner.email_formatted = tools.formataddr((
                    partner.name or u"False",
                    ','.join(emails_normalized)
                ))
            elif partner.email:
                partner.email_formatted = tools.formataddr((
                    partner.name or u"False",
                    partner.email
                ))
