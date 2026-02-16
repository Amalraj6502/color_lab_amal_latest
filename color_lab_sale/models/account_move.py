from odoo import models, fields


class AccountMove(models.Model):
    _inherit = 'account.move'

    def default_cash_round_method(self):
        round_method = self.env['account.cash.rounding'].search([], limit=1)
        if round_method:
            return round_method

    agent_id = fields.Many2one('agent.form', 'Agent', domain=[('state', '=', 'confirm')], tracking=True)
    invoice_cash_rounding_id = fields.Many2one(
        comodel_name='account.cash.rounding',
        string='Cash Rounding Method', default=default_cash_round_method,
        help='Defines the smallest coinage of the currency that can be used to pay by cash.',
    )


