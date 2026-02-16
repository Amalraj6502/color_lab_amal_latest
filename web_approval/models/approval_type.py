from odoo import fields, models


class ApprovalTemplateType(models.Model):
    _name = 'approval.template.type'
    _description = 'Approval Type'
    _order = "id desc"

    name = fields.Char('Type Name', required=True)
    res_model_id = fields.Many2one('ir.model', string='Model', required=True, ondelete='cascade')
    res_model_name = fields.Char(
        related='res_model_id.model', string='Model Name', readonly=True, store=True)
