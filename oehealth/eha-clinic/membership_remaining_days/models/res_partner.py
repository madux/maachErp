# -*- coding: utf-8 -*-
#################################################################################
#
#    Odoo, Open Source Management Solution
#    Copyright (C) 2020-today Ascetic Business Solution <www.asceticbs.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#################################################################################

from odoo import models, api, fields
from dateutil.relativedelta import relativedelta
from datetime import datetime, timedelta
from datetime import datetime
import calendar


class res_partner(models.Model):
    _inherit = "res.partner"

    membership_days_remaining = fields.Integer(compute='_get_membership_remaining_days', string="Remaining Days",
                                       help='Shows the remaining days of the customer membership')

    @api.depends('membership_stop')
    def _get_membership_remaining_days(self):
        for record in self:
            if record.membership_stop:
                membership_stop = record.membership_stop
                current_date = datetime.now().strftime('%Y-%m-%d')
                number_of_days = (
                        fields.Date.from_string(membership_stop) -
                        fields.Date.from_string(current_date)).days + 1
                if number_of_days > 0:
                    record.membership_days_remaining = number_of_days
                else:
                    record.membership_days_remaining = 0
            else:
                record.membership_days_remaining = 0

