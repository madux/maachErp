# -*- coding: utf-8 -*-

from odoo import models, fields, api
import os
from pathlib import Path
import logging

_logger = logging.getLogger(__name__)

class eha_data_migration(models.Model):
    _name = "eha.datamigration"

    @api.model
    def migrate_data(self):
        # reach_doc = self.env['oeh.medical.physician'].search([('name', '=', 'REACH NURSE')])
        # if not reach_doc:
        #     reach_doc = self.env['oeh.medical.physician'].create({'name': 'REACH NURSE'})
        # _logger.info('******************* REACH DOC ************ %s', reach_doc)
        # reach_programe = self.env['oeha.medical.program'].search([('name', '=', 'REACH')])
        # _logger.info('******************* REACH PROGRAM ************ %s', reach_programe)
        # reach_users = self.env['res.users'].search([('program_ids', 'in', reach_programe.ids)])
        # _logger.info('******************* REACH USERS ************ %s', reach_users)
        # prescriptions = self.env['oeh.medical.prescription'].search([('create_uid', 'in', reach_users.ids)])
        # evaluations = self.env['oeh.medical.evaluation'].search([('create_uid', 'in', reach_users.ids)])
        # lab_tests = self.env['oeh.medical.lab.test'].search([('create_uid', 'in', reach_users.ids)])
        # evaluations = self.env['oeh.medical.evaluation'].search([('create_uid', 'in', reach_users.ids)])

        try:
   
            old_cifs = self.env['oeha.covid19.cif'].search([('covid_19_inbound_tester', '=', True), ('id_card','=',False)])
            new_cifs = self.env['oeha.covid19.cif'].search([('covid_19_inbound_tester', '=', True), ('id_card','!=',False)])

            # SQL = ''' 
            #     UPDATE eha_branch 
            #     SET id = 2 
            #     where id = 8;
            # '''
            # self.env.cr.execute(SQL)

        except Exception as e:
            _logger.info(e)
