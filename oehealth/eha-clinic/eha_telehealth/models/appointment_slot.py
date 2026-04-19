from odoo import models


class TimeSlotLine(models.Model):
    _inherit = "time.slot.line"
    
    def _get_formatted_time(self):
        formatted_time = ""
        name = self.name
        name_list = name.split(":")
        hour = name_list[0]
        min = name_list[1]
        if hour and min:
            formatted_time = f"{int(hour) % 12}:{min}{(int(hour) > 12) and 'pm' or 'am'}"
        return formatted_time
        