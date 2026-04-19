# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import route, request
from odoo.addons.mass_mailing.controllers.main import MassMailController


class EhaMassMailController(MassMailController):

    @route('/website_mass_mailing/subscribe', type='json', website=True, auth="public")
    def subscribe(self, list_id, email, subscriber_name, phone, **post):
        Contacts = request.env['mailing.contact'].sudo()
        name, email = Contacts.get_name_email(email)
        new_name = subscriber_name if subscriber_name else name
        
        #format phone
        formatted_phone = request.env['phone.validation.mixin'].phone_format(phone) if phone else False
        
        contact_ids = Contacts.search([
            ('list_ids', 'in', [int(list_id)]),
            ('email', '=', email),
        ], limit=1)
        if not contact_ids:
            # inline add_to_list as we've already called half of it
            Contacts.create({'name': new_name, 'email': email, 'phone':formatted_phone, 'list_ids': [(6,0,[int(list_id)])]})
        elif contact_ids.opt_out:
            contact_ids.opt_out = False
        # add email to session
        request.session['mass_mailing_email'] = email
        return True

