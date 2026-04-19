##############################################################################
#    Copyright (C) 2016 oeHealth (<http://oehealth.in>). All Rights Reserved
#    oeHealth, Hospital Management Solutions
##############################################################################

from odoo import api, fields, models, _

class oeHealthProduct(models.Model):
    _inherit = 'product.template'

    MEDICATION_TYPE = [
        ('Medicine', 'Medicine'),
        ('Vaccine', 'Vaccine'),
    ]

    is_oeh_product = fields.Boolean(string='OEHealth Product', help='Configure as OEHealth product')
    therapeutic_action = fields.Char(string='Therapeutic effect', size=128, help="Therapeutic action")
    composition = fields.Text(string='Composition',help="Components")
    indications = fields.Text(string='Indication',help="Indications")
    dosage = fields.Text(string='Dosage Instructions',help="Dosage / Indications")
    overdosage = fields.Text(string='Overdosage',help="Overdosage")
    pregnancy_warning = fields.Boolean(string='Pregnancy Warning', help="Check when the drug can not be taken during pregnancy or lactancy")
    pregnancy = fields.Text(string='Pregnancy and Lactancy',help="Warnings for Pregnant Women")
    adverse_reaction = fields.Text(string='Adverse Reactions')
    storage = fields.Text(string='Storage Conditions')
    info = fields.Text(string='Extra Info')
    medicament_type = fields.Selection(MEDICATION_TYPE, string='Medication Type')
