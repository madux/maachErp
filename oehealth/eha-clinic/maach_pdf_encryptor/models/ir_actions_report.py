# Copyright 2020 Creu Blanca
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models
import logging
from io import BytesIO
from odoo.exceptions import ValidationError
from datetime import datetime, date
_logger = logging.getLogger(__name__)
# try:
from PyPDF2 import PdfFileReader, PdfFileWriter
# except ImportError as err:
#     _logger.debug(err)


class IrActionsReport(models.Model):

    _inherit = 'ir.actions.report'

    encrypt = fields.Boolean()

    def render_qweb_pdf(self, res_ids=None, data=None):
        document, type = super(IrActionsReport, self).render_qweb_pdf(res_ids=res_ids, data=data)
        listed_models = ["oeh.medical.lab.test", "oeh.medical.prescription"]
        if self.encrypt and self.model in listed_models: 
            # this is to enable configuration of which 
            # model and what determines fields determines the password
            Model = self.env[self.model]
            # for rec in res_ids:
            if not res_ids or len(res_ids) > 1:
                raise ValidationError('Please you can only print one PDF at a time')
                
            else:
                password = None
                record_id = Model.browse(res_ids)
                if record_id.patient.dob:
                    dateofbirth = date.strftime(record_id.patient.dob,"%d-%m-%Y").replace('-', '') # 20081228
                    lastname = record_id.patient.lastname
                    password = "{}{}".format(lastname.lower(), dateofbirth) 
                else:
                    ValidationError('Please provide {} Date of birth'.format(record_id.patient.name))

                output_pdf = PdfFileWriter()
                in_buff = BytesIO(document)
                pdf = PdfFileReader(in_buff)
                output_pdf.appendPagesFromReader(pdf)
                output_pdf.encrypt(password) #self.env.context.get('encrypt_password'))
                buff = BytesIO()
                output_pdf.write(buff)
                document = buff.getvalue()
        
        return document, type
         