from odoo import models, fields


class ResUsers(models.Model):
    _inherit = "res.users"

    def _is_member(self):
        self.ensure_one()
        if self._is_public():
            return False
        patient_id = self.patient_id
        if patient_id and patient_id.plan_id:
            return True
        return False
