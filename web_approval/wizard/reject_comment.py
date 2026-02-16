from odoo import fields, models, _


class ApprovalComment(models.TransientModel):
    _name = 'approval.comment'
    _description = 'Approval Commend'

    comment = fields.Text('Commend on the Action', required=True)

    def post_comment(self):
        if self._context.get('active_id') and self._context.get('active_model'):
            record_id = self.env[self._context['active_model']].browse(self._context['active_id'])
            context = self._context
            activity_type = self.env.ref('web_approval.mail_activity_approval')
            model = context.get('active_model')
            rec_id = context.get('active_id')
            record_id = self.env[model].browse(rec_id)
            activitie = self.env['mail.activity'].search(
                [('activity_type_id', '=', activity_type.id), ('res_model', '=', model), ('res_id', '=', record_id.id)])
            for act in activitie:
                act.unlink()
            record_id.message_mail_with_source(
                "web_approval.approval_comment_summary",
                render_values={
                    "title": _('Request has been rejected with the following comment:'),
                    "comment": self.comment,
                },
            )
            record_id.with_context(comment=self.comment)._do_reject()

        if hasattr(record_id, 'approval_state'):
            record_id.write({'approval_state': False})

        if hasattr(record_id, 'rejection_by'):
            record_id.write({
                'rejection_by': self.env.user.id,
                'rejection_date': fields.Datetime.now(),
                'is_rejected': True
            })
