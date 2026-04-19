# -*- coding: utf-8 -*-
import base64
from odoo import http
from odoo.http import request
import logging

_logger = logging.getLogger(__name__)


class HomeMenuController(http.Controller):

    @http.route('/home_menu/get_apps', type='json', auth='user')
    def get_apps(self):
        """
        Return all root-level menus that have an action attached.
        These are the top-level "apps" shown in the Home Menu dropdown.
        """
        apps = []

        # Same domain Odoo uses for the apps menu
        root_menus = request.env['ir.ui.menu'].sudo().search([
            ('parent_id', '=', False),
            # ('action', '!=', False),
        ], order='sequence, name')

        for i, menu in enumerate(root_menus):
            # Check access rights – only show menus the user can see
            try:
                if not menu.with_user(request.env.uid)._filter_visible_menus():
                    continue
            except Exception:
                pass

            app = {
                'id':       menu.id,
                'name':     menu.name,
                'sequence': menu.sequence,
                'xmlid':    menu.get_external_id().get(menu.id, ''),
                'web_icon': menu.web_icon or '',
            }

            # Action
            if menu.action:
                try:
                    parts = menu.action.split(',')
                    if len(parts) == 2:
                        app['action_model'] = parts[0].strip()
                        app['action_id']    = int(parts[1].strip())
                except Exception:
                    pass

            # Summary / category from ir.module.module
            module_name = app['xmlid'].split('.')[0] if app['xmlid'] else ''
            if module_name:
                app['module'] = module_name
                mod = request.env['ir.module.module'].sudo().search([
                    ('name', '=', module_name),
                    ('state', '=', 'installed'),
                ], limit=1)
                if mod:
                    app['summary']  = mod.summary or mod.shortdesc or menu.name
                    app['category'] = mod.category_id.name if mod.category_id else 'Uncategorized'
                else:
                    app['summary']  = menu.name
                    app['category'] = 'Apps'
            else:
                app['summary']  = menu.name
                app['category'] = 'Apps'

            apps.append(app)
        _logger.info(f"Apps found, {app}")
        return apps

    @http.route('/home_menu/get_icon/<int:menu_id>', type='http', auth='user')
    def get_icon(self, menu_id, **kwargs):
        """Serve the raw icon image for a menu if web_icon_data is set."""
        menu = request.env['ir.ui.menu'].sudo().browse(menu_id)
        if menu.exists() and menu.web_icon_data:
            try:
                image_data = base64.b64decode(menu.web_icon_data)
                return request.make_response(
                    image_data,
                    headers=[
                        ('Content-Type', 'image/png'),
                        ('Cache-Control', 'public, max-age=604800'),
                    ]
                )
            except Exception:
                pass
        return request.not_found()
