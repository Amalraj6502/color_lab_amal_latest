from odoo import fields, models, api, _
from odoo.exceptions import UserError
from odoo.http import request


class access_management(models.Model):
    _name = 'access.management'
    _description = "Access Management"

    name = fields.Char('Name')
    report_action_ids = fields.Integer('field id')
    field_id = fields.Many2many(
        'ir.model.fields',
        'access_management_ir_model_fields_rel',
        'access_management_id',
        'ir_field_id',
        string='Access Management Field'
    )
    btn_store_model_nodes_ids = fields.Many2many(
        'ir.ui.view',
        'access_management_store_model_nodes_rel',
        'access_management_id',
        'store_model_nodes_id',
        string='Button Store Model Nodes'
    )

    invisible = fields.Boolean('Invisible')
    readonly = fields.Boolean('Read-Only')
    required = fields.Boolean('Required')
    domain = fields.Char(string='Filter', default='[]')
    read_right = fields.Boolean('Read', default=True)
    create_right = fields.Boolean('Create')
    write_right = fields.Boolean('Write')
    delete_right = fields.Boolean('Delete')
    external_link = fields.Boolean('Remove External Link')
    server_action_ids = fields.Integer('server')
    view_data_ids = fields.Integer('view data ids')
    restrict_create = fields.Boolean('Hide Create')
    restrict_edit = fields.Boolean('Hide Edit')
    restrict_delete = fields.Boolean('Hide Delete')
    restrict_archive_unarchive = fields.Boolean('Hide Archive/Unarchive')
    restrict_duplicate = fields.Boolean('Hide Duplicate')
    restrict_chatter = fields.Boolean('Hide Chatter')
    restrict_spreadsheet = fields.Boolean('Hide Spreadsheet')
    restrict_export = fields.Boolean('Hide Export')
    restrict_import = fields.Boolean('Hide Import')
    readonly = fields.Boolean('Read-Only')
    user_ids = fields.Many2many('res.users', 'access_management_users_rel_ah', 'access_management_id', 'user_id',
                                'Users')
    readonly = fields.Boolean('Read-Only')
    active = fields.Boolean('Active', default=True)

    hide_menu_ids = fields.Many2many('menu.item', 'access_management_menu_rel_ah', 'access_management_id', 'menu_id',
                                     'Hide Menu')
    hide_field_ids = fields.One2many('hide.field', 'access_management_id', string='Hide Field', copy=True)
    remove_action_ids = fields.One2many('remove.action', 'access_management_id', 'Remove Action', copy=True)

    access_domain_ah_ids = fields.One2many('access.domain.ah', 'access_management_id', 'Access Domain', copy=True)
    hide_view_nodes_ids = fields.One2many('hide.view.nodes', 'access_management_id', 'Button/Tab Access', copy=True)

    self_module_menu_ids = fields.Many2many('ir.ui.menu', 'access_management_ir_ui_self_module_menu',
                                            'access_management_id', 'menu_id', 'Self Module Menu',
                                            default=lambda self: self.env.ref(
                                                'simplify_access_management.main_menu_simplify_access_management'))
    # self_model_ids = fields.Many2many('ir.model', 'access_management_ir_model_self', 'access_management_id', 'model_id',
    #                                   'Self Model', compute="_get_self_module_info")
    total_rules = fields.Integer('Access Rules', compute="_count_total_rules")

    # Chatter
    hide_chatter_ids = fields.One2many('hide.chatter', 'access_management_id', 'Hide Chatter', copy=True)

    hide_chatter = fields.Boolean('Hide Chatter')
    hide_send_mail = fields.Boolean('Hide Send Message')
    hide_log_notes = fields.Boolean('Hide Log Notes')
    hide_schedule_activity = fields.Boolean('Hide Schedule Activity')

    hide_export = fields.Boolean()
    hide_import = fields.Boolean()
    hide_spreadsheet = fields.Boolean()
    hide_add_property = fields.Boolean()
    disable_login = fields.Boolean('Disable Login')

    disable_debug_mode = fields.Boolean('Disable Developer Mode')

    company_ids = fields.Many2many('res.company', 'access_management_comapnay_rel', 'access_management_id',
                                   'company_id', 'Companies', required=True, default=lambda self: self.env.company)

    hide_filters_groups_ids = fields.One2many('hide.filters.groups', 'access_management_id', 'Hide Filters/Group By',
                                              copy=True)
    model_id = fields.Many2one(
        'ir.model', string='Model', index=True,  ondelete='cascade')
    node_option = fields.Selection([('filter', 'Filter'), ('group', 'Groups')], string="Node Option")
    page_store_model_nodes_ids = fields.Many2many(
        'store.model.nodes',
        'page_access_management_store_model_nodes_rel',  # Changed table name here
        'hide_id', 'store_id',
        string='Hide Tab/Page',
        domain="[('node_option','=','page')]"
    )
    link_store_model_nodes_ids = fields.Many2many(
        'store.model.nodes',
        'link_access_management_store_model_nodes_rel',  # Renamed table
        'access_mgmt_id',  # Changed column name for access management model
        'store_id',
        string='Hide Kanban Link',
        domain="[('node_option','=','link')]"
    )
    filters_store_model_nodes_ids = fields.Many2many(
        'store.filters.groups',
        'filters_access_management_store_filters_groups_rel',  # Change relation table name
        'access_id',  # Update column names to avoid conflict
        'store_id',
        string='Access Management Filters',
        domain="[('node_option','=','filter')]"
    )
    groups_store_model_nodes_ids = fields.Many2many(
        'store.filters.groups',
        'groups_access_management_store_filters_groups_rel',  # Change relation table name
        'access_id',  # Update column names to avoid conflict
        'store_id',
        string='Access Management Groups',
        domain="[('node_option','=','group')]"
    )

    def _postprocess_tag_page(self, node, name_manager, node_info):
        # Hide Any Notebook Page
        postprocessor = getattr(super(ir_ui_view, self), '_postprocess_tag_page', False)
        if postprocessor:
            super(ir_ui_view, self)._postprocess_tag_page(node, name_manager, node_info)

        hide = None
        hide_tab_obj = self.env['hide.view.nodes']
        hide_tab_ids = hide_tab_obj.sudo().search([('access_management_id.company_ids', 'in', self.env.company.id),
                                                   ('model_id.model', '=', name_manager.model._name),
                                                   ('access_management_id.active', '=', True),
                                                   ('access_management_id.user_ids', 'in', self._uid)])
        # translation_obj = self.env['ir.translation']
        # Filtered with same env user and current model
        page_store_model_nodes_ids = hide_tab_ids.mapped('page_store_model_nodes_ids')
        if page_store_model_nodes_ids:

            for tab in page_store_model_nodes_ids:
                attribute_string = tab.attribute_string
                if tab.lang_code != self.env.lang:
                    field = self.env['ir.ui.view']._fields['arch_db']
                    translation_dictionary = field.get_translation_dictionary(
                        self.with_context(lang=tab.lang_code).arch_db,
                        {self.env.lang: self.with_context(lang=self.env.lang)['arch_db']})
                    attribute_string = translation_dictionary[attribute_string][self.env.lang]
                if attribute_string == node.get('string'):
                    # if node.get('name'):
                    # if tab.attribute_name == node.get('name'):
                    hide = [tab]
                    break
                    # else:
                    #     hide = [tab]
                    #     break
        if hide:
            node.set('invisible', '1')
            if 'attrs' in node.attrib.keys() and node.attrib['attrs']:
                del node.attrib['attrs']

            node_info['invisible'] = True

        return None

    def _postprocess_tag_button(self, node, name_manager, node_info):
        # Hide Any Button
        postprocessor = getattr(super(ir_ui_view, self), '_postprocess_tag_button', False)
        if postprocessor:
            super(ir_ui_view, self)._postprocess_tag_button(node, name_manager, node_info)

        hide = None
        hide_button_obj = self.env['hide.view.nodes']
        hide_button_ids = hide_button_obj.sudo().search(
            [('access_management_id.company_ids', 'in', self.env.company.id),
             ('model_id.model', '=', name_manager.model._name), ('access_management_id.active', '=', True),
             ('access_management_id.user_ids', 'in', self._uid)])

        # Filtered with same env user and current model
        btn_store_model_nodes_ids = hide_button_ids.mapped('btn_store_model_nodes_ids')
        # translation_obj = self.env['ir.translation']
        if btn_store_model_nodes_ids:
            for btn in btn_store_model_nodes_ids:
                if btn.attribute_name == node.get('name'):
                    # if node.get('string'):
                    #     # if translation_obj._get_source(None, ('model_terms',), self.env.lang, btn.attribute_string, None) == node.get('string'):
                    #     if _(btn.attribute_string) == node.get('string'):
                    hide = [btn]
                    break
                    # else:
                    #     hide = [btn]
                    #     break
        if hide:
            node.set('invisible', '1')
            if 'attrs' in node.attrib.keys() and node.attrib['attrs']:
                del node.attrib['attrs']
            node_info['invisible'] = True

    def _store_btn_data(self, btn, smart_button=False, smart_button_string=False):
        # string_value is used in case of kanban view button store,
        string_value = 'string_value' in self._context.keys() and self._context['string_value'] or False

        store_model_button_obj = self.env['store.model.nodes']
        name = btn.get('string') or string_value
        if smart_button:
            name = smart_button_string
        store_model_button_obj.create({
            'model_id': self.model_id.id,
            'node_option': 'button',
            'attribute_name': btn.get('name'),
            'attribute_string': name,
            'button_type': btn.get('type'),
            'is_smart_button': smart_button,
            'lang_code': self.env.lang,
        })

    def _count_total_rules(self):
        for rec in self:
            rule = 0
            rule = rule + len(rec.hide_menu_ids) + len(rec.hide_field_ids) + len(rec.remove_action_ids) + len(
                rec.access_domain_ah_ids) + len(rec.hide_view_nodes_ids)
            rec.total_rules = rule

    def action_show_rules(self):
        pass

    # def _get_self_module_info(self):
    #     access_menu_id = self.env.ref('simplify_access_management.main_menu_simplify_access_management')
    #     model_list = ['access.management', 'access.domain.ah', 'action.data', 'hide.field', 'hide.view.nodes',
    #                   'store.model.nodes', 'remove.action', 'view.data']
    #     models_ids = self.env['ir.model'].search([('model', 'in', model_list)])
    #     for rec in self:
    #         rec.self_module_menu_ids = False
    #         rec.self_model_ids = False
    #         if access_menu_id:
    #             rec.self_module_menu_ids = [(6, 0, access_menu_id.ids)]
    #         if models_ids:
    #             rec.self_model_ids = [(6, 0, models_ids.ids)]

    def toggle_active_value(self):
        for record in self:
            record.write({'active': not record.active})
        return True

    @api.model_create_multi
    def create(self, vals_list):
        res = super(access_management, self).create(vals_list)
        # for user in self.env['res.users'].sudo().search([('share','=',False)]):
        # user.clear_caches()
        # self.clear_caches()
        request.registry.clear_cache()
        for record in res:
            if record.readonly:
                for user in record.user_ids:
                    if user.has_group('base.group_system') or user.has_group('base.group_erp_manager'):
                        raise UserError(_('Admin user can not be set as a read-only..!'))
        return res

    def unlink(self):
        res = super(access_management, self).unlink()
        # self.clear_caches()
        request.env.registry.clear_cache()
        # for user in self.env['res.users'].sudo().search([('share','=',False)]):
        #     user.clear_caches()
        return res

    def write(self, vals):
        res = super(access_management, self).write(vals)

        if self.readonly:
            for user in self.user_ids:
                if user.has_group('base.group_system') or user.has_group('base.group_erp_manager'):
                    raise UserError(_('Admin user can not be set as a read-only..!'))
        # for user in self.env['res.users'].sudo().search([('share','=',False)]):
        #     user.clear_caches()
        # self.clear_caches()
        request.env.registry.clear_cache()
        return res

    def get_remove_options(self, model):
        restrict_export = self.env['access.management'].search([('company_ids', 'in', self.env.company.id),
                                                                ('active', '=', True),
                                                                ('user_ids', 'in', self.env.user.id),
                                                                ('hide_export', '=', True)], limit=1).id
        remove_action = self.env['remove.action'].sudo().search(
            [('access_management_id.company_ids', 'in', self.env.company.id),
             ('access_management_id', 'in', self.env.user.access_management_ids.ids), ('model_id.model', '=', model)])
        options = []
        added_export = False
        if restrict_export:
            options.append(_('Export'))
            added_export = True

        for action in remove_action:
            if not added_export and action.restrict_export:
                options.append(_('Export'))
            if action.restrict_archive_unarchive:
                options.append(_('Archive'))
                options.append(_('Unarchive'))
            if action.restrict_duplicate:
                options.append(_('Duplicate'))
        return options

    @api.model
    def get_chatter_hide_details(self, user_id, company_id, model=False):
        hide_send_mail = True
        hide_log_notes = True
        hide_schedule_activity = True

        access_ids = self.search([('user_ids', 'in', user_id), ('company_ids', 'in', company_id)])
        for access in access_ids:
            if access.hide_chatter:
                hide_send_mail = False
                hide_log_notes = False
                hide_schedule_activity = False
                break

            if access.hide_send_mail:
                hide_send_mail = False

            if access.hide_log_notes:
                hide_log_notes = False

            if access.hide_schedule_activity:
                hide_schedule_activity = False

        if model and hide_send_mail or hide_log_notes or hide_schedule_activity:
            hide_ids = self.env['hide.chatter'].search([('access_management_id.company_ids', 'in', company_id),
                                                        ('access_management_id.active', '=', True),
                                                        ('access_management_id.user_ids', 'in', user_id),
                                                        ('model_id.model', '=', model)])

            if hide_ids:
                if hide_send_mail and hide_ids.filtered(lambda x: x.hide_send_mail):
                    hide_send_mail = False

                if hide_log_notes and hide_ids.filtered(lambda x: x.hide_log_notes):
                    hide_log_notes = False

                if hide_schedule_activity and hide_ids.filtered(lambda x: x.hide_schedule_activity):
                    hide_schedule_activity = False

        return {
            'hide_send_mail': hide_send_mail,
            'hide_log_notes': hide_log_notes,
            'hide_schedule_activity': hide_schedule_activity
        }

    def is_spread_sheet_available(self, action_model, action_id):
        model = self.env[action_model].sudo().browse(action_id).res_model
        if self.search([('user_ids', 'in', self.env.user.id), ('company_ids', 'in', self.env.company.id),
                        ('active', '=', True), ('hide_spreadsheet', '=', True)]):
            return True

        if model:
            if self.env['remove.action'].search([('access_management_id.active', '=', True),
                                                 ('access_management_id.user_ids', 'in', self.env.user.id),
                                                 ('access_management_id.company_ids', 'in', self.env.company.id),
                                                 ('model_id.model', '=', model),
                                                 ('restrict_spreadsheet', '=', True)]):
                return True

        return False

    def is_add_property_available(self, model):
        if self.search([('user_ids', 'in', self.env.user.id), ('company_ids', 'in', self.env.company.id),
                        ('active', '=', True), ('hide_add_property', '=', True)]):
            return True
        return False

    def is_export_hide(self, model=False):
        if self.search([('user_ids', 'in', self.env.user.id), ('company_ids', 'in', self.env.company.id),
                        ('active', '=', True), ('hide_export', '=', True)]):
            return True

        if model:
            if self.env['remove.action'].search([('access_management_id.active', '=', True),
                                                 ('access_management_id.user_ids', 'in', self.env.user.id),
                                                 ('access_management_id.company_ids', 'in', self.env.company.id),
                                                 ('model_id.model', '=', model),
                                                 ('restrict_export', '=', True)]):
                return True

        return False
