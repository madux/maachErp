# -*- coding: utf-8 -*-

from odoo import models, fields, api
import os
from pathlib import Path
import logging
from odoo import models, fields, api
from odoo.tools.float_utils import float_compare
from odoo.exceptions import UserError
_logger = logging.getLogger(__name__)

class maintenance(models.Model):
    _inherit = "maintenance.equipment"

    branch_id = fields.Many2one('eha.branch', string="Location/Branch")

    @api.model
    def migrate_data(self):
        jabi_equipment_branch = self.env['maintenance.equipment'].search([])
        if jabi_equipment_branch:
            for rec in jabi_equipment_branch:
                branch = None
                if rec.location in ['jabi', 'Jabi', 'Jab']:
                    branch = self.env['eha.branch'].search([('code', '=', 'JABI0011')], limit=1).id or 11
                elif rec.location in ['Kano- Lamido Crescent', 'Lamido Crescent', 'Kano, Lamido crescent.','Kano, Lamido Crescent.', 'Kano- Lamido Crescent','Kano, Lamido Crescent','Kano - Lamido Crescent']:
                    branch = self.env['eha.branch'].search([('code', '=', 'KANO0004')], limit=1).id or 4

                elif rec.location in ['independence', 'Independence','Independence Road']:
                    branch = self.env['eha.branch'].search([('code', '=', 'KANO0007')], limit=1).id or 7
                if branch:
                    rec.write({
                        'branch_id': branch
                    })
        # _logger.info('******************* REACH DOC ************ %s', reach_doc)
        # reach_programe = self.env['oeha.medical.program'].search([('name', '=', 'REACH')])
        # _logger.info('******************* REACH PROGRAM ************ %s', reach_programe)
        # reach_users = self.env['res.users'].search([('program_ids', 'in', reach_programe.ids)])
        # _logger.info('******************* REACH USERS ************ %s', reach_users)
        # prescriptions = self.env['oeh.medical.prescription'].search([('create_uid', 'in', reach_users.ids)])
        # evaluations = self.env['oeh.medical.evaluation'].search([('create_uid', 'in', reach_users.ids)])
        # lab_tests = self.env['oeh.medical.lab.test'].search([('create_uid', 'in', reach_users.ids)])
        # evaluations = self.env['oeh.medical.evaluation'].search([('create_uid', 'in', reach_users.ids)])

        # try:
   
        #     old_cifs = self.env['oeha.covid19.cif'].search([('covid_19_inbound_tester', '=', True), ('id_card','=',False)])
        #     new_cifs = self.env['oeha.covid19.cif'].search([('covid_19_inbound_tester', '=', True), ('id_card','!=',False)])

            # SQL = ''' 
            #     UPDATE eha_branch 
            #     SET id = 2 
            #     where id = 8;
            # '''
            # self.env.cr.execute(SQL)

        # except Exception as e:
        #     _logger.info(e)
