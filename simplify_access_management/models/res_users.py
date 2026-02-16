from odoo import fields, models, api, SUPERUSER_ID,_
from odoo.exceptions import UserError, AccessDenied
import logging
from odoo.modules.registry import Registry
_logger = logging.getLogger(__name__)

class res_users(models.Model):
    _inherit = 'res.users'

    access_management_ids = fields.Many2many('access.management', 'access_management_users_rel_ah', 'user_id', 'access_management_id', 'Access Pack')
    password = fields.Char(string='Private key password')

    # allow_ip_ids = fields.One2many('allow.ip', 'user_id', 'Allow IP')
    
    def write(self, vals):
        res = super(res_users, self).write(vals)
        for access in self.access_management_ids:
            if self.env.company in access.company_ids and access.readonly:
                if self.has_group('base.group_system') or self.has_group('base.group_erp_manager'):
                    raise UserError(_('Admin user can not be set as a read-only..!'))
        return res

    @api.model_create_multi
    def create(self, vals_list):
        res = super(res_users, self).create(vals_list)
        for record in self:
            for access in record.access_management_ids:    
                if self.env.company in access.company_ids and access.readonly:
                    if record.has_group('base.group_system') or record.has_group('base.group_erp_manager'):
                        raise UserError(_('Admin user can not be set as a read-only..!'))
        return res

    @classmethod
    def _login(cls, db, credential, user_agent_env):
        try:
            return super()._login(db, credential, user_agent_env=user_agent_env)
        except AccessDenied as e:
            with Registry(db).cursor() as cr:
                login = credential['login']
                cr.execute("SELECT id FROM res_users WHERE lower(login)=%s", (login,))
                res = cr.fetchone()
                if res:
                    raise e

                env = api.Environment(cr, SUPERUSER_ID, {})
                Ldap = env['res.company.ldap']
                for conf in Ldap._get_ldap_dicts():
                    entry = Ldap._authenticate(conf, login, credential['password'])
                    if entry:
                        return {
                            'uid': Ldap._get_or_create_user(conf, login, entry),
                            'auth_method': 'ldap',
                            'mfa': 'default',
                        }
                raise e