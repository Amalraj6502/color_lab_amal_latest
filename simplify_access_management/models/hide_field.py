from odoo import fields, models, api, _
from lxml import etree


class hide_field(models.Model):
    _name = 'hide.field'
    _description = "Fields Rights"

    access_management_id = fields.Many2one('access.management', string='Access Management')
    model_id = fields.Many2one('ir.model', 'Model')

    field_id = fields.Many2many(
        'ir.model.fields',  # The target model
        'hide_field_ir_model_fields_rel',  # Unique relation table name for this Many2many field
        'hide_field_id',  # Column name for the current model (hide.field)
        'ir_field_id',  # Column name for the target model (ir.model.fields)
        string='Field'
    )

    invisible = fields.Boolean('Invisible')
    readonly = fields.Boolean('Read-Only')
    required = fields.Boolean('Required')
    external_link = fields.Boolean('Remove External Link')
