import base64
import logging
import mimetypes
import os
import re

from odoo import http, _

_logger = logging.getLogger()

class Sign(http.Controller):


    @http.route(['/sign/<link>/<int:partner_id>'], type='http', auth='public')
    def share_link(self, link, partner_id=False):#, **post):
        '''id = template_share_id'''
        template = http.request.env['sign.template'].sudo().search([('share_link', '=', link)], limit=1)
        template_partner_id = http.request.env['res.partner'].sudo().search([('id', '=', partner_id)], limit=1)

        if not template:
            return http.request.not_found()
        sign_request = http.request.env['sign.request'].sudo(template.create_uid).create({
            'template_id': template.id,
            'reference': "%(template_name)s-public" % {'template_name': template.attachment_id.name},
            'favorited_ids': [(4, template.create_uid.id)],
            'partner_id': template_partner_id.id if template_partner_id else False,
        })

        request_item = http.request.env['sign.request.item'].sudo().create({'sign_request_id': sign_request.id, 'role_id': template.sign_item_ids.mapped('responsible_id').id})
        sign_request.action_sent()

        if partner_id:
            return http.redirect_with_hash('/sign/document/%(request_id)s/%(access_token)s/?name=%(partner_name)s&email=%(partner_email)s' % {'request_id': sign_request.id, 'access_token': request_item.access_token, 'partner_name': template_partner_id.name, 'partner_email': template_partner_id.email})
        else:
            return http.redirect_with_hash('/sign/document/%(request_id)s/%(access_token)s' % {'request_id': sign_request.id, 'access_token': request_item.access_token})
