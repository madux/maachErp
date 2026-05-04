# -*- coding: utf-8 -*-
"""
report_portal/controllers/report_portal.py
==========================================
Routes:
  GET  /report-portal                  → serves report_portal.html with injected user/company data
  POST /report-portal/dashboard        → JSON: KPI cards, branch chart, monthly trend
  POST /report-portal/data             → JSON: any report type (GL, TB, P&L, BS, Tax, Consolidated, Monthly)
  POST /report-portal/meta/branches    → JSON: branch list for a set of company_ids
  POST /report-portal/meta/accounts    → JSON: account list filtered by account_type + company_ids
  POST /report-portal/meta/companies   → JSON: company list available to the current user
"""

import json
import os
import logging
from datetime import date, datetime, timedelta

from dateutil.relativedelta import relativedelta

from odoo import http
from odoo.http import request
from odoo.modules.module import get_resource_path

_logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _fmt(val):
    """Comma-formatted float string, 2 dp."""
    try:
        return '{:,.2f}'.format(float(val or 0))
    except Exception:
        return '0.00'


def _parse_date(date_str, fallback=None):
    """Accept YYYY-MM-DD or MM/DD/YYYY or DD/MM/YYYY."""
    if not date_str:
        return fallback
    for fmt in ('%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y'):
        try:
            return datetime.strptime(date_str.strip(), fmt).date()
        except ValueError:
            continue
    return fallback


def _ids(raw):
    """Safely cast a list of values to list[int]."""
    try:
        return [int(x) for x in (raw or []) if x]
    except (TypeError, ValueError):
        return []


# Odoo 16 account_type → internal type list mapping
_TYPE_MAP = {
    'expense':   ['expense', 'expense_direct_cost'],
    'income':    ['income', 'income_other'],
    'asset':     ['asset_receivable', 'asset_cash', 'asset_current',
                  'asset_non_current', 'asset_prepayments', 'asset_fixed'],
    'liability': ['liability_payable', 'liability_credit_card',
                  'liability_current', 'liability_non_current'],
    'equity':    ['equity', 'equity_unaffected'],
}


# ─────────────────────────────────────────────────────────────────────────────
# Controller
# ─────────────────────────────────────────────────────────────────────────────

class ReportPortalController(http.Controller):

    # ── 1. Serve the HTML shell ───────────────────────────────────────
    @http.route('/report-portal', type='http', auth='user', methods=['GET'])
    def show_portal(self, **kw):
        """
        Reads report_portal.html from static/html/, injects a JSON meta block
        into <head> so the JS knows the current user, companies, and branches,
        then returns the raw HTML response.
        """
        file_path = get_resource_path('report_portal', 'static/html', 'report_portal.html')
        if not file_path or not os.path.exists(file_path):
            return request.make_response(
                '<h3>report_portal.html not found in static/html/</h3>',
                headers=[('Content-Type', 'text/html')]
            )

        with open(file_path, 'r', encoding='utf-8') as fh:
            html = fh.read()

        env  = request.env
        user = env.user

        # Companies accessible to this user
        companies = env['res.company'].sudo().search([])

        # Branches (guard: multi.branch may not be installed)
        branches = []
        if 'multi.branch' in env:
            branches = [
                {'id': b.id, 'name': b.name, 'company_id': b.company_id.id}
                for b in env['multi.branch'].sudo().search([])
            ]

        current_year = date.today().year

        meta = {
            'user_id':      user.id,
            'user_name':    user.name,
            'company_id':   user.company_id.id,
            'company_name': user.company_id.name,
            'company_street': user.company_id.street or '',
            'company_city':   user.company_id.city or '',
            'company_country': user.company_id.country_id.name or '',
            'companies': [
                {'id': c.id, 'name': c.name}
                for c in companies
            ],
            'branches':     branches,
            'current_year': current_year,
            'year_start':   f'{current_year}-01-01',
            'today':        date.today().isoformat(),
            'fiscal_years': list(range(current_year - 4, current_year + 1)),
        }

        # Inject meta tag just before </head>
        meta_tag = (
            f'<meta name="report-portal-meta" '
            f'content=\'{json.dumps(meta, ensure_ascii=False)}\'>\n'
        )
        html = html.replace('</head>', meta_tag + '</head>', 1)

        return request.make_response(
            html,
            headers=[('Content-Type', 'text/html; charset=utf-8')]
        )

    # ── 2. Dashboard KPIs + charts ────────────────────────────────────
    @http.route('/report-portal/dashboard', type='json', auth='user', methods=['POST'])
    def dashboard(self, **post):
        """
        Returns:
          kpis          : { total_income, total_expense, net_pl, total_payable, tx_count, net_positive }
          branch_chart  : [ { branch, income, expense } ]
          company_chart : [ { name, expense, pct } ]
          monthly       : [ { month, income, expense } ]   ← last 6 months
          top_accounts  : [ { code, name, amount } ]       ← top 6 expense accounts
        """
        env         = request.env
        date_from   = _parse_date(post.get('date_from'), date(date.today().year, 1, 1))
        date_to     = _parse_date(post.get('date_to'),   date.today())
        company_ids = _ids(post.get('company_ids'))
        branch_ids  = _ids(post.get('branch_ids'))

        AML = env['account.move.line'].sudo()

        base = [
            ('move_id.state', '=', 'posted'),
            ('date', '>=', date_from),
            ('date', '<=', date_to),
        ]
        if company_ids:
            base.append(('company_id', 'in', company_ids))
        if branch_ids:
            base.append(('move_id.branch_id', 'in', branch_ids))

        # ── KPIs ───────────────────────────────────────────────────────
        inc_lines = AML.search(base + [('account_id.account_type', 'in', ['income', 'income_other'])])
        total_income = abs(sum(inc_lines.mapped('balance')))

        exp_lines = AML.search(base + [('account_id.account_type', 'in', ['expense', 'expense_direct_cost'])])
        total_expense = sum(exp_lines.mapped('balance'))

        net_pl = total_income - total_expense

        pay_domain = [
            ('move_id.state', '=', 'posted'),
            ('account_id.account_type', '=', 'liability_payable'),
            ('reconciled', '=', False),
        ]
        if company_ids:
            pay_domain.append(('company_id', 'in', company_ids))
        payable_lines = AML.search(pay_domain)
        total_payable = abs(sum(payable_lines.mapped('amount_residual')))

        # transaction count = distinct posted moves
        moves = env['account.move'].sudo().search(
            [('state', '=', 'posted'),
             ('date', '>=', date_from),
             ('date', '<=', date_to)]
            + ([('company_id', 'in', company_ids)] if company_ids else [])
        )
        tx_count = len(moves)

        # ── Branch chart ───────────────────────────────────────────────
        branch_chart = []
        if 'multi.branch' in env:
            b_domain = []
            if company_ids:
                b_domain.append(('company_id', 'in', company_ids))
            all_branches = env['multi.branch'].sudo().search(b_domain)
            for br in all_branches:
                b_base = base + [('move_id.branch_id', '=', br.id)]
                b_inc = abs(sum(AML.search(
                    b_base + [('account_id.account_type', 'in', ['income', 'income_other'])]
                ).mapped('balance')))
                b_exp = sum(AML.search(
                    b_base + [('account_id.account_type', 'in', ['expense', 'expense_direct_cost'])]
                ).mapped('balance'))
                if b_inc or b_exp:
                    branch_chart.append({
                        'branch':  br.name,
                        'income':  round(b_inc, 2),
                        'expense': round(b_exp, 2),
                    })

        # ── Company chart ──────────────────────────────────────────────
        company_chart = []
        all_companies = env['res.company'].sudo().search(
            [('id', 'in', company_ids)] if company_ids else []
        )
        total_co_exp = 0.0
        co_exp_raw = []
        for co in all_companies:
            c_exp = sum(AML.search(
                [('move_id.state', '=', 'posted'),
                 ('date', '>=', date_from), ('date', '<=', date_to),
                 ('company_id', '=', co.id),
                 ('account_id.account_type', 'in', ['expense', 'expense_direct_cost'])]
            ).mapped('balance'))
            if c_exp:
                co_exp_raw.append({'name': co.name, 'expense': round(c_exp, 2)})
                total_co_exp += c_exp
        for item in co_exp_raw:
            item['pct'] = round((item['expense'] / total_co_exp * 100) if total_co_exp else 0, 1)
            company_chart.append(item)

        # ── Monthly trend (last 6 months) ──────────────────────────────
        monthly = []
        ref_end = date_to
        for i in range(5, -1, -1):
            m_start = (ref_end.replace(day=1) - relativedelta(months=i))
            m_end   = m_start + relativedelta(months=1) - timedelta(days=1)
            m_base  = [
                ('move_id.state', '=', 'posted'),
                ('date', '>=', m_start), ('date', '<=', m_end),
            ]
            if company_ids:
                m_base.append(('company_id', 'in', company_ids))
            m_inc = abs(sum(AML.search(
                m_base + [('account_id.account_type', 'in', ['income', 'income_other'])]
            ).mapped('balance')))
            m_exp = sum(AML.search(
                m_base + [('account_id.account_type', 'in', ['expense', 'expense_direct_cost'])]
            ).mapped('balance'))
            monthly.append({'month': m_start.strftime('%b %Y'), 'income': round(m_inc, 2), 'expense': round(m_exp, 2)})

        # ── Top expense accounts ────────────────────────────────────────
        acc_exp = {}
        for line in exp_lines:
            acc = line.account_id
            acc_exp.setdefault(acc.code, {'code': acc.code, 'name': acc.name, 'amount': 0.0})
            acc_exp[acc.code]['amount'] += line.balance
        top_accounts = sorted(acc_exp.values(), key=lambda x: x['amount'], reverse=True)[:8]
        for t in top_accounts:
            t['amount'] = round(t['amount'], 2)

        return {
            'status': True,
            'kpis': {
                'total_income':  round(total_income, 2),
                'total_expense': round(total_expense, 2),
                'net_pl':        round(net_pl, 2),
                'total_payable': round(total_payable, 2),
                'tx_count':      tx_count,
                'net_positive':  net_pl >= 0,
            },
            'branch_chart':  branch_chart,
            'company_chart': company_chart,
            'monthly':       monthly,
            'top_accounts':  top_accounts,
        }

    # ── 3. Report data dispatcher ──────────────────────────────────────
    @http.route('/report-portal/data', type='json', auth='user', methods=['POST'])
    def report_data(self, **post):
        """
        Dispatches to the correct report builder.
        Accepted post keys:
          report_type, date_from, date_to, company_ids, branch_ids, account_type, account_ids
        """
        report_type  = post.get('report_type', 'monthly_expense')
        date_from    = _parse_date(post.get('date_from'), date(date.today().year, 1, 1))
        date_to      = _parse_date(post.get('date_to'),   date.today())
        company_ids  = _ids(post.get('company_ids'))
        branch_ids   = _ids(post.get('branch_ids'))
        account_type = post.get('account_type', '')
        account_ids  = _ids(post.get('account_ids'))

        builders = {
            'monthly_expense': self._monthly_expense,
            'general_ledger':  self._general_ledger,
            'trial_balance':   self._trial_balance,
            'profit_loss':     self._profit_loss,
            'balance_sheet':   self._balance_sheet,
            'tax_report':      self._tax_report,
            'consolidated':    self._consolidated,
        }
        builder = builders.get(report_type)
        if not builder:
            return {'status': False, 'message': f'Unknown report type: {report_type}'}

        try:
            result = builder(date_from, date_to, company_ids, branch_ids, account_type, account_ids)
            result['status'] = True
            return result
        except Exception as exc:
            _logger.exception('Report error [%s]', report_type)
            return {'status': False, 'message': str(exc)}

    # ── 4. Meta helpers ────────────────────────────────────────────────
    @http.route('/report-portal/meta/branches', type='json', auth='user', methods=['POST'])
    def meta_branches(self, **post):
        company_ids = _ids(post.get('company_ids'))
        if 'multi.branch' not in request.env:
            return {'status': True, 'branches': []}
        domain = [('company_id', 'in', company_ids)] if company_ids else []
        branches = request.env['multi.branch'].sudo().search(domain)
        return {
            'status': True,
            'branches': [{'id': b.id, 'name': b.name} for b in branches],
        }

    @http.route('/report-portal/meta/accounts', type='json', auth='user', methods=['POST'])
    def meta_accounts(self, **post):
        account_type = post.get('account_type', '')
        company_ids  = _ids(post.get('company_ids'))
        domain = []
        if account_type and account_type in _TYPE_MAP:
            domain.append(('account_type', 'in', _TYPE_MAP[account_type]))
        if company_ids:
            domain.append(('company_id', 'in', company_ids))
        accounts = request.env['account.account'].sudo().search(domain, limit=400)
        return {
            'status': True,
            'accounts': [{'id': a.id, 'name': f'{a.code} – {a.name}'} for a in accounts],
        }

    @http.route('/report-portal/meta/companies', type='json', auth='user', methods=['POST'])
    def meta_companies(self, **post):
        companies = request.env['res.company'].sudo().search([])
        return {
            'status': True,
            'companies': [{'id': c.id, 'name': c.name} for c in companies],
        }

    # ==========================================================================
    # PRIVATE REPORT BUILDERS
    # ==========================================================================

    def _base_domain(self, date_from, date_to, company_ids, branch_ids, account_type='', account_ids=None):
        domain = [
            ('move_id.state', '=', 'posted'),
            ('date', '>=', date_from),
            ('date', '<=', date_to),
        ]
        if company_ids:
            domain.append(('company_id', 'in', company_ids))
        if branch_ids:
            domain.append(('move_id.branch_id', 'in', branch_ids))
        if account_type and account_type in _TYPE_MAP:
            domain.append(('account_id.account_type', 'in', _TYPE_MAP[account_type]))
        if account_ids:
            domain.append(('account_id', 'in', account_ids))
        return domain

    # ── Monthly Expenditure ────────────────────────────────────────────
    def _monthly_expense(self, date_from, date_to, company_ids, branch_ids, account_type, account_ids):
        env      = request.env
        eff_type = account_type or 'expense'
        domain   = self._base_domain(date_from, date_to, company_ids, branch_ids, eff_type, account_ids)
        lines    = env['account.move.line'].sudo().search(domain, order='date asc')

        months = []
        cur = date_from.replace(day=1)
        while cur <= date_to:
            months.append(cur.strftime('%b %Y'))
            cur += relativedelta(months=1)

        acc_data = {}
        for line in lines:
            acc  = line.account_id
            mlbl = line.date.strftime('%b %Y')
            if acc.code not in acc_data:
                acc_data[acc.code] = {'code': acc.code, 'name': acc.name,
                                      'months': {m: 0.0 for m in months}, 'total': 0.0}
            if mlbl in acc_data[acc.code]['months']:
                acc_data[acc.code]['months'][mlbl] += line.balance
                acc_data[acc.code]['total']        += line.balance

        columns = ['Chart of Account', 'Description'] + months + ['TOTAL']
        rows    = []
        grand   = {m: 0.0 for m in months}
        grand_total = 0.0

        for acc in sorted(acc_data.values(), key=lambda x: x['code']):
            row = [acc['code'], acc['name']]
            for m in months:
                v = acc['months'][m]
                row.append(_fmt(v))
                grand[m] += v
            row.append(_fmt(acc['total']))
            grand_total += acc['total']
            rows.append({'cells': row, 'is_group': False, 'detail_lines': []})

        rows.append({'cells': ['', 'GRAND TOTAL'] + [_fmt(grand[m]) for m in months] + [_fmt(grand_total)],
                     'is_group': True, 'detail_lines': []})

        return {
            'title':   f'Monthly Expenditure – {date_from:%b %Y} to {date_to:%b %Y}',
            'columns': columns, 'rows': rows,
            'summary': {'Grand Total': _fmt(grand_total), 'Period': f'{date_from} → {date_to}'},
        }

    # ── General Ledger ─────────────────────────────────────────────────
    def _general_ledger(self, date_from, date_to, company_ids, branch_ids, account_type, account_ids):
        env    = request.env
        AML    = env['account.move.line'].sudo()
        domain = self._base_domain(date_from, date_to, company_ids, branch_ids, account_type, account_ids)
        lines  = AML.search(domain, order='account_id, date, id')

        columns = ['Date', 'Reference', 'Partner', 'Journal', 'Debit', 'Credit', 'Balance']
        rows    = []
        current_acc = None
        running     = 0.0
        total_dr = total_cr = 0.0

        for line in lines:
            acc = line.account_id
            if acc.id != current_acc:
                ob = AML.search([('account_id', '=', acc.id),
                                  ('move_id.state', '=', 'posted'),
                                  ('date', '<', date_from)]
                                 + ([('company_id', 'in', company_ids)] if company_ids else []))
                running     = sum(ob.mapped('balance'))
                current_acc = acc.id
                rows.append({
                    'cells': [acc.code, acc.name, '', '', '', '', _fmt(running)],
                    'is_group': True,
                    'detail_lines': [],
                })
            running  += line.debit - line.credit
            total_dr += line.debit
            total_cr += line.credit
            rows.append({
                'cells': [
                    line.date.strftime('%Y-%m-%d'),
                    line.move_id.name or '',
                    line.partner_id.name or '',
                    line.journal_id.name or '',
                    _fmt(line.debit),
                    _fmt(line.credit),
                    _fmt(running),
                ],
                'is_group': False, 'detail_lines': [],
            })

        return {
            'title':   f'General Ledger – {date_from} to {date_to}',
            'columns': columns, 'rows': rows,
            'summary': {'Total Debit': _fmt(total_dr), 'Total Credit': _fmt(total_cr),
                        'Period': f'{date_from} → {date_to}'},
        }

    # ── Trial Balance ──────────────────────────────────────────────────
    def _trial_balance(self, date_from, date_to, company_ids, branch_ids, account_type, account_ids):
        env  = request.env
        AML  = env['account.move.line'].sudo()
        acc_domain = []
        if company_ids:
            acc_domain.append(('company_id', 'in', company_ids))
        if account_ids:
            acc_domain.append(('id', 'in', account_ids))
        accounts = env['account.account'].sudo().search(acc_domain)

        columns = ['Code', 'Account Name', 'Opening Dr', 'Opening Cr',
                   'Period Dr', 'Period Cr', 'Closing Dr', 'Closing Cr']
        rows   = []
        totals = {k: 0.0 for k in ['op_dr','op_cr','per_dr','per_cr','cl_dr','cl_cr']}

        for acc in accounts.sorted('code'):
            base = [('account_id','=',acc.id),('move_id.state','=','posted')]
            if company_ids:
                base.append(('company_id','in',company_ids))
            if branch_ids:
                base.append(('move_id.branch_id','in',branch_ids))

            ob     = AML.search(base + [('date','<',date_from)])
            per    = AML.search(base + [('date','>=',date_from),('date','<=',date_to)])
            if not ob and not per:
                continue

            op_bal = sum(ob.mapped('balance'))
            op_dr  = max(op_bal, 0);  op_cr = abs(min(op_bal, 0))
            per_dr = sum(per.mapped('debit'))
            per_cr = sum(per.mapped('credit'))
            cl_bal = op_bal + per_dr - per_cr
            cl_dr  = max(cl_bal, 0);  cl_cr = abs(min(cl_bal, 0))

            rows.append({'cells': [acc.code, acc.name,
                                   _fmt(op_dr), _fmt(op_cr),
                                   _fmt(per_dr), _fmt(per_cr),
                                   _fmt(cl_dr),  _fmt(cl_cr)],
                         'is_group': False, 'detail_lines': []})

            for k, v in [('op_dr',op_dr),('op_cr',op_cr),('per_dr',per_dr),
                          ('per_cr',per_cr),('cl_dr',cl_dr),('cl_cr',cl_cr)]:
                totals[k] += v

        rows.append({'cells': ['','TOTAL',
                                _fmt(totals['op_dr']),_fmt(totals['op_cr']),
                                _fmt(totals['per_dr']),_fmt(totals['per_cr']),
                                _fmt(totals['cl_dr']),_fmt(totals['cl_cr'])],
                     'is_group': True, 'detail_lines': []})

        balanced = abs(totals['cl_dr'] - totals['cl_cr']) < 0.01
        return {
            'title':   f'Trial Balance – {date_from} to {date_to}',
            'columns': columns, 'rows': rows,
            'summary': {'Closing Debit': _fmt(totals['cl_dr']),
                        'Closing Credit': _fmt(totals['cl_cr']),
                        'Balanced': 'Yes ✔' if balanced else 'No ✘'},
        }

    # ── Profit & Loss ──────────────────────────────────────────────────
    def _profit_loss(self, date_from, date_to, company_ids, branch_ids, account_type, account_ids):
        env = request.env
        AML = env['account.move.line'].sudo()
        base = [('move_id.state','=','posted'),('date','>=',date_from),('date','<=',date_to)]
        if company_ids:
            base.append(('company_id','in',company_ids))
        if branch_ids:
            base.append(('move_id.branch_id','in',branch_ids))

        columns     = ['Code', 'Account Name', 'Amount']
        rows        = []
        total_inc   = total_exp = 0.0

        for section, types, sign in [
            ('INCOME',   ['income','income_other'],               -1),
            ('EXPENSES', ['expense','expense_direct_cost'],        1),
        ]:
            lines = AML.search(base + [('account_id.account_type','in',types)])
            acc_map = {}
            for line in lines:
                acc = line.account_id
                acc_map.setdefault(acc.code, {'code':acc.code,'name':acc.name,'bal':0.0})
                acc_map[acc.code]['bal'] += line.balance

            sec_total = 0.0
            rows.append({'cells':[section,'',''],'is_group':True,'detail_lines':[]})
            for acc in sorted(acc_map.values(), key=lambda x: x['code']):
                amount    = abs(acc['bal']) if sign == -1 else acc['bal']
                sec_total += amount
                rows.append({'cells':[acc['code'],acc['name'],_fmt(amount)],
                             'is_group':False,'detail_lines':[]})
            rows.append({'cells':['',f'Total {section}',_fmt(sec_total)],
                         'is_group':True,'detail_lines':[]})
            if sign == -1:
                total_inc = sec_total
            else:
                total_exp = sec_total

        net = total_inc - total_exp
        rows.append({'cells':['','NET PROFIT / (LOSS)',_fmt(net)],'is_group':True,'detail_lines':[]})

        return {
            'title':   f'Profit & Loss – {date_from} to {date_to}',
            'columns': columns, 'rows': rows,
            'summary': {'Total Income': _fmt(total_inc), 'Total Expense': _fmt(total_exp),
                        'Net P&L': _fmt(net), 'Profitable': 'Yes' if net >= 0 else 'No'},
        }

    # ── Balance Sheet ──────────────────────────────────────────────────
    def _balance_sheet(self, date_from, date_to, company_ids, branch_ids, account_type, account_ids):
        env = request.env
        AML = env['account.move.line'].sudo()
        base = [('move_id.state','=','posted'),('date','<=',date_to)]
        if company_ids:
            base.append(('company_id','in',company_ids))
        if branch_ids:
            base.append(('move_id.branch_id','in',branch_ids))

        columns  = ['Code', 'Account Name', 'Balance']
        rows     = []
        sec_tots = {}

        for section, types in [
            ('ASSETS',      ['asset_receivable','asset_cash','asset_current',
                             'asset_non_current','asset_prepayments','asset_fixed']),
            ('LIABILITIES', ['liability_payable','liability_credit_card',
                             'liability_current','liability_non_current']),
            ('EQUITY',      ['equity','equity_unaffected']),
        ]:
            lines = AML.search(base + [('account_id.account_type','in',types)])
            acc_map = {}
            for line in lines:
                acc = line.account_id
                acc_map.setdefault(acc.code,{'code':acc.code,'name':acc.name,'bal':0.0})
                acc_map[acc.code]['bal'] += line.balance

            s_tot = 0.0
            rows.append({'cells':[section,'',''],'is_group':True,'detail_lines':[]})
            for acc in sorted(acc_map.values(), key=lambda x: x['code']):
                s_tot += acc['bal']
                rows.append({'cells':[acc['code'],acc['name'],_fmt(acc['bal'])],
                             'is_group':False,'detail_lines':[]})
            rows.append({'cells':['',f'Total {section}',_fmt(s_tot)],'is_group':True,'detail_lines':[]})
            sec_tots[section] = s_tot

        ta = sec_tots.get('ASSETS',0)
        tl = sec_tots.get('LIABILITIES',0)
        te = sec_tots.get('EQUITY',0)
        balanced = abs(ta - (tl + te)) < 0.01
        _logger.info(f"""Balance sheet info:
         datefrom {date_from} dateto: {date_to} company: {company_ids} branch: {branch_ids} acctype: {account_type} {account_ids} 
         base domain: {base}""")
        
        return {
            'title':   f'Balance Sheet as of {date_to}',
            'columns': columns, 'rows': rows,
            'summary': {'Total Assets': _fmt(ta), 'Total Liabilities': _fmt(tl),
                        'Total Equity': _fmt(te),
                        'Balanced': 'Yes ✔' if balanced else 'No ✘'},
        }


    # ── Tax Report ─────────────────────────────────────────────────────
    def _tax_report(self, date_from, date_to, company_ids, branch_ids, account_type, account_ids):
        env = request.env
        AML = env['account.move.line'].sudo()

        base = [('move_id.state','=','posted'),('date','>=',date_from),('date','<=',date_to)]
        if company_ids:
            base.append(('company_id','in',company_ids))
        if branch_ids:
            base.append(('move_id.branch_id','in',branch_ids))

        tax_lines  = AML.search(base + [('tax_ids','!=',False)])
        tline_rows = AML.search(base + [('tax_line_id','!=',False)])

        tax_map = {}
        for line in tax_lines:
            for tax in line.tax_ids:
                tax_map.setdefault(tax.name,{'base':0.0,'tax_amount':0.0})
                tax_map[tax.name]['base'] += abs(line.balance)
        for tl in tline_rows:
            name = tl.tax_line_id.name
            tax_map.setdefault(name,{'base':0.0,'tax_amount':0.0})
            tax_map[name]['tax_amount'] += abs(tl.balance)

        columns     = ['Tax Name','Base Amount','Tax Amount','Total']
        rows        = []
        grand_base  = grand_tax = 0.0

        for name, vals in sorted(tax_map.items()):
            total = vals['base'] + vals['tax_amount']
            rows.append({'cells':[name,_fmt(vals['base']),_fmt(vals['tax_amount']),_fmt(total)],
                         'is_group':False,'detail_lines':[]})
            grand_base += vals['base']
            grand_tax  += vals['tax_amount']

        rows.append({'cells':['TOTAL',_fmt(grand_base),_fmt(grand_tax),_fmt(grand_base+grand_tax)],
                     'is_group':True,'detail_lines':[]})

        return {
            'title':   f'Tax Report – {date_from} to {date_to}',
            'columns': columns, 'rows': rows,
            'summary': {'Total Base': _fmt(grand_base), 'Total Tax': _fmt(grand_tax),
                        'Grand Total': _fmt(grand_base+grand_tax)},
        }

    # ── Consolidated District Report ───────────────────────────────────
    def _consolidated(self, date_from, date_to, company_ids, branch_ids, account_type, account_ids):
        env      = request.env
        AML      = env['account.move.line'].sudo()
        eff_type = account_type or 'expense'

        # Resolve branch columns
        if 'multi.branch' in env:
            b_dom = []
            if company_ids:
                b_dom.append(('company_id','in',company_ids))
            if branch_ids:
                b_dom.append(('id','in',branch_ids))
            branches = env['multi.branch'].sudo().search(b_dom)
        else:
            branches = []

        branch_names  = [b.name for b in branches]
        branch_id_map = {b.id: b.name for b in branches}
        if branches:
            branch_names.append('UNASSIGNED')

        base = [('move_id.state','=','posted'),('date','>=',date_from),('date','<=',date_to)]
        if company_ids:
            base.append(('company_id','in',company_ids))

        full_domain = base + [('account_id.account_type','in',_TYPE_MAP.get(eff_type,[eff_type]))]
        if account_ids:
            full_domain.append(('account_id','in',account_ids))

        all_lines = AML.search(full_domain, order='account_id, date')

        columns = ['Chart of Account','Description'] + branch_names + ['TOTAL REV.','TOTAL EXP.','BALANCE']

        acc_data = {}
        for line in all_lines:
            acc = line.account_id
            if acc.code not in acc_data:
                acc_data[acc.code] = {
                    'code': acc.code, 'name': acc.name, 'acc_id': acc.id,
                    'branches': {bn: 0.0 for bn in branch_names},
                    'detail_lines': [],
                }
            bf = getattr(line.move_id, 'branch_id', None)
            bname = branch_id_map.get(bf.id, 'UNASSIGNED') if bf else 'UNASSIGNED'
            if bname in acc_data[acc.code]['branches']:
                acc_data[acc.code]['branches'][bname] += line.balance
            acc_data[acc.code]['detail_lines'].append({
                'date':    line.date.strftime('%Y-%m-%d'),
                'desc':    line.name or line.move_id.name or '',
                'ref':     line.move_id.ref or '',
                'partner': line.partner_id.name or '',
                'branch':  bname,
                'amount':  _fmt(line.balance),
                'raw':     line.balance,
            })

        rows       = []
        grand      = {bn: 0.0 for bn in branch_names}
        grand_rev  = grand_exp = 0.0

        for acc in sorted(acc_data.values(), key=lambda x: x['code']):
            acc_total = 0.0
            b_totals  = {}
            for bn in branch_names:
                v = acc['branches'][bn]
                b_totals[bn] = v
                grand[bn]   += v
                acc_total   += v

            t_rev = abs(min(acc_total, 0))
            t_exp = max(acc_total, 0)
            grand_rev += t_rev;  grand_exp += t_exp

            cells = [acc['code'], acc['name']] + \
                    [_fmt(b_totals[bn]) for bn in branch_names] + \
                    [_fmt(t_rev), _fmt(t_exp), _fmt(t_rev - t_exp)]

            rows.append({'cells': cells, 'is_group': True,
                         'detail_lines': acc['detail_lines']})

        rows.append({
            'cells': ['','GRAND TOTAL'] +
                     [_fmt(grand[bn]) for bn in branch_names] +
                     [_fmt(grand_rev), _fmt(grand_exp), _fmt(grand_rev-grand_exp)],
            'is_group': True, 'detail_lines': [],
        })

        return {
            'title':   f'Consolidated District Report – {date_from:%b %Y} to {date_to:%b %Y}',
            'columns': columns, 'rows': rows,
            'summary': {'Total Revenue': _fmt(grand_rev), 'Total Expense': _fmt(grand_exp),
                        'Balance': _fmt(grand_rev-grand_exp),
                        'Period':  f'{date_from} → {date_to}'},
        }
