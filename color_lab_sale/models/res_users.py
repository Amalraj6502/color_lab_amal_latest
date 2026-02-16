from odoo import models, fields, api, tools, _


class User(models.Model):
    _inherit = ['res.users']

    create_agent = fields.Boolean(store=False, default=False, copy=False,
                                     string="Technical field, whether to create an Agent")
    create_agent_id = fields.Many2one('agent.form', store=False, copy=False,
                                         string="Technical field, bind user to this Agent on create")
