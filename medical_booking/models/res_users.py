from odoo import models, fields, api


class ResUsers(models.Model):
    _inherit = 'res.users'

    is_doctor = fields.Boolean(
        string='Is Doctor / Medical Staff',
        default=False,
    )
    is_nurse = fields.Boolean(
        string='Is Nurse',
        default=False,
    )
    medical_speciality = fields.Char(string='Medical Speciality')
    branch_ids = fields.Many2many(
        'multi.branch',
        'booking_branch_doctor_rel',
        'user_id',
        'branch_id',
        string='Assigned Branches',
    )

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + [
            'is_doctor', 'is_nurse', 'medical_speciality', 'branch_ids',
        ]

    @property
    def SELF_WRITEABLE_FIELDS(self):
        return super().SELF_WRITEABLE_FIELDS + [
            'medical_speciality',
        ]
