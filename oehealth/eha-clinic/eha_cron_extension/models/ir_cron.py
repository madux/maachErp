from odoo import models, fields


class IrCron(models.Model):
    _inherit = 'ir.cron'

    description = fields.Text(string='Description', help="""This field helps to provide more information 
                              on what the CRON does e.g. This cron syncs labtests to NCDC for patients that are travelling to Canada""")
