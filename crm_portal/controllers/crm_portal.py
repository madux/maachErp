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
        Lead = request.env['crm.lead']

        my_leads = Lead.search([('user_id', '=', uid), ('type', '=', 'lead')])
        my_opps  = Lead.search([('user_id', '=', uid), ('type', '=', 'opportunity')])
        won_opps = Lead.search([('user_id', '=', uid), ('stage_id.is_won', '=', True)])
        lost_opps = Lead.search([('user_id', '=', uid), ('active', '=', False), ('probability', '=', 0)])

        # Pipeline by stage
        stages = request.env['crm.stage'].search([])
        pipeline = []
        for stage in stages:
            count = Lead.search_count([('user_id', '=', uid), ('stage_id', '=', stage.id), ('type', '=', 'opportunity')])
            rev = sum(Lead.search([('user_id', '=', uid), ('stage_id', '=', stage.id)]).mapped('expected_revenue'))
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
            won = Lead.search([
                ('user_id', '=', uid),
                ('stage_id.is_won', '=', True),
                ('date_closed', '>=', str(m_start)),
                ('date_closed', '<', str(m_end)),
            ])
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
        }

    # ─────────────────────────────────────────────────────────────
    # CRM LEAD/OPPORTUNITY CRUD
    # ─────────────────────────────────────────────────────────────

    @http.route('/crm-portal/api/records', type='json', auth='user')
    def api_records(self, record_type='all', **kw):
        uid = request.env.uid
        Lead = request.env['crm.lead']
        domain = [('user_id', '=', uid)]

        if record_type == 'lead':
            domain.append(('type', '=', 'lead'))
        elif record_type == 'opportunity':
            domain.append(('type', '=', 'opportunity'))
            domain.append(('active', '=', True))

        leads = Lead.search(domain, order='create_date desc', limit=200)
        result = []
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
                'email_from':       l.email_from or '',
                'phone':            l.phone or '',
                'street':           l.street or '',
                'date_deadline':    str(l.date_deadline) if l.date_deadline else '',
                'description':      l.description or '',
                'active':           l.active,
                'sale_order_ids':   l.order_ids.ids if hasattr(l, 'order_ids') else [],
            })
        return result

    @http.route('/crm-portal/api/record/<int:record_id>', type='json', auth='user')
    def api_record_get(self, record_id, **kw):
        uid = request.env.uid
        lead = request.env['crm.lead'].browse(record_id)
        if not lead.exists() or lead.user_id.id != uid:
            return {'error': 'Not found or access denied'}

        stages = request.env['crm.stage'].search([])
        partners = request.env['res.partner'].search([('customer_rank', '>', 0)], limit=100)

        sale_orders = []
        if hasattr(lead, 'order_ids'):
            for so in lead.order_ids:
                sale_orders.append({
                    'id': so.id,
                    'name': so.name,
                    'state': so.state,
                    'amount_total': so.amount_total,
                    'date_order':    str(so.date_order)[:10] if so.date_order else '',
                    'invoice_status': so.invoice_status if hasattr(so, 'invoice_status') else '',
                })

        return {
            'id':               lead.id,
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
            'email_from':       lead.email_from or '',
            'phone':            lead.phone or '',
            'street':           lead.street or '',
            'date_deadline':    str(lead.date_deadline) if lead.date_deadline else '',
            'description':      lead.description or '',
            'active':           lead.active,
            'sale_orders':      sale_orders,
            'stages':           [{'id': s.id, 'name': s.name, 'is_won': s.is_won} for s in stages],
            'partners':         [{'id': p.id, 'name': p.name} for p in partners],
        }

    @http.route('/crm-portal/api/stages', type='json', auth='user')
    def api_stages(self, **kw):
        stages = request.env['crm.stage'].search([])
        return [{'id': s.id, 'name': s.name, 'is_won': s.is_won} for s in stages]

    @http.route('/crm-portal/api/partners', type='json', auth='user')
    def api_partners(self, query='', **kw):
        domain = [('customer_rank', '>', 0)]
        if query:
            domain.append(('name', 'ilike', query))
        partners = request.env['res.partner'].search(domain, limit=50)
        return [{'id': p.id, 'name': p.name, 'email': p.email or '', 'phone': p.phone or ''} for p in partners]

    @http.route('/crm-portal/api/create', type='json', auth='user')
    def api_create(self, vals, **kw):
        try:
            uid = request.env.uid
            vals['user_id'] = uid
            lead = request.env['crm.lead'].create(vals)
            return {'success': True, 'id': lead.id}
        except Exception as e:
            _logger.exception("CRM create error")
            return {'error': str(e)}

    @http.route('/crm-portal/api/update/<int:record_id>', type='json', auth='user')
    def api_update(self, record_id, vals, **kw):
        try:
            uid = request.env.uid
            lead = request.env['crm.lead'].browse(record_id)
            if not lead.exists() or lead.user_id.id != uid:
                return {'error': 'Not found or access denied'}
            if lead.stage_id.is_won:
                return {'error': 'Cannot edit a won record'}
            lead.write(vals)
            return {'success': True}
        except Exception as e:
            _logger.exception("CRM update error")
            return {'error': str(e)}

    @http.route('/crm-portal/api/delete/<int:record_id>', type='json', auth='user')
    def api_delete(self, record_id, **kw):
        try:
            uid = request.env.uid
            lead = request.env['crm.lead'].browse(record_id)
            if not lead.exists() or lead.user_id.id != uid:
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
            lead = request.env['crm.lead'].browse(record_id)
            if not lead.exists() or lead.user_id.id != uid:
                return {'error': 'Not found or access denied'}
            partner_id = lead.partner_id
            if not partner_id:
                partner_id = request.env['res.partner'].create({
                    'name': lead.partner_name or lead.contact_name,
                    'phone': lead.phone,
                    'email': lead.email_from,
                    'street': lead.street,
                })
            lead.write({'type': 'opportunity', 'partner_id': partner_id.id})
            if not lead.stage_id:
                stage = request.env['crm.stage'].search([], limit=1)
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
            lead = request.env['crm.lead'].browse(record_id)
            if not lead.exists() or lead.user_id.id != uid:
                return {'error': 'Not found or access denied'}
            so_orders = lead.order_ids.filtered(lambda s: s.state in ['sale'])
            if so_orders:
                return {'error': 'You cannot cancel this opportunity because the a sale order has already been generated '}
            lead.write({'type': 'lead', 'probability': 0})
            # if not lead.stage_id:
            stage = request.env['crm.stage'].search([('is_won', '=', False)])
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
            lead = request.env['crm.lead'].browse(record_id)
            if not lead.exists() or lead.user_id.id != uid:
                return {'error': 'Not found or access denied'}
            lead.action_set_won_rainbowman()
            return {'success': True}
        except Exception as e:
            _logger.exception("Mark won error")
            return {'error': str(e)}

    @http.route('/crm-portal/api/action/mark_lost/<int:record_id>', type='json', auth='user')
    def action_mark_lost(self, record_id, **kw):
        try:
            uid = request.env.uid
            lead = request.env['crm.lead'].browse(record_id)
            if not lead.exists() or lead.user_id.id != uid:
                return {'error': 'Not found or access denied'}
            lead.action_set_lost()
            return {'success': True}
        except Exception as e:
            _logger.exception("Mark lost error")
            return {'error': str(e)}

    @http.route('/crm-portal/api/action/create_quotation/<int:record_id>', type='json', auth='user')
    def action_create_quotation(self, record_id, **kw):
        try:
            uid = request.env.uid
            lead = request.env['crm.lead'].browse(record_id)
            sale_lead = request.env['sale.order'].search([
                ('opportunity_id', '=', lead.id), ('state', 'in', ['sale', 'sent'])
                ], limit=1)
            if not lead.exists() or lead.user_id.id != uid:
                return {'error': 'Not found or access denied'}
            if sale_lead.exists():
                return {'error': 'Sale Quotation or order has already been generated. Kindly confirm system admin to cancel or modify'}

            # Create sale order linked to this lead
            so_vals = {
                'partner_id': lead.partner_id.id if lead.partner_id else request.env['res.partner'].search([], limit=1).id,
                'opportunity_id': lead.id,
                'user_id': uid,
                'date_order': fields.Date.today(),
                'state': 'draft',
            }
            so = request.env['sale.order'].sudo().create(so_vals)
            so_lines = request.env['sale.order.line'].sudo().create({
                'order_id': so.id,
                'product_id': request.env.ref('crm_portal.crm_product_id').id,
                'product_uom_qty': 1,
                'name': lead.name,
                'price_unit': lead.expected_revenue,
            })
            _logger.info(f"SO ORDER WITH LINE CREATING {so_lines}")
            return {'success': True, 'sale_order_id': so.id, 'sale_order_name': so.name}
        except Exception as e:
            _logger.exception("Create quotation error")
            return {'error': str(e)}

    @http.route('/crm-portal/api/action/confirm_quotation/<int:sale_order_id>', type='json', auth='user')
    def action_confirm_quotation(self, sale_order_id, **kw):
        try:
            so = request.env['sale.order'].browse(sale_order_id)
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
            so = request.env['sale.order'].browse(sale_order_id)
            if not so.exists():
                return {'error': 'Sale order not found'}
            so.action_cancel()
            return {'success': True, 'state': so.state}
        except Exception as e:
            _logger.exception("Cancel quotation error")
            return {'error': str(e)}

    @http.route('/crm-portal/api/action/generate_invoice/<int:sale_order_id>', type='json', auth='user')
    def action_generate_invoice(self, sale_order_id, **kw):
        try:
            so = request.env['sale.order'].browse(sale_order_id)
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
            lead = request.env['crm.lead'].browse(record_id)
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
            lead = request.env['crm.lead'].browse(record_id)
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
        orders = request.env['sale.order'].search([('user_id', '=', uid)], order='create_date desc', limit=100)
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
