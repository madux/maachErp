import json
from odoo import models, api, _, fields
from odoo.tools.misc import formatLang, get_lang
from odoo.exceptions import UserError
import datetime
import requests
from odoo.tools import float_is_zero
from dateutil.relativedelta import relativedelta


class CompanyInherit(models.Model):
    _inherit = "res.company"

    mono_publickey = fields.Char('Mono Public Key')
    mono_secretckey = fields.Char('Mono Secret Key')


class AccountJournalInherit(models.Model):
    _inherit = "account.journal"

    mono_publickey = fields.Char('Mono Public Key', related='company_id.mono_publickey')
    mono_secretckey = fields.Char('Mono Secret Key', related='company_id.mono_secretckey')
    mono_api_token = fields.Char('Mono Access Token')
    mono_account_id = fields.Char('Mono Account ID')
    last_sync_date = fields.Date('Last Sync Date')
    sync_active = fields.Boolean('Sync Active')
    sync_limit = fields.Char('Sync Limit', default=500)

    def authenticate(self):
        pass

    def _get_mono_credentials(self):
        return {
            'url': 'https://api.withmono.com/accounts'
        }

    def mono_fetch(self, url, params, data, type_request='POST'):
        credentials = self._get_mono_credentials()
        company_id = self.company_id or self.env.company
        url = credentials['url'] + url
        if not company_id.mono_publickey or not company_id.mono_secretckey:
            pass
        if not self.mono_account_id or not self.mono_api_token:
            pass
        headerVal = {"Accept": "application/json", "mono-sec-key": "%s" % (company_id.mono_secretckey)}
        try:
            resp = requests.request(type_request, url, params=params, json=data, headers=headerVal)
        except requests.exceptions.Timeout:
            raise UserError(_('Timeout: the server did not reply within 30s'))
        except requests.exceptions.ConnectionError:
            raise UserError(_('Server not reachable, please try again later'))
        return resp.json()

    def retrieve_transactions(self):
        today = fields.Date.today()
        fetch_today = False
        if self.last_sync_date == fields.Date().today():
            fetch_today = True
            today = today + datetime.timedelta(days=1)
        params = {
            'start': self.last_sync_date and self.last_sync_date.strftime('%d-%m-%Y'),
            'end': today.strftime('%d-%m-%Y'),
            'limit': 500,
            'paginate': False
        }
        if not self.last_sync_date:
            params.pop('start')
            params.pop('end')
        offset = 0
        transactions = []
        while True:
            if offset > 0:
                params['skip'] = offset
            transaction_url = '/' + self.mono_account_id + '/transactions'
            resp_json = self.mono_fetch(transaction_url, params, {}, 'GET')
            for tr in resp_json.get('data', []):
                date = fields.Date.from_string(tr.get('date'))
                amount = tr.get('amount', 0)
                # ignore transaction with 0
                if amount == 0:
                    continue
                vals = {
                    'online_identifier': str(tr.get('_id')),
                    'date': date,
                    'name': tr.get('narration', 'No description'),
                    'amount': (amount * -1) / 100 if tr.get('type') == 'debit' else amount / 100,
                    'end_amount': tr.get('balance'),
                }
                transactions.append(vals)
            if resp_json.get('paging', {}).get('total') < 500:
                break
            else:
                offset += 500
        if fetch_today:
            new_tr = []
            for tr in transactions:
                if tr['date'] == fields.Date.today():
                    new_tr.append(tr)
            transactions = new_tr
        self.last_sync_date = fields.Date.today()
        if transactions:
            print('============', transactions)
            return self.env['account.bank.statement'].with_context({'from_mono': True}).online_sync_bank_statement(
                transactions, self)

    def _cron_fetch_transactions(self):
        for rec in self.search([('sync_active', '=', True)]):
            rec.retrieve_transactions()

class AccountBankStatement(models.Model):
    _inherit = "account.bank.statement"

    @api.model
    def online_sync_bank_statement(self, transactions, journal):
        from datetime import datetime
        """
         build a bank statement from a list of transaction and post messages is also post in the online_account of the journal.
         :param transactions: A list of transactions that will be created in the new bank statement.
             The format is : [{
                 'id': online id,                  (unique ID for the transaction)
                 'date': transaction date,         (The date of the transaction)
                 'name': transaction description,  (The description)
                 'amount': transaction amount,     (The amount of the transaction. Negative for debit, positive for credit)
                 'end_amount': total amount on the account
                 'partner_id': optional field used to define the partner
                 'online_partner_vendor_name': optional field used to store information on the statement line under the
                    online_partner_vendor_name field (typically information coming from plaid/yodlee). This is use to find partner
                    for next statements
                 'online_partner_bank_account': optional field used to store information on the statement line under the
                    online_partner_bank_account field (typically information coming from plaid/yodlee). This is use to find partner
                    for next statements
             }, ...]
         :param journal: The journal (account.journal) of the new bank statement

         Return: The number of imported transaction for the journal
        """
        # Since the synchronization succeeded, set it as the bank_statements_source of the journal
        journal.sudo().write({'bank_statements_source': 'online_sync'})

        all_lines = self.env['account.bank.statement.line'].search([('journal_id', '=', journal.id),
                                                                    ('date', '>=', journal.account_online_journal_id.last_sync)])
        total = 0
        lines = []
        last_date = journal.account_online_journal_id.last_sync
        end_amount = 0
        for transaction in transactions:
            if all_lines.search_count([('online_identifier', '=', transaction['online_identifier'])]) > 0 or transaction['amount'] == 0.0:
                continue
            line = transaction.copy()
            total += line['amount']
            if self.env.context.get('from_mono'):
                end_amount = line['end_amount'] / 100
            else:
                end_amount = line['end_amount']
            line.pop('end_amount')
            # Get the last date
            if not last_date or line['date'] > last_date:
                last_date = line['date']
            lines.append((0, 0, line))

        # Search for previous transaction end amount
        previous_statement = self.search([('journal_id', '=', journal.id)], order="date desc, id desc", limit=1)
        # For first synchronization, an opening bank statement line is created to fill the missing bank statements
        all_statement = self.search_count([('journal_id', '=', journal.id)])
        digits_rounding_precision = journal.currency_id.rounding if journal.currency_id else journal.company_id.currency_id.rounding
        if all_statement == 0 and not float_is_zero(end_amount - total, precision_rounding=digits_rounding_precision):
            lines.append((0, 0, {
                'date': transactions and (transactions[0]['date']) or datetime.now(),
                'name': _("Opening statement: first synchronization"),
                'amount': end_amount - total,
            }))
            total = end_amount

        # If there is no new transaction, the bank statement is not created
        if lines:
            to_create = []
            # Depending on the option selected on the journal, either create a new bank statement or add lines to existing bank statement.
            previous_amount_to_report = 0
            for line in lines:
                create = False
                if not previous_statement or previous_statement.state == 'confirm':
                    to_create = lines
                    break
                line_date = line[2]['date']
                p_stmt = previous_statement.date
                if journal.bank_statement_creation == 'day' and previous_statement.date != line[2]['date']:
                    create = True
                elif journal.bank_statement_creation == 'week' and line_date.isocalendar()[1] != p_stmt.isocalendar()[1]:
                    create = True
                elif journal.bank_statement_creation == 'bimonthly':
                    if (line_date.month != p_stmt.month or line_date.year != p_stmt.year):
                        create = True
                    elif line_date.day > 15 and p_stmt.day <= 15:
                        create = True
                elif journal.bank_statement_creation == 'month' and (line_date.month != p_stmt.month or line_date.year != p_stmt.year):
                    create = True
                elif not journal.bank_statement_creation or journal.bank_statement_creation == 'none':
                    create = True

                if create:
                    to_create.append(line)
                else:
                    previous_amount_to_report += line[2]['amount']
                    line[2].update({'statement_id': previous_statement.id})
                    self.env['account.bank.statement.line'].create(line[2])

            if not float_is_zero(previous_amount_to_report, precision_rounding=digits_rounding_precision):
                previous_statement.write({'balance_end_real': previous_statement.balance_end_real + previous_amount_to_report})

            if to_create:
                balance_start = None
                if previous_statement:
                    balance_start = previous_statement.balance_end_real
                sum_lines = sum([l[2]['amount'] for l in to_create])
                print('======================hiren2222')

                self.create({'name': _('online sync'),
                            'journal_id': journal.id,
                            'line_ids': to_create,
                            'balance_end_real': end_amount if balance_start is None else balance_start + sum_lines,
                            'balance_start': (end_amount - total) if balance_start is None else balance_start
                            })

        journal.account_online_journal_id.sudo().write({'last_sync': last_date})
        return len(lines)
