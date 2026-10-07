# -*- coding: utf-8 -*-
import json
import logging
from odoo import http
from odoo import fields
from odoo.http import request
from odoo.tools import file_path
from odoo.modules.module import get_resource_path

_logger = logging.getLogger(__name__)


class CrmPortalController(http.Controller):

    # ─────────────────────────────────────────────────────────────
    # HTML PAGE ROUTES
    # ─────────────────────────────────────────────────────────────
    @http.route('/crm-portal', type='http', auth='user')
    def show_html_page(self, **kw):
        # Get actual file path inside the module
        html_path = '/crm_portal/static/html/crm_portal.html'
        
        file_path = get_resource_path(
            'crm_portal',  # your module name
            'static/html',          # folder path inside module
            'crm_portal.html'          # file name
        )
        if not file_path:
            return "HTML file not found."

        # Read HTML file content
        with open(file_path, 'r', encoding='utf-8') as f:
            html = f.read()
        user = request.env.user

        data = {
            'user_id':   user.id,
            'user_name': user.name,
            'user_email': user.email or '',
        }
        # Return raw HTML content
        return request.make_response(
            html,
            headers=[('Content-Type', 'text/html'),('defaultData', json.dumps(data))],
            
        )

    def _render_html(self, html_file, extra_data=None):
        """Helper: load an HTML file, inject user meta, return response."""
        try:
            path = file_path(f'crm_portal/static/html/{html_file}')
        except Exception:
            return request.make_response(
                f'<h3>File not found: {html_file}</h3>',
                headers=[('Content-Type', 'text/html')]
            )

        with open(path, 'r', encoding='utf-8') as f:
            html = f.read()

        user = request.env.user
        data = {
            'user_id':   user.id,
            'user_name': user.name,
            'user_email': user.email or '',
        }
        if extra_data:
            data.update(extra_data)

        meta = f'<meta name="crm-user-data" content=\'{json.dumps(data)}\'>'
        html = html.replace('</head>', f'{meta}\n</head>', 1)
        return request.make_response(html, headers=[('Content-Type', 'text/html')])

    @http.route('/crm-portal2', type='http', auth='user', website=False)
    def crm_portal(self, **kw):
        return self._render_html('crm_portal.html')

    @http.route('/crm-portal/leads', type='http', auth='user', website=False)
    def crm_leads(self, **kw):
        return self._render_html('crm_portal.html', {'active_menu': 'leads'})

    @http.route('/crm-portal/opportunities', type='http', auth='user', website=False)
    def crm_opportunities(self, **kw):
        return self._render_html('crm_portal.html', {'active_menu': 'opportunities'})

    @http.route('/crm-portal/sales', type='http', auth='user', website=False)
    def crm_sales(self, **kw):
        return self._render_html('crm_portal.html', {'active_menu': 'sales'})

    @http.route('/crm-portal/pipeline', type='http', auth='user', website=False)
    def crm_pipeline(self, **kw):
        return self._render_html('crm_portal.html', {'active_menu': 'pipeline'})

    # ─────────────────────────────────────────────────────────────
    # DASHBOARD API
    # ─────────────────────────────────────────────────────────────

    @http.route('/crm-portal/api/dashboard', type='json', auth='user')
    def api_dashboard(self, **kw):
        uid = request.env.uid
        Lead = request.env['crm.lead'].sudo()
        user_uid = ('user_id', '=', uid)
        sys_admin = request.env.user.has_group("base.group_system")
        lead = [('type', '=', 'lead')] if sys_admin else [('type', '=', 'lead'), user_uid]
        opportunity = [('type', '=', 'opportunity')] if sys_admin else [('type', '=', 'opportunity'), user_uid]
        won = [('stage_id.is_won', '=', True)] if sys_admin else [('stage_id.is_won', '=', True), user_uid]
        lost = [('active', '=', False), ('probability', '=', 0)] if sys_admin else [('active', '=', False), ('probability', '=', 0), user_uid]
        my_leads = Lead.search(lead)
        my_opps  = Lead.search(opportunity)
        won_opps = Lead.search(won)
        lost_opps = Lead.search(lost)

        # Pipeline by stage
        stages = request.env['crm.stage'].sudo().search([])
        pipeline = []
        sys_admin = request.env.user.has_group("base.group_system")

        for stage in stages:
            domain = [('stage_id', '=', stage.id), ('type', '=', 'opportunity')] if sys_admin else [('user_id', '=', uid), ('stage_id', '=', stage.id), ('type', '=', 'opportunity')]
            count = Lead.search_count(domain)
            rev_domain = [('stage_id', '=', stage.id)] if sys_admin else [('user_id', '=', uid), ('stage_id', '=', stage.id)]

            rev = sum(Lead.search(rev_domain).mapped('expected_revenue'))
            pipeline.append({'stage': stage.name, 'count': count, 'revenue': rev})

        # Monthly won (last 6 months)
        from datetime import date, timedelta
        monthly = []
        today = date.today()
        for i in range(5, -1, -1):
            d = today.replace(day=1) - timedelta(days=i * 28)
            m_start = d.replace(day=1)
            if d.month == 12:
                m_end = d.replace(year=d.year + 1, month=1, day=1)
            else:
                m_end = d.replace(month=d.month + 1, day=1)
            monthly_won_domain = [
                ('stage_id.is_won', '=', True),
                ('date_closed', '>=', str(m_start)),
                ('date_closed', '<', str(m_end)),
            ] if sys_admin else [
                ('user_id', '=', uid),
                ('stage_id.is_won', '=', True),
                ('date_closed', '>=', str(m_start)),
                ('date_closed', '<', str(m_end)),
            ]
            won = Lead.search(monthly_won_domain)
            monthly.append({
                'month': m_start.strftime('%b %Y'),
                'count': len(won),
                'revenue': sum(won.mapped('expected_revenue')),
            })

        return {
            'leads_count':     len(my_leads),
            'opps_count':      len(my_opps),
            'won_count':       len(won_opps),
            'lost_count':      len(lost_opps),
            'total_revenue':   sum(won_opps.mapped('expected_revenue')),
            'pipeline':        pipeline,
            'monthly_won':     monthly,
            'company_currency': request.env.user.company_id.currency_id.symbol

        }


    @http.route('/crm-portal/api/sale-order/<int:order_id>', type='json', auth='user')
    def api_sale_order_print(self, order_id, **kw):
        order = request.env['sale.order'].sudo().browse(order_id).exists()

        # Ownership check: only the salesperson of the linked lead can print it
        if not order or order.opportunity_id.user_id.id != request.env.uid:
            return {'error': 'Not found or access denied'}

        currency = order.currency_id
        date_order = fields.Datetime.context_timestamp(order, order.date_order)

        lines = [{
            'name': l.name,
            'qty': l.product_uom_qty,
            'uom': l.product_uom.name if l.product_uom else '',
            'price_unit': l.price_unit,
            'discount': l.discount,
            'taxes': ', '.join(l.tax_id.mapped('name')),
            'subtotal': l.price_subtotal,
        } for l in order.order_line if not l.display_type]

        return {
            'name': order.name,
            'state': order.state,
            'date_order': date_order.strftime('%d/%m/%Y %H:%M'),
            'validity_date': order.validity_date.strftime('%d/%m/%Y') if order.validity_date else '',
            'customer': order.partner_id.name,
            'customer_address': (order.partner_id.contact_address or '').strip(),
            'customer_email': order.partner_id.email or '',
            'customer_phone': order.partner_id.phone or '',
            'salesperson': order.user_id.name or '',
            'company': order.company_id.name,
            'company_address': (order.company_id.partner_id.contact_address or '').strip(),
            'currency_symbol': currency.symbol,
            'currency_position': currency.position,   # 'before' or 'after'
            'lines': lines,
            'amount_untaxed': order.amount_untaxed,
            'amount_tax': order.amount_tax,
            'amount_total': order.amount_total,
            'note': order.note or '',
            'company_logo': f'/web/image/res.company/{order.company_id.id}/logo',
        }

    # ─────────────────────────────────────────────────────────────
    # CRM LEAD/OPPORTUNITY CRUD
    # ─────────────────────────────────────────────────────────────

    @http.route('/crm-portal/api/records', type='json', auth='user')
    def api_records(self, record_type='all', **kw):
        uid = request.env.uid
        Lead = request.env['crm.lead'].sudo()
        sys_admin = request.env.user.has_group("base.group_system")

        domain = [('user_id', '=', uid)] if not sys_admin else []

        if record_type == 'lead':
            domain.append(('type', '=', 'lead'))
        elif record_type == 'opportunity':
            domain.append(('type', '=', 'opportunity'))
            domain.append(('active', '=', True))

        leads = Lead.search(domain, order='create_date desc', limit=200)
        result = []
        company_currency = request.env.user.company_id.currency_id.symbol

        for l in leads:
            result.append({
                'id':               l.id,
                'name':             l.name or '',
                'type':             l.type,
                'stage':            l.stage_id.name if l.stage_id else '',
                'stage_id':         l.stage_id.id if l.stage_id else False,
                'is_won':           l.stage_id.is_won if l.stage_id else False,
                'probability':      l.probability,
                'expected_revenue': l.expected_revenue,
                'partner_name':     l.partner_id.name if l.partner_id else (l.partner_name or ''),
                'partner_id':       l.partner_id.id if l.partner_id else False,
                'assign_id':       l.assigned_to.id if l.assigned_to else False,
                'assign_name':     l.assigned_to.name if l.assigned_to else '',
                'currency_id':       l.currency_id.id if l.currency_id else False,
                'currency_name':       l.currency_id.name if l.currency_id else '',
                'email_from':       l.email_from or '',
                'phone':            l.phone or '',
                'street':           l.street or l.partner_id.street or '',
                'date_deadline':    str(l.date_deadline) if l.date_deadline else '',
                'description':      l.description or '',
                'active':           l.active,
                'sale_order_ids':   l.order_ids.ids if hasattr(l, 'order_ids') else [],
                'company_currency': request.env.user.company_id.currency_id.symbol,
                'user_name': request.env.user.name

            })
        return result

    @http.route('/crm-portal/api/record/<int:record_id>', type='json', auth='user')
    def api_record_get(self, record_id, **kw):
        uid = request.env.uid
        lead = request.env['crm.lead'].sudo().browse(record_id)
        if not lead.exists():
            return {'error': 'Not found or access denied'}

        stages = request.env['crm.stage'].sudo().search([])
        product_ids = request.env['product.product'].sudo().search([])
        partners = request.env['res.partner'].sudo().search([('customer_rank', '>', 0)], limit=100)
        product_list = [{'id': p.id, 'name': p.name} for p in product_ids]
        sale_orders = []
        amount_total = 0.0
        company_currency = request.env.user.company_id.currency_id.symbol

        if hasattr(lead, 'order_ids'):
            if lead.order_ids:
                company_currency = lead.order_ids[0].currency_id.symbol or request.env.user.company_id.currency_id.symbol
                for so in lead.order_ids[0]:
                    for sl in so.order_line:
                        amount_total += sl.price_total
                        sale_orders.append({
                            'id': sl.id,
                            'sale_orderId': so.id,
                            'name': sl.name,
                            'state': sl.order_id.state,
                            'product_ids': product_list,
                            'product_id': sl.product_id.id,
                            # 'product_id': so.order_line[0].product_id.id if so.order_line else False,
                            'amount_total': so.amount_total,
                            'price_total': sl.price_total,
                            'product_uom_qty': sl.product_uom_qty,
                            'price_unit': sl.price_unit,
                            'date_order':    str(sl.order_id.date_order)[:10] if sl.order_id.date_order else '',
                            'invoice_status': sl.order_id.invoice_status if hasattr(sl.order_id, 'invoice_status') else '',
                        })
        lenOrderline = len(lead.order_ids[0].order_line.ids) if lead.order_ids else 0,
        return {
            'id':               lead.id,
            'company_currency': company_currency,
            'product_ids': product_list,
            'amount_total': amount_total,
            'orderLinesLength': lenOrderline,
            'sale_orderId':  lead.order_ids and lead.order_ids[0].id,
            'sale_order_status':  lead.order_ids and lead.order_ids[0].state,
            'name':             lead.name or '',
            'type':             lead.type,
            'stage_id':         lead.stage_id.id if lead.stage_id else False,
            'stage_name':       lead.stage_id.name if lead.stage_id else '',
            'is_won':           lead.stage_id.is_won if lead.stage_id else False,
            'probability':      lead.probability,
            'expected_revenue': lead.expected_revenue,
            'partner_id':       lead.partner_id.id if lead.partner_id else False,
            'partner_name':     lead.partner_id.name if lead.partner_id else '',
            'partner_name_manual': lead.partner_name or '',
            'email_from':       lead.email_from or lead.partner_id.email or '',
            'assign_id':       lead.assigned_to.id if lead.assigned_to else False,
            'assign_name':     lead.assigned_to.name if lead.assigned_to else '',
            'currency_id':       lead.currency_id.id if lead.currency_id else False,
            'currency_name':       lead.currency_id.name if lead.currency_id else '',
            
            'phone':            lead.phone or lead.partner_id.phone or lead.partner_id.mobile or '',
            'street':           lead.street or lead.partner_id.street or '',
            'date_deadline':    str(lead.date_deadline) if lead.date_deadline else '',
            'description':      lead.description or '',
            'active':           lead.active,
            'sale_orders':      sale_orders,
            'stages':           [{'id': s.id, 'name': s.name, 'is_won': s.is_won} for s in stages],
            'partners':         [{'id': p.id, 'name': p.name} for p in partners],
        }

    @http.route('/crm-portal/api/stages', type='json', auth='user')
    def api_stages(self, **kw):
        stages = request.env['crm.stage'].sudo().search([])
        return [{'id': s.id, 'name': s.name, 'is_won': s.is_won, 
                 'company_currency': request.env.user.company_id.currency_id.symbol
    } for s in stages]

    @http.route('/crm-portal/api/partners', type='json', auth='user')
    def api_partners(self, query='', **kw):
        domain = [('customer_rank', '>', 0), ('active', '=', True)]
        if query:
            domain.append(('name', 'ilike', query))
        partners = request.env['res.partner'].sudo().search(domain, limit=100)
        return [{'id': p.id, 'name': p.name, 'email': p.email or '', 'phone': p.phone or '', 'address': p.street or ''} for p in partners]

    @http.route('/crm-portal/api/users', type='json', auth='user')
    def api_users(self, query='', **kw):
        domain = [('active', '=', True)]
        if query:
            domain.append(('name', 'ilike', query))
        users = request.env['res.users'].sudo().search(domain, limit=100)
        return [{'id': p.id, 'name': p.name, 'email': p.email or ''} for p in users]

    @http.route('/crm-portal/api/currency', type='json', auth='user')
    def api_currency(self, query='', **kw):
        domain = [('active', '=', True)]
        if query:
            domain.append(('name', 'ilike', query))
        currency = request.env['res.currency'].sudo().search(domain, limit=100)
        return [{'id': p.id, 'name': p.name} for p in currency]

    @http.route('/crm-portal/api/create', type='json', auth='user')
    def api_create(self, vals, **kw):
        try:
            uid = request.env.uid
            vals['user_id'] = uid
            lead = request.env['crm.lead'].sudo().create(vals)
            return {'success': True, 'id': lead.id}
        except Exception as e:
            _logger.exception("CRM create error")
            return {'error': str(e)}

    # @http.route('/crm-portal/api/update/<int:record_id>', type='json', auth='user')
    # def api_update(self, record_id, vals, **kw):
    #     try:
    #         uid = request.env.uid
    #         lead = request.env['crm.lead'].browse(record_id)
    #         if not lead.exists():
    #             return {'error': 'Not found or access denied'}
    #         if lead.stage_id.is_won:
    #             return {'error': 'Cannot edit a won record'}
    #         lead.write(vals)
    #         return {'success': True}
    #     except Exception as e:
    #         _logger.exception("CRM update error")
    #         return {'error': str(e)}

    @http.route(
        '/crm-portal/api/update/<int:record_id>',
        type='json',
        auth='user'
    )
    def api_update(
            self,
            record_id,
            vals,
            saleOrderId=None,
            sale_order_lines=None,
            **kw):

        # try:
        uid = request.env.uid
        _logger.info(f'CRM AND Sales order information VALS {vals} Saleorder lines ==>{sale_order_lines} Order id {saleOrderId}')

        lead = request.env['crm.lead'].sudo().browse(record_id)

        if not lead.exists():
            return {
                'error': 'Not found or access denied'
            }

        if lead.stage_id.is_won:
            return {
                'error': 'Cannot edit a won record'
            }
        partner = False
        if not vals.get('partner_id'):
            partner = request.env['res.partner'].sudo().search([('phone', '=', vals.get('phone'))], limit=1)
            if not partner:            
                partner = request.env['res.partner'].sudo().create({
                    'name': lead.partner_name or lead.contact_name,
                    'phone': lead.phone,
                    'email': lead.email_from,
                    'street': lead.street,
                    'customer_rank': 1
                })
        if partner:
            vals['partner_id'] = partner.id

        lead.write(vals)
        sale_order = request.env[
            'sale.order'
        ].sudo().search(
            [('id', '=', saleOrderId)],
            limit=1
        )
        
        _logger.info(f'Sale LINE CREATED {sale_order}')
        
        _logger.info(f'Sale LINE CREATED STATE {sale_order.state}')

        if sale_order and sale_order.state in ['draft']:
            _logger.info(f'Sale LINE CREATED {sale_order.state}')

            sale_order.order_line.unlink()

            for line in sale_order_lines or []:

                product = request.env[
                    'product.product'
                ].sudo().browse(
                    line.get('product_id')
                )

                if not product.exists():
                    continue

                REQ = request.env[
                    'sale.order.line'
                ].sudo().create({
                    'order_id': sale_order.id,
                    'product_id': product.id,
                    'name': product.display_name,
                    'product_uom_qty': line.get(
                        'product_uom_qty', 1
                    ),
                    'price_unit': line.get(
                        'price_unit',
                        product.lst_price
                    ),
                })
                _logger.info(f'Sale LINE CREATED {REQ}')

        return {
            'success': True
        }
        # except Exception as e:
        #     _logger.exception("CRM update error")
        #     return {
        #         'error': str(e)
        #     }
            
    @http.route(
        '/api/sale-order-line/delete/<int:line_id>',
        type='json',
        auth='user',
        csrf=False
    )
    def delete_sale_order_line(self, line_id, **kwargs):

        line = request.env['sale.order.line'].sudo().browse(
            int(line_id)
        )

        if not line.exists():
            return {
                'success': False,
                'message': 'Line not found'
            }

        if line.order_id.state != 'draft':
            return {
                'success': False,
                'message': 'Only draft quotations can be modified.'
            }

        line.unlink()

        return {
            'success': True
        }

    @http.route(
        '/api/product/info',
        type='json',
        auth='user',
        csrf=False
    )
    def get_product_info(self, product_id, **kwargs):

        product = request.env['product.product'].sudo().browse(
            int(product_id)
        )

        if not product.exists():
            return {
                'success': False,
                'message': 'Product not found'
            }

        return {
            'success': True,
            'product_id': product.id,
            'name': product.name,
            'price': product.lst_price,
            'uom': product.uom_id.name,
        }

    @http.route('/crm-portal/api/delete/<int:record_id>', type='json', auth='user')
    def api_delete(self, record_id, **kw):
        try:
            uid = request.env.uid
            lead = request.env['crm.lead'].sudo().browse(record_id)
            if not lead.exists():
                return {'error': 'Not found or access denied'}
            lead.unlink()
            return {'success': True}
        except Exception as e:
            _logger.exception("CRM delete error")
            return {'error': str(e)}

    # ─────────────────────────────────────────────────────────────
    # ACTIONS
    # ─────────────────────────────────────────────────────────────

    @http.route('/crm-portal/api/action/convert_opportunity/<int:record_id>', type='json', auth='user')
    def action_convert_opportunity(self, record_id, **kw):
        try:
            uid = request.env.uid
            lead = request.env['crm.lead'].sudo().browse(record_id)
            if not lead.exists():
                return {'error': 'Not found or access denied'}
            partner_id = lead.partner_id
            if not partner_id:
                partner_id = request.env['res.partner'].sudo().create({
                    'name': lead.partner_name or lead.contact_name,
                    'phone': lead.phone,
                    'email': lead.email_from,
                    'street': lead.street,
                    'customer_rank': 1
                })
            lead.write({'type': 'opportunity', 'partner_id': partner_id.id})
            if not lead.stage_id:
                stage = request.env['crm.stage'].sudo().search([], limit=1)
                if stage:
                    lead.stage_id = stage.id
            return {'success': True, 'type': lead.type}
        except Exception as e:
            _logger.exception("Convert opportunity error")
            return {'error': str(e)}

    @http.route('/crm-portal/api/action/cancel_opportunity/<int:record_id>', type='json', auth='user')
    def action_cancel_opportunity(self, record_id, **kw):
        try:
            uid = request.env.uid
            lead = request.env['crm.lead'].sudo().browse(record_id)
            if not lead.exists():
                return {'error': 'Not found or access denied'}
            so_orders = lead.order_ids.filtered(lambda s: s.state in ['sale'])
            if so_orders:
                return {'error': 'You cannot cancel this opportunity because the a sale order has already been generated '}
            lead.write({'type': 'lead', 'probability': 0})
            # if not lead.stage_id:
            stage = request.env['crm.stage'].sudo().search([('is_won', '=', False)])
            if stage:
                lead.stage_id = stage[0].id
            return {'success': True, 'type': lead.type}
        except Exception as e:
            _logger.exception("Cancel opportunity error")
            return {'error': str(e)}

    @http.route('/crm-portal/api/action/mark_won/<int:record_id>', type='json', auth='user')
    def action_mark_won(self, record_id, **kw):
        try:
            uid = request.env.uid
            lead = request.env['crm.lead'].sudo().browse(record_id)
            if not lead.exists():
                return {'error': 'No CRM record found or access denied'}
            if lead.order_ids:
                expected_revenue = sum([r.amount_total for r in lead.order_ids])
                lead.expected_revenue = expected_revenue
            lead.action_set_won_rainbowman()
            return {'success': True}
        except Exception as e:
            _logger.exception("Mark won error")
            return {'error': str(e)}

    @http.route('/crm-portal/api/action/mark_lost/<int:record_id>', type='json', auth='user')
    def action_mark_lost(self, record_id, **kw):
        try:
            uid = request.env.uid
            lead = request.env['crm.lead'].sudo().browse(record_id)
            if not lead.exists():
                return {'error': 'Not found or access denied'}
            lead.action_set_lost()
            return {'success': True}
        except Exception as e:
            _logger.exception("Mark lost error")
            return {'error': str(e)}

    @http.route('/crm-portal/api/action/create_quotation/<int:record_id>', type='json', auth='user')
    def action_create_quotation(self, record_id, sale_order_lines, **kw):
        try:
            uid = request.env.uid
            lead = request.env['crm.lead'].sudo().browse(record_id)
            sale_lead = request.env['sale.order'].sudo().search([
                ('opportunity_id', '=', lead.id), ('state', 'in', ['sale', 'sent'])
                ], limit=1)
            if not lead.exists():
                return {'error': 'Not found or access denied'}
            if sale_lead.exists():
                return {'error': 'Sale Quotation or order has already been generated. Kindly confirm system admin to cancel or modify'}
            _logger.info(f'Sales Quotation information {sale_order_lines} ')
            
            if not sale_order_lines:
                return {'error': 'Sale Order lines not added. Kindly add a line to proceed'}
                
            # Create sale order linked to this lead
            so_vals = {
                'partner_id': lead.partner_id.id if lead.partner_id else request.env['res.partner'].search([], limit=1).id,
                'opportunity_id': lead.id,
                'user_id': uid,
                'date_order': fields.Date.today(),
                'state': 'draft',
            }
            so = request.env['sale.order'].sudo().create(so_vals)
            for line in sale_order_lines or []:
            
                product = request.env[
                    'product.product'
                ].sudo().browse(
                    line.get('product_id')
                )

                if not product.exists():
                    continue

                so_lines = request.env[
                    'sale.order.line'
                ].create({
                    'order_id': so.id,
                    'product_id': product.id,
                    'name': product.display_name,
                    'product_uom_qty': line.get(
                        'product_uom_qty', 1
                    ),
                    'price_unit': line.get(
                        'price_unit',
                        product.lst_price
                    ),
                })
                _logger.info(f'Sale LINE CREATED {so_lines}')
            # so_lines = request.env['sale.order.line'].sudo().create({
            #     'order_id': so.id,
            #     'product_id': request.env.ref('crm_portal.crm_product_id').id,
            #     'product_uom_qty': 1,
            #     'name': lead.name,
            #     'price_unit': lead.expected_revenue,
            # })
            return {'success': True, 'sale_order_id': so.id, 'sale_order_name': so.name}
        except Exception as e:
            _logger.exception("Create quotation error")
            return {'error': str(e)}

    @http.route('/crm-portal/api/action/confirm_quotation/<int:sale_order_id>', type='json', auth='user')
    def action_confirm_quotation(self, sale_order_id, **kw):
        try:
            so = request.env['sale.order'].sudo().browse(sale_order_id)
            if not so.exists():
                return {'error': 'Sale order not found'}
            so.action_confirm()
            return {'success': True, 'state': so.state}
        except Exception as e:
            _logger.exception("Confirm quotation error")
            return {'error': str(e)}

    @http.route('/crm-portal/api/action/cancel_quotation/<int:sale_order_id>', type='json', auth='user')
    def action_cancel_quotation(self, sale_order_id, **kw):
        try:
            so = request.env['sale.order'].sudo().browse([sale_order_id])
            if not so.exists():
                return {'error': 'Sale order not found'}
            soc = request.env['sale.order.cancel'].sudo().create({
                'recipient_ids': [(6, 0, [so.partner_id.id])],
                'order_id': sale_order_id
                })
            # soc.action_cancel()
            soc.action_send_mail_and_cancel()
            so.action_draft()
            _logger.info("So cancelled")

            return {'success': True, 'state': so.state}
        except Exception as e:
            _logger.exception("Cancel quotation error")
            return {'error': str(e)}

    @http.route('/crm-portal/api/action/generate_invoice/<int:sale_order_id>', type='json', auth='user')
    def action_generate_invoice(self, sale_order_id, **kw):
        try:
            so = request.env['sale.order'].sudo().browse(sale_order_id) or request.env['sale.order'].sudo().search([('opportunity_id', '=', sale_order_id)])
            if not so.exists():
                return {'error': 'Sale order not found'}
            so._create_invoices()
            return {'success': True}
        except Exception as e:
            _logger.exception("Generate invoice error")
            return {'error': str(e)}

    @http.route('/crm-portal/api/action/send_sms/<int:record_id>', type='json', auth='user')
    def action_send_sms(self, record_id, message, **kw):
        try:
            lead = request.env['crm.lead'].sudo().browse(record_id)
            if not lead.exists():
                return {'error': 'Not found'}
            phone = lead.phone or (lead.partner_id.phone if lead.partner_id else '')
            if not phone:
                return {'error': 'No phone number on record'}
            # Log SMS note (actual SMS sending requires SMS gateway integration)
            lead.message_post(body=f'📱 SMS sent to {phone}: {message}', message_type='comment')
            return {'success': True, 'phone': phone}
        except Exception as e:
            _logger.exception("SMS error")
            return {'error': str(e)}

    @http.route('/crm-portal/api/action/log_call/<int:record_id>', type='json', auth='user')
    def action_log_call(self, record_id, **kw):
        try:
            lead = request.env['crm.lead'].sudo().browse(record_id)
            if not lead.exists():
                return {'error': 'Not found'}
            phone = lead.phone or (lead.partner_id.phone if lead.partner_id else '')
            lead.message_post(body=f'📞 Call logged to {phone}', message_type='comment')
            return {'success': True, 'phone': phone}
        except Exception as e:
            _logger.exception("Log call error")
            return {'error': str(e)}

    @http.route('/crm-portal/api/sales', type='json', auth='user')
    def api_sales(self, **kw):
        uid = request.env.uid
        sys_admin = request.env.user.has_group("base.group_system")
        domain = [('user_id', '=', uid)] if not sys_admin else []
        orders = request.env['sale.order'].sudo().search(domain, order='create_date desc', limit=100)
        result = []
        for so in orders:
            result.append({
                'id':            so.id,
                'name':          so.name,
                'state':         so.state,
                'partner_name':  so.partner_id.name if so.partner_id else '',
                'amount_total':  so.amount_total,
                'date_order':    str(so.date_order)[:10] if so.date_order else '',
                'invoice_status': so.invoice_status if hasattr(so, 'invoice_status') else '',
                'opportunity_id': so.opportunity_id.id if hasattr(so, 'opportunity_id') and so.opportunity_id else False,
            })
        return result
