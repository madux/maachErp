# -*- coding: utf-8 -*-

import copy
import re
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.osv import expression
from odoo.tools.misc import formatLang, format_date, parse_date
from odoo.tools import float_compare, float_is_zero
from odoo.exceptions import UserError

import re
from math import copysign


class AccountReconciliationInherit(models.AbstractModel):
    _inherit = 'account.reconciliation.widget'

    @api.model
    def get_bank_statement_data(self, bank_statement_line_ids, srch_domain=[]):
        """ Get statement lines of the specified statements or all unreconciled
            statement lines and try to automatically reconcile them / find them
            a partner.
            Return ids of statement lines left to reconcile and other data for
            the reconciliation widget.

            :param bank_statement_line_ids: ids of the bank statement lines
        """
        if not bank_statement_line_ids:
            return {}
        suspense_moves_mode = self._context.get('suspense_moves_mode')
        bank_statements = self.env['account.bank.statement.line'].browse(
            bank_statement_line_ids).mapped('statement_id')
        query = '''
             SELECT line.id
             FROM account_bank_statement_line line
             LEFT JOIN res_partner p on p.id = line.partner_id
             WHERE line.account_id IS NULL
             AND line.amount != 0.0
             AND line.id IN %(ids)s
             {cond}
             GROUP BY line.id
        '''.format(
            cond=not suspense_moves_mode and "AND NOT EXISTS (SELECT 1 from account_move_line aml WHERE aml.statement_line_id = line.id)" or "",
        )
        self.env.cr.execute(query, {'ids': tuple(bank_statement_line_ids)})
        domain = [['id', 'in', [
            line.get('id') for line in self.env.cr.dictfetchall()]]] + srch_domain
        bank_statement_lines = self.env['account.bank.statement.line'].search(
            domain)
        results = self.get_bank_statement_line_data(bank_statement_lines.ids)
        bank_statement_lines_left = self.env['account.bank.statement.line'].browse(
            [line['st_line']['id'] for line in results['lines']])
        bank_statements_left = bank_statement_lines_left.mapped('statement_id')
        results.update({
            'statement_name': len(bank_statements_left) == 1 and bank_statements_left.name or False,
            'journal_id': bank_statements and bank_statements[0].journal_id.id or False,
            'notifications': []
        })

        if len(results['lines']) < len(bank_statement_lines):
            results['notifications'].append({
                'type': 'info',
                'template': 'reconciliation.notification.reconciled',
                'reconciled_aml_ids': results['reconciled_aml_ids'],
                'nb_reconciled_lines': results['value_min'],
                'details': {
                    'name': _('Journal Items'),
                    'model': 'account.move.line',
                    'ids': results['reconciled_aml_ids'],
                }
            })

        return results

class AccountReconcileModelInherit(models.Model):
    _inherit = 'account.reconcile.model'

    def _get_invoice_matching_query(self, st_lines, excluded_ids=None, partner_map=None):
        ''' Get the query applying all rules trying to match existing entries with the given statement lines.
        :param st_lines:        Account.bank.statement.lines recordset.
        :param excluded_ids:    Account.move.lines to exclude.
        :param partner_map:     Dict mapping each line with new partner eventually.
        :return:                (query, params)
        '''
        if any(m.rule_type != 'invoice_matching' for m in self):
            raise UserError(_('Programmation Error: Can\'t call _get_invoice_matching_query() for different rules than \'invoice_matching\''))

        queries = []
        all_params = []
        for rule in self:
            # N.B: 'communication_flag' is there to distinguish invoice matching through the number/reference
            # (higher priority) from invoice matching using the partner (lower priority).
            query = r'''
            SELECT
                %s                                  AS sequence,
                %s                                  AS model_id,
                st_line.id                          AS id,
                aml.id                              AS aml_id,
                aml.currency_id                     AS aml_currency_id,
                aml.date_maturity                   AS aml_date_maturity,
                aml.amount_residual                 AS aml_amount_residual,
                aml.amount_residual_currency        AS aml_amount_residual_currency,
                aml.balance                         AS aml_balance,
                aml.amount_currency                 AS aml_amount_currency,
                account.internal_type               AS account_internal_type,
                ''' + rule._get_select_communication_flag() + r''', ''' + rule._get_select_payment_reference_flag() + r'''
            FROM account_bank_statement_line st_line
            LEFT JOIN account_journal journal       ON journal.id = st_line.journal_id
            LEFT JOIN jnl_precision                 ON jnl_precision.journal_id = journal.id
            LEFT JOIN res_company company           ON company.id = st_line.company_id
            LEFT JOIN partners_table line_partner   ON line_partner.line_id = st_line.id
            , account_move_line aml
            LEFT JOIN account_move move             ON move.id = aml.move_id AND move.state = 'posted'
            LEFT JOIN account_account account       ON account.id = aml.account_id
            WHERE st_line.id IN %s
                AND aml.company_id = st_line.company_id
                AND (
                        -- the field match_partner of the rule might enforce the second part of
                        -- the OR condition, later in _apply_conditions()
                        line_partner.partner_id = 0
                        OR
                        aml.partner_id = line_partner.partner_id
                    )
                AND CASE WHEN st_line.amount > 0.0
                         THEN aml.balance > 0
                         ELSE aml.balance < 0
                    END

                -- if there is a partner, propose all aml of the partner, otherwise propose only the ones
                -- matching the statement line communication
                -- "case when" used to enforce evaluation order (performance optimization)
                AND (CASE WHEN
                (
                    (
                    -- blue lines appearance conditions
                    aml.account_id IN (journal.default_credit_account_id, journal.default_debit_account_id)
                    AND aml.statement_id IS NULL
                    AND (
                        company.account_bank_reconciliation_start IS NULL
                        OR
                        aml.date > company.account_bank_reconciliation_start
                        )
                    )
                    AND (
                        move.state = 'posted'
                        OR
                        ((move.state = 'draft' OR move.state IS NULL) AND journal.post_at = 'bank_rec')
                    )
                    OR
                    (
                    -- black lines appearance conditions
                    account.reconcile IS TRUE
                    AND aml.reconciled IS NOT TRUE
                    AND move.state = 'posted'
                    )
                ) 
                THEN (CASE WHEN
                (
                    (
                        line_partner.partner_id != 0
                        AND
                        aml.partner_id = line_partner.partner_id
                    )
                    OR
                    (
                        line_partner.partner_id = 0
                        AND
                        substring(REGEXP_REPLACE(st_line.name, '[^0-9|^\s]', '', 'g'), '\S(?:.*\S)*') != ''
                        AND
                        (
                            (
                                aml.name IS NOT NULL
                                AND
                                substring(REGEXP_REPLACE(aml.name, '[^0-9|^\s]', '', 'g'), '\S(?:.*\S)*') != ''
                                AND
                                    regexp_split_to_array(substring(REGEXP_REPLACE(aml.name, '[^0-9|^\s]', '', 'g'), '\S(?:.*\S)*'),'\s+')
                                    && regexp_split_to_array(substring(REGEXP_REPLACE(st_line.name, '[^0-9|^\s]', '', 'g'), '\S(?:.*\S)*'), '\s+')
                            )
                            OR
                                regexp_split_to_array(substring(REGEXP_REPLACE(move.name, '[^0-9|^\s]', '', 'g'), '\S(?:.*\S)*'),'\s+')
                                && regexp_split_to_array(substring(REGEXP_REPLACE(st_line.name, '[^0-9|^\s]', '', 'g'), '\S(?:.*\S)*'), '\s+')
                            OR
                            (
                                move.ref IS NOT NULL
                                AND
                                substring(REGEXP_REPLACE(move.ref, '[^0-9|^\s]', '', 'g'), '\S(?:.*\S)*') != ''
                                AND
                                    regexp_split_to_array(substring(REGEXP_REPLACE(move.ref, '[^0-9|^\s]', '', 'g'), '\S(?:.*\S)*'),'\s+')
                                    && regexp_split_to_array(substring(REGEXP_REPLACE(st_line.name, '[^0-9|^\s]', '', 'g'), '\S(?:.*\S)*'), '\s+')
                            )
                            OR
                            (
                                move.ref IS NOT NULL
                                AND
                                regexp_replace(move.ref, '\s+', '', 'g') = regexp_replace(st_line.name, '\s+', '', 'g')
                            )
                        )
                    )
                )
                THEN 1 END) END) = 1
            '''
            # Filter on the same currency.
            if rule.match_same_currency:
                query += '''
                    AND COALESCE(st_line.currency_id, journal.currency_id, company.currency_id) = COALESCE(aml.currency_id, company.currency_id)
                '''

            params = [rule.sequence, rule.id, tuple(st_lines.ids)]
            # Filter out excluded account.move.line.
            if excluded_ids:
                query += 'AND aml.id NOT IN %s'
                params += [tuple(excluded_ids)]
            query, params = rule._apply_conditions(query, params)
            queries.append(query)
            all_params += params
        full_query = self._get_with_tables(st_lines, partner_map=partner_map)
        full_query += ' UNION ALL '.join(queries)
        # Oldest due dates come first.
        full_query += ' ORDER BY aml_date_maturity, aml_id'
        return full_query, all_params
