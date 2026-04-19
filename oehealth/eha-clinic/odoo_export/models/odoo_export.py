# -*- coding: utf-8 -*-

import csv 
import io
import xlwt
from datetime import datetime, timedelta
import base64
import random
from odoo.exceptions import ValidationError
from odoo import fields, models, api, _
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from dateutil.parser import parse
import ast 
import logging
_logger = logging.getLogger(__name__)


class MaOdooExport(models.Model):
    _name = "ma.export.report"
    _description = 'Export model'


    name = fields.Char(string="Title of Document", help="Display title of the excel file to generate")
    target_model = fields.Many2one('ir.model', string="Target Model")
    target_model_field_ids = fields.One2many('ma.export.line', 'export_id', string="Fields")
    domain = fields.Text(string="Domain", default="[]",
     help="Configure domain to be used: eg [('active', '=', True)]")
    limit = fields.Integer('limit', default=0)
    set_limit = fields.Boolean('Set limit', default=False)
    start_limit = fields.Integer('Start limit', default=0)
    end_limit = fields.Integer('End limit', default=0)
    excel_file = fields.Binary('Download Excel file', readonly=True)
    filename = fields.Char('Excel File')
    

    @api.onchange('set_limit')
    def onchange_set_limit(self):
        if not self.set_limit:
            self.start_limit = 0
            self.end_limit = 10

    @api.onchange('end_limit')
    def onchange_end_limit(self):
        if self.end_limit and self.end_limit <= self.start_limit:
            raise ValidationError('End limit should not be lesser than start limit')
 

    def method_export(self):
        self.build_excel_via_field_lines()

    def get_vals(self, fieldchain, comparision):
        return [(fieldchain, 'in', comparision)]

    def build_excel_via_field_lines(self):
        if self.target_model:
            p = f"{self.target_model.model}"
            record_obj = self.env[p].sudo()#.search([])
            if self.domain:
                if not self.domain.startswith('[') or not self.domain.endswith(']'):
                    """checks if domain is available and starts or ends with [] respectively"""
                    raise ValidationError('There is an Issue with the domain construction')
            domain = ast.literal_eval(self.domain)
            limit = self.limit if self.limit > 0 else None
            records = record_obj.search(domain, limit=limit)
            # obj_field_dict = record_obj.fields_get()
            if self.mapped('target_model_field_ids').filtered(lambda s: s.name == False):
                raise ValidationError('Please provide header name for one of the field line')
            if records:
                setlimit = "[self.start_limit: self.end_limit]"
                headers = [
                    hd.name.capitalize() for hd in self.target_model_field_ids
                    ] 
                lenght_of_headers = len(headers)
                style0 = xlwt.easyxf('font: name Times New Roman, color-index red, bold on',
                    num_format_str='#,##0.00')
                # style1 = xlwt.easyxf(num_format_str='DD-MMM-YYYY')
                wb = xlwt.Workbook()
                ws = wb.add_sheet(self.name)
                colh = 0
                # ws.write(0, 6, 'RECORDS GENERATED: %s - On %s' %(self.name, datetime.strftime(fields.Date.today(), '%Y-%m-%d')), style0)
                for head in headers:
                    ws.write(0, colh, head)
                    colh += 1
                row = 1
                
                def get_repr(value): 
                    if callable(value):
                        return '%s' % value()
                    return value or ""

                def get_field(instance, field):
                    field_path = field.split('.')
                    attr = instance
                    for elem in field_path:
                        try:
                            attr = getattr(attr, elem)
                        except AttributeError:
                            return None
                    return attr

                def join_related_chains(object_instance, field_chains):
                    '''
                    i.e field_chains = patient_id.partner_id.street2, patient_id.partner_id.street2
                    if field_chains:
                        chains = related_field_chain.split(',') e.g ['patient_id.partner_id.street', 'patient_id.partner_id.street2']
                        for ch in chains:
                            loops each and returns the joined the value
                    '''
                    if field_chains:
                        chains = field_chains.split(',')
                        txts = [] 
                        for chain in chains:
                            # e.g chain is 'patient_id.partner_id.street'
                            vals = get_repr(get_field(object_instance, chain))
                            if vals:
                                txts.append(vals)
                        try:
                            txt = ','.join(txts)
                            return txt
                        except TypeError as e:
                            raise ValidationError(e)
                        
                for rec in records:
                    col = 0
                    for field in self.target_model_field_ids:
                        related_field_chain = field.related_field_chain
                        # _logger.info(f"""lllllll {eval("rec.patient_id.name")}""")
                        if field.field_type in ['one2many', 'many2many']:
                            m2m_txt = []
                            for object_instance in rec.mapped(f'{field.technical_name}'):
                                #eg rec.mapped('lab_test_criteria). 
                                vals = get_repr(get_field(object_instance, related_field_chain))
                                if vals:
                                    m2m_txt.append(vals)
                            txt = ""
                            try:
                                txt = ','.join(m2m_txt)
                            except TypeError as e:
                                raise ValidationError(
                                            """Wrong value returned kindly set the one2many
                                                field properly to return a Text value"""
                                                )
                            ws.write(row, col, txt)
                        elif field.field_type in ['many2one']:
                            # objinstance_vals = get_repr(get_field(rec, related_field_chain))
                            # if objinstance_vals and field.date_format:
                            #     val = datetime.strftime(objinstance_vals, field.date_format)
                            # else:
                            #     val = objinstance_vals
                            # ws.write(row, col, val)
                            if field.date_format:
                                objinstance_vals = get_repr(get_field(rec, related_field_chain))
                                val = datetime.strftime(objinstance_vals, field.date_format)
                            else:
                                # objinstance_vals = get_repr(get_field(rec, related_field_chain))
                                objinstance_vals = join_related_chains(rec, related_field_chain)
                                val = objinstance_vals
                            ws.write(row, col, val)

                        elif field.field_type in ['datetime', 'date']:
                            try:
                                objinstance_vals = get_repr(get_field(rec, field.technical_name))
                                # objinstance_vals = can be in the format set as d-m-y h:m:s
                                if objinstance_vals: 
                                    date_val = datetime.strftime(objinstance_vals, field.date_format)
                                else:
                                    date_val = ""
                                _logger.info(f'DATE TIME GOTTEN IS {date_val}==> {objinstance_vals}')
                                ws.write(row, col, date_val)
                            except TypeError as e:
                                pass 
                        elif field.field_type in ['boolean']:
                            res = ""
                            try:
                                objinstance_vals = get_repr(get_field(rec, field.technical_name))
                                # objinstance_vals = can be True or False
                                value = objinstance_vals
                                if field.field_domain:
                                    # exec(field.field_domain) # e.g result = 10 if {value} is True else 12
                                    res = eval(field.field_domain)
                                else:
                                    res = value
                                ws.write(row, col, res)
                            except Exception as e:
                                raise ValidationError(f"Issues occured with boolean value logic expression for field {field.technical_name}. see error {e}")
                        elif field.field_type in ['char']:
                            if related_field_chain:
                                val = join_related_chains(rec, related_field_chain)
                            else:
                                val = get_repr(get_field(rec, field.technical_name))
                            ws.write(row, col, val)
                        else:
                            if field.field_id:
                                obj_vals = get_repr(get_field(rec, field.technical_name))
                                ws.write(row, col, obj_vals)
                            else:
                                ws.write(row, col, "")
                        col += 1
                    row += 1
                fp = io.BytesIO()
                wb.save(fp)
                filename = "{} ON {}.xls".format(
                    self.name, datetime.strftime(fields.Date.today(), '%Y-%m-%d'), style0)
                self.excel_file = base64.encodestring(fp.getvalue())
                self.filename = filename
                fp.close()
                return {
                        'type': 'ir.actions.act_url',
                        'url': '/web/content/?model=ma.export.report&download=true&field=excel_file&id={}&filename={}'.format(self.id, self.filename),
                        'target': 'current',
                        'nodestroy': False,
                }
            else:
                raise ValidationError('No record found')

                    
class MaOdooExportLine(models.Model):
    _name = 'ma.export.line'
    _description = 'Export model line'
    
    sequence = fields.Char('')
    export_id = fields.Many2one('ma.export.report', string="")
    target_model = fields.Many2one('ir.model', string="Target Model")
    field_id = fields.Many2one('ir.model.fields', string="Field")
    name = fields.Char(string="Header Name", store=True, readonly=False, help="Display name of field")
    technical_name = fields.Char(string="Technical Name", store=True, readonly=True, compute="_compute_field_id", help="technical name of field")
    field_model = fields.Many2one('ir.model', string="Field Model", compute="_compute_field_id")
    field_type = fields.Char(string="Field Type", store=True, readonly=True, compute="_compute_field_id")
    related_field_chain = fields.Char(string="field Chain")
    date_format = fields.Char(string="Date format")
    field_domain = fields.Char(string="Python Logic", 
    help="""
    Set python expression eg. for boolean use result = 10 if value is True else 12,
     for m2m or o2m, use if the result test is in ['Result Interpretation]""")

    @api.depends('field_id')
    def _compute_field_id(self):
        for rec in self:
            if rec.field_id:
                rec.field_model = rec.field_id.model_id.id
                rec.field_type = rec.field_id.ttype
                # rec.name = rec.field_id.field_description
                rec.technical_name = rec.field_id.name
            else:
                rec.field_model = False
                rec.field_type = False
                rec.technical_name = False

    @api.onchange('target_model')
    def onchange_target_model(self):
        items = [('id', '=', None)]
        if self.target_model: 
            related_model_fields = [
                rec.id for rec in self.target_model.mapped('field_id')
                    ] 
            items = [('id', 'in', related_model_fields)]
        return {
            'domain': {
                'field_id': items
            }
        }
 