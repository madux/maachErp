# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _




class AccountReport(models.AbstractModel):
    _inherit = 'account.report'

    filter_branch = None

    @api.model
    def _init_filter_branch(self, options, previous_options=None):
        if not self.filter_branch:
            return

        options['branch'] = True
        options['branch_ids'] = previous_options and previous_options.get('branch_ids') or []
        selected_branch_ids = [int(partner) for partner in options['branch_ids']]
        selected_branches = selected_branch_ids and self.env['eha.branch'].browse(selected_branch_ids) or self.env['eha.branch']
        options['selected_branch_ids'] = selected_branches.mapped('name')


    # @api.model
    # def _get_options(self, previous_options=None):
    #     # removed this method for v16 
    #     # TODO: to be replaced after the analytic module is migrated or purchased
    #     # Create default options.
    #     options = {
    #         'unfolded_lines': previous_options and previous_options.get('unfolded_lines') or [],
    #     }

    #     # Multi-company is there for security purpose and can't be disabled by a filter.
    #     self._init_filter_multi_company(options, previous_options=previous_options)

    #     # Call _init_filter_date/_init_filter_comparison because the second one must be called after the first one.
    #     if self.filter_date:
    #         self._init_filter_date(options, previous_options=previous_options)
    #     if self.filter_comparison:
    #         self._init_filter_comparison(options, previous_options=previous_options)
    #     if self.filter_analytic:
    #         options['analytic'] = self.filter_analytic

    #     # if self.filter_branch:
    #     #     self._init_filter_branch(options, previous_options=previous_options)

    #     filter_list = [attr for attr in dir(self)
    #                    if (attr.startswith('filter_') or attr.startswith('order_')) and attr not in ('filter_date', 'filter_comparison') and len(attr) > 7 and not callable(getattr(self, attr))]
    #     for filter_key in filter_list:
    #         options_key = filter_key[7:]
    #         init_func = getattr(self, '_init_%s' % filter_key, None)
    #         if init_func:
    #             init_func(options, previous_options=previous_options)
    #         else:
    #             filter_opt = getattr(self, filter_key, None)
    #             if filter_opt is not None:
    #                 if previous_options and options_key in previous_options:
    #                     options[options_key] = previous_options[options_key]
    #                 else:
    #                     options[filter_key[7:]] = filter_opt
    #     return options


    def _set_context(self, options):
        ctx = self.env.context.copy()
        if options.get('date') and options['date'].get('date_from'):
            ctx['date_from'] = options['date']['date_from']
        if options.get('date'):
            ctx['date_to'] = options['date'].get('date_to') or options['date'].get('date')
        if options.get('all_entries') is not None:
            ctx['state'] = options.get('all_entries') and 'all' or 'posted'
        if options.get('journals'):
            ctx['journal_ids'] = [j.get('id') for j in options.get('journals') if j.get('selected')]
        company_ids = []
        if options.get('multi_company'):
            company_ids = [c.get('id') for c in options['multi_company'] if c.get('selected')]
            company_ids = company_ids if len(company_ids) > 0 else [c.get('id') for c in options['multi_company']]
        ctx['company_ids'] = len(company_ids) > 0 and company_ids or [self.env.company.id]

        if options.get('analytic_accounts'):
            ctx['analytic_account_ids'] = self.env['account.analytic.account'].browse([int(acc) for acc in options['analytic_accounts']])

        # if options.get('analytic_tags'):
        #     ctx['analytic_tag_ids'] = self.env['account.analytic.tag'].browse([int(t) for t in options['analytic_tags']])

        if options.get('partner_ids'):
            ctx['partner_ids'] = self.env['res.partner'].browse([int(partner) for partner in options['partner_ids']])

        if options.get('branch_ids'):
            ctx['branch_ids'] = self.env['eha.branch'].browse([int(branch) for branch in options['branch_ids']])

        if options.get('partner_categories'):
            ctx['partner_categories'] = self.env['res.partner.category'].browse([int(category) for category in options['partner_categories']])
        return ctx


    # def get_report_informations(self, options):
    #     '''
    #     return a dictionary of informations that will be needed by the js widget, manager_id, footnotes, html of report and searchview, ...
    #     '''
    #     options = self._get_options(options)

    #     searchview_dict = {'options': options, 'context': self.env.context}
    #     # Check if report needs analytic
        


    #     if options.get('analytic_accounts') is not None:
    #         options['selected_analytic_account_names'] = [self.env['account.analytic.account'].browse(int(account)).name for account in options['analytic_accounts']]
    #     # if options.get('analytic_tags') is not None:
    #     #     options['selected_analytic_tag_names'] = [self.env['account.analytic.tag'].browse(int(tag)).name for tag in options['analytic_tags']]
    #     if options.get('partner'):
    #         options['selected_partner_ids'] = [self.env['res.partner'].browse(int(partner)).name for partner in options['partner_ids']]
    #         options['selected_partner_categories'] = [self.env['res.partner.category'].browse(int(category)).name for category in options['partner_categories']]

    #     if options.get('branch'):
    #         options['selected_branch_ids'] = [self.env['eha.branch'].browse(int(branch)).name for branch in options['branch_ids']]

    #     # Check whether there are unposted entries for the selected period or not (if the report allows it)
    #     if options.get('date') and options.get('all_entries') is not None:
    #         date_to = options['date'].get('date_to') or options['date'].get('date') or fields.Date.today()
    #         period_domain = [('state', '=', 'draft'), ('date', '<=', date_to)]
    #         options['unposted_in_period'] = bool(self.env['account.move'].search_count(period_domain))

    #     if options.get('journals'):
    #         journals_selected = set(journal['id'] for journal in options['journals'] if journal.get('selected'))
    #         for journal_group in self.env['account.journal.group'].search([('company_id', '=', self.env.company.id)]):
    #             if journals_selected and journals_selected == set(self._get_filter_journals().ids) - set(journal_group.excluded_journal_ids.ids):
    #                 options['name_journal_group'] = journal_group.name
    #                 break
         
    #     report_manager = self._get_report_manager(options)
    #     info = {'options': options,
    #             'context': self.env.context,
    #             'report_manager_id': report_manager.id,
                
    #             'footnotes': [{'id': f.id, 'line': f.line, 'text': f.text} for f in report_manager.footnotes_ids],
    #             # 'buttons': self._get_reports_buttons_in_sequence(),
    #             'main_html': self.get_html(options),
    #             'searchview_html': self.env['ir.ui.view'].render_template(self._get_templates().get('search_template', 'account_report.search_template'), values=searchview_dict),
    #             }
    #     return info
    
    def get_report_informations(self, previous_options):
        """
        return a dictionary of information that will be consumed by the js widget, manager_id, footnotes, html of report and searchview, ...
        """
        self.ensure_one()

        if not previous_options:
            previous_options = {}

        options = self._get_options(previous_options)

        if not self.root_report_id:
            # This report has no root, so it IS a root. We might want to load a variant instead.

            if options['report_id'] != self.id:
                # Load the variant instead of the root report
                return self.env['account.report'].browse(options['report_id']).get_report_informations({**previous_options, 'report_id': options['report_id']})

        searchview_dict = {'options': options, 'context': self.env.context, 'report': self}

        ##############
        if options.get('analytic_accounts') is not None:
            options['selected_analytic_account_names'] = [self.env['account.analytic.account'].browse(int(account)).name for account in options['analytic_accounts']]
        # if options.get('analytic_tags') is not None:
        #     options['selected_analytic_tag_names'] = [self.env['account.analytic.tag'].browse(int(tag)).name for tag in options['analytic_tags']]
        if options.get('partner'):
            options['selected_partner_ids'] = [self.env['res.partner'].browse(int(partner)).name for partner in options['partner_ids']]
            options['selected_partner_categories'] = [self.env['res.partner.category'].browse(int(category)).name for category in options['partner_categories']]

        if options.get('branch'):
            options['selected_branch_ids'] = [self.env['eha.branch'].browse(int(branch)).name for branch in options['branch_ids']]

        if options.get('journals'):
            journals_selected = set(journal['id'] for journal in options['journals'] if journal.get('selected'))
            for journal_group in self.env['account.journal.group'].search([('company_id', '=', self.env.company.id)]):
                if journals_selected and journals_selected == set(self._get_filter_journals().ids) - set(journal_group.excluded_journal_ids.ids):
                    options['name_journal_group'] = journal_group.name
                    break
        ##############
        # Check whether there are unposted entries for the selected period or not (if the report allows it)
        if options.get('date') and options.get('all_entries') is not None:
            date_to = options['date'].get('date_to') or options['date'].get('date') or fields.Date.today()
            period_domain = [('state', '=', 'draft'), ('date', '<=', date_to)]
            options['unposted_in_period'] = bool(self.env['account.move'].search_count(period_domain))

        all_column_groups_expression_totals = self._compute_expression_totals_for_each_column_group(self.line_ids.expression_ids, options)
        lines = self._get_lines(options, all_column_groups_expression_totals)

        report_html = self.get_html(options, lines)

        # Convert all_column_groups_expression_totals to a json-friendly form (its keys are records)
        json_friendly_column_group_totals = self._get_json_friendly_column_group_totals(all_column_groups_expression_totals)

        report_manager = self._get_report_manager(options)
        info = {
            'options': options,
            'column_groups_totals': json_friendly_column_group_totals,
            'context': self.env.context,
            'report_manager_id': report_manager.id,
            'footnotes': [{'id': f.id, 'line': f.line, 'text': f.text} for f in report_manager.footnotes_ids],
            'main_html': report_html,
            'searchview_html': self.env['ir.ui.view']._render_template(self.search_template, values=searchview_dict),
        }

        return info
    
     
