from collections import defaultdict

from odoo import models, fields, api


class PartnerInherit(models.Model):
    _inherit = 'res.partner'

    unreconciled_aml_ids = fields.One2many('account.move.line', compute='_compute_total_due', readonly=False)
    total_due = fields.Monetary(
        compute='_compute_total_due',
        groups='account.group_account_readonly,account.group_account_invoice')
    total_overdue = fields.Monetary(
        compute='_compute_total_due',
        groups='account.group_account_readonly,account.group_account_invoice')
    is_agent_customer = fields.Boolean('Is Agent Customer', default=False)
    agent_customer_id = fields.Many2one('agent.customer.form', 'Agent Customer')
    agent_id = fields.Many2one('agent.form', 'Agent')

    def _get_unreconciled_aml_domain(self):
        return [
            ('reconciled', '=', False),
            ('account_id.deprecated', '=', False),
            ('account_id.account_type', '=', 'asset_receivable'),
            ('parent_state', '=', 'posted'),
            ('partner_id', 'in', self.ids),
            ('company_id', 'child_of', self.env.company.id),
        ]

    @api.depends('invoice_ids')
    @api.depends_context('company', 'allowed_company_ids')
    def _compute_total_due(self):
        due_data = defaultdict(float)
        overdue_data = defaultdict(float)
        unreconciled_aml_ids = defaultdict(list)
        for overdue, partner, amount_residual_sum, aml_ids in self.env['account.move.line']._read_group(
                domain=self._get_unreconciled_aml_domain(),
                groupby=['partner_id'],
                aggregates=['amount_residual:sum', 'id:array_agg'],
        ):
            unreconciled_aml_ids[partner] += aml_ids
            due_data[partner] += amount_residual_sum
            if overdue:
                overdue_data[partner] += amount_residual_sum

        for partner in self:
            partner.total_due = due_data.get(partner, 0.0)
            partner.total_overdue = overdue_data.get(partner, 0.0)
            partner.unreconciled_aml_ids = self.env['account.move.line'].browse(unreconciled_aml_ids.get(partner, []))

    @api.depends('parent_id')
    def _compute_display_name(self):
        """ override function for removing the parent with the name in customer and other customer forms
        """
        for category in self:
            category.display_name = category.name
