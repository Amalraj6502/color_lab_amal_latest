from dateutil.relativedelta import relativedelta

from odoo import fields, models, _, api
from odoo.exceptions import UserError, ValidationError


class ApprovalTemplate(models.Model):
    _name = 'approval.template'
    _description = 'Approval Template'

    name = fields.Char('Approval Name', required=True)
    type_id = fields.Many2one('approval.template.type', string='Approval Type')
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    approval_lines = fields.One2many('approval.template.line', 'approval_id', string='Approvers')
    approval_type = fields.Selection(string='Approval Based On', selection=[
        ('amount', 'Amount'),
        ('level', 'Level'), ], required=True, default='level')
    access_type = fields.Selection(string='Approved By', selection=[
        ('user', 'Users'),
        ('group', 'Access Groups'), ], required=True, default='user')
    res_model_id = fields.Many2one(related='type_id.res_model_id')
    res_model_name = fields.Char(related='type_id.res_model_name')
    amount_field_id = fields.Many2one(
        'ir.model.fields', string='Amount Field',
        domain="[('model_id', '=', res_model_id), ('ttype', 'in', ('monetary', 'float', 'integer'))]",
        ondelete='cascade')
    rejection_comment_required = fields.Boolean('Required Rejection Reason?',
                                                help='If ticked, a popup will appear to enter the reason when the approver rejects the request.')

    currency_id = fields.Many2one(related='company_id.currency_id', string='Company Currency',
                                  readonly=True, store=True)

    @api.constrains('approval_type')
    def _check_account_code(self):
        for rec in self:
            if rec.approval_type == 'amount' and not rec.amount_field_id:
                raise ValidationError(_(
                    "Amount field must be specified as you selected the approval is based on amount.\n"
                ))

    def is_done(self, approvals):
        approvals = approvals and approvals.get('approved_vals', [])
        if approvals and any(item.get('is_rejected') for item in approvals):
            return False
        if approvals and len(approvals) >= len(self.approval_lines):
            return True
        return False

    def _get_previous_approval_ids(self, vals):
        lines = self.env['approval.template.line']
        if not vals or not isinstance(vals, dict) or not vals.get('approved_vals'):
            return lines
        line_ids = [item.get('approval_line_id') for item in vals['approved_vals']]
        return lines.browse(line_ids)

    def _generate_approval_vals(self, vals=None, initial=None):
        previous_lines = self._get_previous_approval_ids(vals)
        remaining_approval_lines = self.approval_lines - previous_lines
        if initial:
            current_approval_id = self.approval_lines.browse()
        else:
            current_approval_id = remaining_approval_lines[0] if remaining_approval_lines else remaining_approval_lines
        current_approvals = current_approval_id._generate_approval_vals_json()
        next_approvals = []
        exclude_from_upcoming = [current_approval_id.id]
        if not self._context.get('is_rejected', False):
            if initial:
                next_approval_id = remaining_approval_lines[
                    0] if remaining_approval_lines else remaining_approval_lines.browse()
            else:
                next_approval_id = remaining_approval_lines[1] if len(
                    remaining_approval_lines) >= 2 else remaining_approval_lines.browse()
            next_approval_id._notify_users()
            next_approvals = next_approval_id._generate_upcoming_approval_json()
            exclude_from_upcoming.append(next_approval_id.id)
        upcoming_approvals = remaining_approval_lines.filtered(
            lambda l: l.id not in exclude_from_upcoming)._generate_upcoming_approval_json()
        return current_approvals, next_approvals, upcoming_approvals

    def _get_initial_approval_structure(self):
        new_approval, next_approval, upcoming_approvals = self._generate_approval_vals(initial=True)
        # print(new_approval,next_approval,upcoming_approvals)
        new_approval_vals = {
            "approval_id": {
                'id': self.id,
                'name': self.name
            },
            "approved_vals": [],
            "next_approval": next_approval,
            "upcoming_approvals": upcoming_approvals
        }
        return new_approval_vals

    def approve(self, previous_approvals):
        if not isinstance(previous_approvals, dict):
            previous_approvals = {}
        user_id = self.env.user
        approvals = previous_approvals.get('approved_vals', [])
        if approvals:
            approvals.sort(key=lambda x: x['approval_time'])
        # Closing previous activities
        context = self._context
        activity_type = self.env.ref('web_approval.mail_activity_approval')
        model = context.get('active_model')
        rec_id = context.get('active_id')
        record_id = self.env[model].browse(rec_id)
        activitie = self.env['mail.activity'].search(
            [('activity_type_id', '=', activity_type.id), ('res_model', '=', model), ('res_id', '=', record_id.id),
             ('user_id', '!=', self.env.user.id)])
        for act in activitie:
            act.unlink()
        activitie = self.env['mail.activity'].search(
            [('activity_type_id', '=', activity_type.id), ('res_model', '=', model), ('res_id', '=', record_id.id),
             ('user_id', '=', self.env.user.id)])
        for act in activitie:
            act.action_feedback()
        current_approval, next_approval, upcoming_approvals = self._generate_approval_vals(previous_approvals)
        if current_approval and current_approval.get('approval_line_id'):
            new_approval_line_id = self.env['approval.template.line'].browse(current_approval['approval_line_id'])
            if user_id.id not in new_approval_line_id._get_approval_users().ids:
                raise UserError(_("You cannot approve/reject this request because of one of the following reasons:"
                                  "\n1. You have no permission to approve/reject this request."
                                  "\n2. There is one or more approvers to validate this request before your approval."))
        if current_approval:
            approvals.append(current_approval)
        new_approvals = {
            "approval_id": {
                'id': self.id,
                'name': self.name
            },
            "approved_vals": approvals,
            "next_approval": next_approval,
            "upcoming_approvals": upcoming_approvals
        }
        new_approvals.update({
            'is_done': self.is_done(new_approvals)
        })

        return new_approvals

    def reject(self, previous_approvals):
        return self.with_context(is_rejected=True).approve(previous_approvals)

    def clear_previous_approvals(self):
        return {}

    def init_approval_structure(self):
        return self._get_initial_approval_structure()


class ApprovalTemplateLine(models.Model):
    _name = 'approval.template.line'
    _description = 'Approvers'
    _order = 'sequence asc, id desc'

    name = fields.Char('Level Name', required=True)
    sequence = fields.Integer(default=10)
    approval_id = fields.Many2one('approval.template', string='Approval Type', required=True)
    user_ids = fields.Many2many('res.users', 'approval_template_users_rel', 'approval_line_id', 'user_id',
                                string='Approval Users')
    group_ids = fields.Many2many('res.groups', string='Access Group')

    amount_limit = fields.Monetary('Amount', required=True, help='Minimum approval amount. If set zero, '
                                                                 'any amount will be needing to get approval')
    escalation_days = fields.Integer('Escalation Days',
                                     help='A notification will be sent if the approver not approved/rejected the '
                                          'request after the escalation days')
    escalation_user_ids = fields.Many2many('res.users', 'approval_template_escalation_users_rel', 'approval_line_id',
                                           'user_id', string='Escalation Users',
                                           help='A notification will be sent to these users if the approver not '
                                                'approved/rejected the request after the escalation days')
    currency_id = fields.Many2one(related='approval_id.currency_id')
    approval_type = fields.Selection(related='approval_id.approval_type')
    access_type = fields.Selection(related='approval_id.access_type')

    def _notify_users(self):
        today = fields.Date.context_today(self)
        context = self._context
        model = context.get('active_model')
        rec_id = context.get('active_id')
        record_id = self.env[model].browse(rec_id)
        note = "%s has requested for the %s approval of the record %s" % (
            self.env.user.name,self.name, record_id.read(fields=[record_id._rec_name])[0][record_id._rec_name])
        # if record_id and 'mail.activity.mixin' in record_id._inherit
        for rec in self:
            for user in rec.user_ids:
                record_id.activity_schedule('web_approval.mail_activity_approval', note=note,
                                        user_id=user.id,
                                        date_deadline=today + relativedelta(days=rec.escalation_days))

    def _generate_approval_vals_json(self):
        user_id = self.env.user
        if not self:
            return {}
        cxt = self._context
        is_rejected = cxt.get('is_rejected', False)
        vals = {
            "approval_line_id": self.id,
            "approval_time": str(fields.Datetime.now()),
            "is_rejected": is_rejected,
            "comment": cxt.get('comment', False) if is_rejected else False,
            "approval_user": {
                'id': user_id.id,
                'name': user_id.name,
                'partner_id': user_id.partner_id.id,
            },
            "level": self.name,
        }
        return vals

    def _check_amount_limit(self):
        field_id = self.approval_id.amount_field_id
        if self.approval_id.approval_type == 'amount' and self.amount_limit != 0.0 or field_id:
            record_id = self.env[field_id.model].browse(self._context.get('active_id', False))
            if record_id.exists():
                amount = record_id.read(fields=[field_id.name])[0].get(field_id.name)
                if amount < self.amount_limit:
                    return False
            else:
                raise ValueError('No active_id found in the context.')
        return True

    def _get_approval_users(self):
        if self.approval_id.access_type == 'user':
            return self.user_ids
        return self.group_ids.mapped('users')

    def _generate_upcoming_approval_json(self):
        vals = []
        for approval in self:
            if not approval._check_amount_limit():
                continue
            user_vals = []
            users = approval._get_approval_users()
            for user in users:
                user_vals.append({
                    'id': user.id,
                    'name': user.name,
                })
            if len(users) > 1:
                others = len(users) - 1
                user_names = ', '.join([users[0].name]) + ' and %s others' % others
            else:
                user_names = ', '.join(users.mapped('name'))

            vals.append({
                "approval_line_id": approval.id,
                'approval_users': user_vals,
                'approval_user_names': user_names,
                'level': approval.name,
                "is_rejected": self._context.get('is_rejected', False),
            })
        return vals
