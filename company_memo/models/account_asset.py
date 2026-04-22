from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from dateutil.relativedelta import relativedelta
from io import BytesIO
import random
import base64
from datetime import date
import psycopg2
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, PageBreak, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import fonts
from calendar import monthrange
import calendar

fonts.addMapping('DejaVu', 0, 0, 'DejaVuSerif')

ACCOUNT_SELECTION_TYPE = [
            ("asset_receivable", "Receivable"),
            ("asset_cash", "Other Recurrent"),
            ("asset_current", "Assets"),
            ("asset_non_current", "Non-current Assets"),
            ("asset_prepayments", "Prepayments"),
            ("asset_fixed", "Fixed Assets"),
            ("liability_payable", "Payable"),
            ("liability_credit_card", "Credit Card"),
            ("liability_current", "Liability"),
            ("liability_non_current", "Non-current Liabilities"),
            ("equity", "Equity"),
            ("equity_unaffected", "Current Year Earnings"),
            ("income", "REVENUE"),
            ("income_other", "Other Income"),
            ("expense", "Expenditure"),
            ("expense_depreciation", "Depreciation"),
            ("expense_direct_cost", "Cost of Revenue"),
            ("off_balance", "Off-Balance Sheet"),
        ]

class accountMove(models.Model):
    _inherit = 'account.move'
    _description = "Account Move"
    
    asset_parent_id = fields.Many2one(
        'account.asset', 
        string="Parent Asset",  
        store=True,
        compute="_compute_parent_asset"
        ) 
    
    @api.depends('asset_id')
    def _compute_parent_asset(self):
        for rec in self:
            rec.asset_parent_id = rec.asset_id.model_id.id if rec.asset_id and rec.asset_id.model_id else False
    
class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'
    _order = "id desc"

    code = fields.Char(string="Code")
    select = fields.Boolean(string="Select")
    asset_id = fields.Many2one('account.asset', string="Asset", store=True, related="move_id.asset_id")
    responsible_bu = fields.Many2one('multi.branch', string="Responsible BU")
    asset_number = fields.Char(string="Asset number",store=True)# , related="move_id.asset_id.name")
    asset_batch_number = fields.Char(string="Asset batch #",store=True, related="move_id.asset_batch_number")
    asset_modified_amount = fields.Float(string="Modified Asset Value", 
                                         help="During asset computation, If asset has been modified, system finds it and generate move for the modified different value")
    

class accountAsset(models.Model):
    _inherit = 'account.asset'
    _description = "Account asset"
    
    _order = "id desc"
    
    @api.depends('name')
    def _compute_display_name(self):
        for record in self:
            if record.name or record.product_id:
                name = f"[{record.name or ''}] {record.product_id.name or ''}"
                record.display_name = name
                record.product_desc = record.product_id.name
            else:
                record.display_name = record.name
                
    def _search_display_name(self, operator, value):
        """
        This method tells Odoo how to search on our computed field.
        It will search in both the 'name' and 'code' fields.
        """
        return ['|','|', '|',
                ('name', operator, value), 
                ('product_id', operator, value), 
                ('asset_code', operator, value),
                ('serial_number', operator, value)]

    memo_type_key = fields.Char(string="Memo type key") 
    asset_code = fields.Char(string="Asset code", copy=True) 
    purchase_value_without_tax = fields.Float(string="Purchase Value(Vat Exclusive)", copy=False) 
    name = fields.Char(string="Name", required=False, copy=True) 
    product_age = fields.Integer(string="Asset Age (Yrs)", compute="_compute_asset_age") 
    fleet_number = fields.Char(string="Fleet Number", copy=True) 
    serial_number = fields.Char(string="Serial Number", copy=True) 
    parent_number = fields.Char(string="Parent Number", copy=True, store=True,
    index=True) 
    memo_state = fields.Char(string="Memo state") 
    insurance_policy_number = fields.Char(string="Insurance Policy Number", copy=True) 
    # insurance_policy_id = fields.Many2one(
    #     "memo.insurance.agreement", 
    #     string="Insurance Policy", copy=True
    #     )
    src_location_id = fields.Many2one('stock.location', string="Asset Location", copy=True)
    date_of_commission = fields.Datetime(string="Commissioning Date", copy=True) 
    acquisition_date = fields.Date(string="Acquisition date", default=fields.Date.today()) 
    memo_state = fields.Char(string="Memo state") 
    memo_id = fields.Many2one('memo.model', string="Memo id") 
    product_id = fields.Many2one('product.product', string="Product id", copy=True) 
    responsible_bu = fields.Many2one('multi.branch', string="Responsible Business Unit") 
    branch_id = fields.Many2one('multi.branch', string="Branch") 
    responsible_employee_id = fields.Many2one('hr.employee', string="Responsible Employee ID") 
    disposed_date = fields.Datetime(string="Date Disposed", copy=True) 
    inventory_number = fields.Char(string="Inventory Number", copy=True) 
    customer_id = fields.Many2one('res.partner', string="Customer Name", compute="compute_inventory_number") 
    product_desc = fields.Char(string="Description")#, related="product_id.description") 
    qty_received = fields.Float('Asset Quantity')
    foreign_currency_amount = fields.Float('Foreign Currency Amount', compute="compute_purchase_forex_amount")
    is_asset_from_procurement = fields.Boolean('Asset Procurement')
    old_asset_value = fields.Float(store=True, string="old asset Value")
    new_asset_value = fields.Float(store=True, string="New asset Value")
    
    purchase_order = fields.Many2one('purchase.order', string="PO Ref")
    category_id = fields.Many2one('product.category', string="Product category")
    
    def get_forex_rate(self, currency, order_date):
        conversion_rate = False
        if currency and currency.rate_ids:
            rate_line = currency.rate_ids.filtered(
                    lambda r: fields.Date.to_date(r.name) <= order_date
                ).sorted(key=lambda r: r.name, reverse=True)[:1]
            conversion_rate = rate_line.inverse_company_rate
        return conversion_rate
            
    @api.depends('purchase_order')
    def compute_purchase_forex_amount(self):
        for rec in self:
            if rec.purchase_order and rec.purchase_order.currency_id.id != self.env.user.company_id.currency_id.id:
                forex_currency = rec.purchase_order.currency_id
                conversion_rate = rec.get_forex_rate(forex_currency, rec.purchase_order.date_order)
                if conversion_rate:
                    rec.foreign_currency_amount =  rec.original_value / conversion_rate
                else:
                    rec.foreign_currency_amount = rec.original_value
            else:
                rec.foreign_currency_amount = 0
                
    @api.depends('purchase_order')
    def compute_inventory_number(self):
        for rec in self:
            if rec.purchase_order:
                rec.customer_id = rec.purchase_order.partner_id.id
            else:
                rec.customer_id = False
                    
    modify_action= fields.Selection(
        [
        ('dispose', _("Dispose")),
        ('sell', _("Sell")),
        ('modify', _("Re-evaluate")),
        ('pause', _("Pause")),
        ('resume', _("Resume")),
        ], 
        string="Asset action",
        help="""Used to determine Asset action to take"""
    )
    account_type = fields.Selection(
        selection=ACCOUNT_SELECTION_TYPE,
        string='Account Class',
        tracking=True,
        store=True,
        default="asset_current"
    )
     
    # @api.onchange('name')
    # def onchange_name(self):
    #     for rec in self:
    #         if rec.name:
    #             if rec.state != 'model':
    #                 if rec.name.isdigit(): 
    #                     rec.asset_code = rec.name 
    #                 else:
    #                     rec.name = False 
    #                     raise ValidationError("Asset number must be digit only")
                
    @api.depends('name')
    def _compute_asset_age(self):
        for rec in self:
            if rec.acquisition_date: 
                diff = fields.Date.today() - rec.acquisition_date 
                rec.product_age = diff.days / 360
            else:
                rec.product_age = False
    
    def action_asset_modify(self):
        """ Returns an action opening the asset modification wizard.
        """
        self.ensure_one()
        new_wizard = self.env['asset.modify'].create({
            'asset_id': self.id,
            'modify_action': self.modify_action or 'resume' if self.env.context.get('resume_after_pause') else 'dispose',
        })
        return {
            'name': _('Modify Asset'),
            'view_mode': 'form',
            'res_model': 'asset.modify',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'res_id': new_wizard.id,
            'context': self.env.context,
        }
    
    def view_asset_line(self):
        return {
            'name': _('Modify Asset'),
            'view_mode': 'form',
            'res_model': 'account.asset',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'res_id': self.id, 
        }
        
    @api.onchange('model_id')
    def onchange_model(self):
        if self.model_id:
            # self.category_id = self.model_id.product_id.categ_id.id
            self.method_number = self.model_id.method_number
            self.method_period = self.model_id.method_period
            self.method = self.model_id.method
            self.account_asset_id = self.model_id.account_asset_id.id
            self.account_depreciation_id = self.model_id.account_depreciation_id.id
            self.account_depreciation_expense_id = self.model_id.account_depreciation_expense_id.id
            
    def reject_as_nonasset(self):
        '''this will go and create account line to debit product/category inventory account and credit product asset model expense account '''
        pass 
             
    def generate_child_asset(self):
        asset_ids = []
        for rec in self:
            # remove all records that has parent number as this and regenerate 
            old_assets = self.env['account.asset'].search([
                ('parent_number', 'in', [rec.name, rec.asset_code]),
                ('state', 'in', ['draft', 'close'])
                ])
            if old_assets:
                # looped because it is fast enough
                for asset in old_assets:
                    asset.unlink()
            if rec.qty_received > 0: # if it has quantity greater than 1, then it is a parent
                for asst in range(0, int(rec.qty_received)):                    
                    asset_obj = self.env['account.asset'].sudo()
                    # this will auto update product models
                    if rec.category_id:
                        rec.product_id.categ_id = rec.category_id.id
                        rec.product_id.account_asset_model = rec.model_id.id
                        rec.product_id.categ_id.account_asset_model = rec.model_id.id
                    
                    ass_id = asset_obj.create({
                        'product_id': rec.product_id.id,
                        'product_desc': rec.product_id.name or rec.product_id.description,
                        'memo_id': self.memo_id.id,                                
                        'source_location_id': rec.source_location_id.id or self.env.user.branch_id.id,                                
                        'branch_id': rec.branch_id.id or self.env.user.branch_id.id,                                
                        'date_of_commission': rec.date_of_commission,
                        'model_id': rec.model_id.id,
                        'account_asset_id': rec.account_asset_id.id,
                        'account_depreciation_id': rec.account_depreciation_id.id,
                        'account_depreciation_expense_id': rec.account_depreciation_expense_id.id,
                        'modify_action': rec.modify_action,
                        # 'asset_code': asset_code, # f'''{self.code} {self.id} {asset_count}''',
                        'original_value': rec.original_value,
                        'inventory_number':rec.inventory_number,
                        'responsible_bu': rec.responsible_bu.id or self.env.user.branch_id.id,
                        'method_number': rec.method_number,
                        'method_period': rec.method_period,
                        'method': rec.method,
                        'prorata_computation_type': rec.prorata_computation_type,
                        'parent_number': rec.name or rec.asset_code, # make it empty since this is the parent asset #asset_model.name,
                        # 'serial_number': rec.serial_number or rec.name or rec.asset_code, # make it empty since this is the parent asset #asset_model.name,
                        'fleet_number': rec.fleet_number,
                        'state': 'open',
                        'is_asset_from_procurement': False,
                        'purchase_order': rec.purchase_order.id,
                    })
                    asset_ids.append(ass_id.id)
        tree_view_id = self.env.ref('company_memo.memo_asset_model_tree_view').id
        form_view_id = self.env.ref('account_asset.view_account_asset_form').id
        ret = {
        'name': "Asset lines",
        'view_mode': 'tree',
        'view_type': 'tree',
        'views': [
            (tree_view_id, 'tree'), 
            (form_view_id, 'form')],
        'res_model': 'account.asset',
        'domain': [('id', 'in', asset_ids)],
        'type': 'ir.actions.act_window', 
        'target': 'current',
        }
        return ret
    
    def print_serial_number(self):

        # DYMO 99012 Label Size (252 x 100.8 points)
        LABEL_WIDTH = 252
        LABEL_HEIGHT = 100.8

        # Margins (converted from inches → points)
        top = 5.76
        bottom = 0
        left = 11.52
        right = 12.24

        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=(LABEL_WIDTH, LABEL_HEIGHT),
            leftMargin=left,
            rightMargin=right,
            topMargin=top,
            bottomMargin=bottom,
        )
        styles = getSampleStyleSheet()
        elements = []

        for rec in self:
            line1 = f"Property of {self.env.user.company_id.name}"
            number = rec.name or rec.asset_code
            line2 = f"Asset No: {number}"
            line3 = f"*{number}*"
            line4 = f"{rec.product_id.name}"

            # Label contents
            l1 = Paragraph(f"<font size=14><b>{line1}</b></font>", styles["Normal"])
            l1.alignment = 1  # Center align the support message
            elements.append(l1)
            elements.append(Spacer(1, 4))

            l2 = Paragraph(f"<font size=10>{line2}</font>", styles["Normal"])
            elements.append(l2)
            l2.alignment = 1  # Center align the support message 
            elements.append(Spacer(1, 4)) 
            
            l3 = Paragraph(f"<font size=14>{line3}</font>", styles["Normal"])
            elements.append(l3)
            l3.alignment = 1  # Center align the support message 
            elements.append(Spacer(1, 6))
            
            l4 = Paragraph(f"<font size=11>{line4}</font>", styles["Normal"])
            elements.append(l4)
            l4.alignment = 1
            # Add a page break AFTER each label, except the last one
            elements.append(PageBreak())

        # Remove LAST unnecessary PageBreak
        if isinstance(elements[-1], PageBreak):
            elements.pop()

        doc.build(elements)

        pdf = buffer.getvalue()
        buffer.close()

        pdf_content = base64.b64encode(pdf)

        attachment = self.env['ir.attachment'].create({
            'name': 'Labels.pdf',
            'type': 'binary',
            'datas': pdf_content,
            'mimetype': 'application/pdf',
            'res_model': self._name,
            'res_id': self.ids[0],
        })

        return {
            'type': 'ir.actions.act_url',
            'name': 'Labels Print',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'new',
        }
        
    def _get_default_code(self, vals):
        return self.env["ir.sequence"].next_by_code("account.asset") or ""
    
    @api.model
    def create(self, vals):
        code = self.env['ir.sequence'].next_by_code('account.asset')
        vals['name'] = code
        result = super(accountAsset, self).create(vals)
        return result

    def get_missing_depreciation_periods(self, asset):
        moves = asset.depreciation_move_ids.filtered(
            lambda m: m.state != 'cancel'
        )

        if not moves:
            return []
        dates = moves.mapped('date')
        existing_periods = {
            (d.year, d.month) for d in dates
        }
        start = min(dates)
        end = max(dates)

        missing_periods = []

        current = date(start.year, start.month, 1)
        end_period = date(end.year, end.month, 1)

        # while current <= end_period:
        for rec in existing_periods:
            if current <= end_period:
                if (current.year, current.month) not in existing_periods:
                    missing_periods.append(current)
                    date_to_run = date(current.year, current.month, 1)
                    self.action_compute_next_month(current_date=date_to_run)
                custom_period, method_length, interval_period  = self.get_interval_artifacts(asset)
                # current += relativedelta(months=1)
                current += interval_period
        return missing_periods
        
    def prorate_monthly_depreciation(self, monthly_amount, start_date):
        """
        Prorate monthly depreciation based on start date
        """
        days_in_month = calendar.monthrange(
            start_date.year, start_date.month
        )[1]
        
        days_used = days_in_month - start_date.day + 1

        prorated_amount = round(
            monthly_amount * (days_used / days_in_month), 2
        )
        return prorated_amount, days_used, days_in_month
    
    # Check remaining periods
    def get_interval_artifacts(self, asset):
        if asset.method_period in [12, '12']:
            '''running in full year'''
            if asset.prorata_computation_type == "none": 
                '''Just run with years'''
                custom_period = 1 
                method_length = asset.method_number
                interval_period = relativedelta(years=1)
            else:
                '''run per month into the number of years'''
                custom_period = 12
                method_length = asset.method_number * 12
                interval_period = relativedelta(months=1)
        else:
            custom_period = asset.method_number
            '''just run in months'''
            method_length = asset.method_number
            interval_period = relativedelta(months=1)
        return custom_period,method_length,interval_period
                
    def action_compute_next_month(self, batch_number=None, current_date=False, auto_post=None):
        """Compute only ONE depreciation move (monthly)"""
        f_date = fields.Date.today()
        batch_number = batch_number
        if not batch_number:
            batch_number = f"BATCH-SIN/{f_date.today().year}/{f_date.month}/{f_date.day}/{self.id}/{''.join(random.choice('2301945678') for _ in range(4))}"
        current_date_option = current_date if current_date else self.prorata_date or fields.Date.today()
        for asset in self: 
            if auto_post:
                asset.write({"state":'open'})
                # Posted depreciation lines
                posted_lines = asset.depreciation_move_ids.filtered(lambda m: m.state == 'posted')
            else:
                posted_lines = asset.depreciation_move_ids
            #filtered(lambda m: m.is_asset_additional_period == 'posted') # e.g 4165.67
            # Check remaining periods
            last_posted_depreciated_value = posted_lines
            custom_period, method_length, interval_period  = self.get_interval_artifacts(asset)
            
            # Determine depreciation date
            is_first_depreciation, first_post_date, last_post_date = False, None, None
            if posted_lines:
                first_post_date = posted_lines[-1].date
                last_post_date = posted_lines[0].date
                posted_months = (last_post_date.year - first_post_date.year) * 12 + (last_post_date.month - first_post_date.month)
                    
                if current_date:
                    depreciation_date = current_date 
                else:
                    last_date = max(posted_lines.mapped('date'))
                    depreciation_date = last_date + interval_period
                    # just replace the month with current date end period
                    # get the number of days of the month
                    days_in_month = calendar.monthrange(
                        depreciation_date.year, depreciation_date.month
                    )[1]
                    depreciation_date = depreciation_date.replace(day=days_in_month)
            else:
                asset.first_depreciation_date = current_date_option or asset.prorata_date
                depreciation_date = asset.first_depreciation_date 
                is_first_depreciation = True
            # remaining_value = asset.value_residual
            posted_months = 0 
            if first_post_date and last_post_date:
                posted_months = (last_post_date.year - first_post_date.year) * 12 + (last_post_date.month - first_post_date.month)
            # eg method_length = 12 - posted_months = 11
            remaining_periods = method_length - posted_months
            if remaining_periods <= 0:
                pass # raise UserError(_("No remaining depreciation periods."))
            else:
                # Monthly depreciation amount
                cummulative_depreciation_value = sum(posted_lines.mapped('depreciation_value'))
                asset_dep_value = cummulative_depreciation_value
                method_number  = asset.method_number # 5  
                if asset.method_number < 1:
                    raise ValidationError(f"Asset {asset.name} duration is set to 0. We cannot compute such")
                depreciation_percentage = (100 / method_number) / custom_period  
                # ie. 5% 100/5year/1 or 12 if months asset.depreciation_percentage
                # test : original value 20000, at 5 years by 12 months == 333.33 
                depreciation_value = asset.original_value * (depreciation_percentage / 100 )
                is_asset_additional_period = False
                if last_posted_depreciated_value:
                    if len(last_posted_depreciated_value) == 1:
                        '''here i need to knw if there is a change in price'''
                        if asset.new_asset_value > 0:
                            deficit = 0
                            for i in posted_lines:
                                if not i.is_first_depreciation:
                                    deficit += depreciation_value - i.depreciation_value
                                else:
                                    days_used = self.prorate_monthly_depreciation(depreciation_value, i.date)
                                    current_deprec = (days_used[1] / days_used[2] * depreciation_value) - i.depreciation_value
                                    deficit += current_deprec
                            depreciation_value = deficit + depreciation_value
                            is_asset_additional_period = True
                            asset.new_asset_value = 0
                        else:
                            depreciation_value = asset.original_value * (depreciation_percentage / 100 )
                            is_asset_additional_period = False
                    else:
                        if asset.new_asset_value > 0:
                            deficit = 0
                            for i in posted_lines:
                                if not i.is_first_depreciation:
                                    deficit += depreciation_value - i.depreciation_value
                                else:
                                    days_used = self.prorate_monthly_depreciation(depreciation_value, i.date)
                                    # days_used[2] = 31 days days of the month
                                    current_deprec = (days_used[1] / days_used[2] * depreciation_value) - i.depreciation_value
                                    deficit += current_deprec
                            depreciation_value = deficit + depreciation_value
                            is_asset_additional_period = True
                            asset.new_asset_value = 0 # change it to 0 to track new asset price changes
                        else:
                            is_asset_additional_period = False
                            depreciation_value = asset.original_value * (depreciation_percentage / 100 )
                    if not is_asset_additional_period:
                        depreciation_value = asset.original_value * (depreciation_percentage / 100 )
                        
                if is_first_depreciation:
                    '''Check the days to prorate if this is the first post'''
                    monthly_depreciation = depreciation_value
                    start_date = depreciation_date # date(2025, 12, 22)
                    prorated_amount, used_days, month_days = self.prorate_monthly_depreciation(
                        monthly_depreciation, start_date
                    )
                    depreciation_value = prorated_amount
                    
                asset_remaining_value = asset.original_value - cummulative_depreciation_value
                
                if remaining_periods == 1 and first_post_date:
                    fir_post = first_post_date.day - 1
                    depreciation_date = depreciation_date
                    days_in_month = calendar.monthrange(
                        depreciation_date.year, depreciation_date.month
                    )[1]
                    # posted_lines[-2].
                    depreciation_value = round(
                        depreciation_value * (fir_post / days_in_month), 2
                    )
                    try:
                        depreciation_date = depreciation_date.replace(day=fir_post)
                    except:
                        depreciation_date = depreciation_date.replace(day=days_in_month)
                    
                # Create move
                move_vals = asset._prepare_move_for_depreciation(
                    depreciation_date=depreciation_date,
                    batch_number=batch_number,
                    asset_depreciated_value = asset_dep_value,
                    depreciation_value = depreciation_value,
                    depreciation_percentage = depreciation_percentage,
                    asset_remaining_value = asset_remaining_value,
                    is_asset_additional_period = is_asset_additional_period,
                    is_first_depreciation = is_first_depreciation,
                    to_transfer_expense = asset.to_transfer_expense
                )
                move = self.env['account.move'].create(move_vals)
                if auto_post:
                    move.action_post()
            self.get_missing_depreciation_periods(asset)
        return True
        
    def _prepare_move_for_depreciation(
        self,
        depreciation_date, batch_number, **kwargs):
        'asset_depreciated_value : cummulative depreciation = total of all posted depreciation value'
        self.ensure_one()
        amount = kwargs.get('depreciation_value')
        to_transfer_expense = kwargs.get('to_transfer_expense')
        branch = self.previous_location.id if not to_transfer_expense else self.source_location_id.id,
        return {
            'date': depreciation_date,
            'ref': f"{self.name} - Depreciation",
            'asset_batch_number': f"{batch_number}",
            'asset_id': self.id,
            'journal_id': self.journal_id.id,
            'branch_id': branch,
            'asset_depreciated_value': kwargs.get('asset_depreciated_value'),
            'depreciation_value': amount,
            'depreciation_percentage': kwargs.get('depreciation_percentage'),
            'is_first_depreciation': kwargs.get('is_first_depreciation'),
            'asset_remaining_value': kwargs.get('asset_remaining_value'),
            'is_asset_additional_period': kwargs.get('is_asset_additional_period'),
            # 'previous_depreciation_asset_value': kwargs.get('previous_depreciation_asset_value'),
            'move_type': 'entry',
            'line_ids': [
                (0, 0, {
                    'name':  f"Credit Depreciation for Asset -{self.name}",
                    'account_id': self.account_depreciation_id.id,
                    'credit': amount,
                    'responsible_bu': self.responsible_bu.id,
                    'asset_batch_number': batch_number,
                    'asset_id': self.id,
                    'branch_id': branch,
                }),
                (0, 0, {
                    'name':  f"Debit Depreciation for Asset -{self.name}",
                    'account_id': self.account_depreciation_expense_id.id,
                    'debit': amount,
                    'responsible_bu': branch,
                    'asset_batch_number': batch_number,
                    'asset_id': self.id,
                    'branch_id': branch,
                }),
            ],
        }
        
    depreciation_months_total = fields.Integer(
        string="Total Months",
        compute="_compute_depreciation_stats",
        store=False
    )
    transfer_status = fields.Char(
        string="Transfer Status")
    awaiting_transfer_location = fields.Char(
        string="Transfered location")
    to_transfer_expense = fields.Boolean('Expenses transfer') 
    depreciation_months_done = fields.Integer(
        string="Posted Months",
        compute="_compute_depreciation_stats",
        store=False
    )
    date_received = fields.Date('Transfer Received')
    depreciation_months_remaining = fields.Integer(
        string="Remaining Months",
        compute="_compute_depreciation_stats",
        store=False
    )
    depreciation_amount_posted = fields.Monetary(
        string="Amount Posted",
        compute="_compute_depreciation_stats",
        store=False
    )
    depreciation_amount_remaining = fields.Monetary(
        string="Amount Not Posted",
        compute="_compute_depreciation_stats",
        store=False
    )
    first_depreciation_date = fields.Date(
        string="First depreciation date",
    )

    @api.depends('depreciation_move_ids.state', 'value_residual', 'method_number', 'original_value')
    def _compute_depreciation_stats(self):
        for asset in self:
            posted_moves = asset.depreciation_move_ids.filtered(
                lambda m: m.state == 'posted'
            )

            asset.depreciation_months_total = asset.method_number
            asset.depreciation_months_done = len(posted_moves)
            asset.depreciation_months_remaining = (
                asset.method_number - asset.depreciation_months_done
            )

            asset.depreciation_amount_posted = sum(
                posted_moves.mapped('amount_total')
            )

            asset.depreciation_amount_remaining = asset.value_residual
    
    depreciation_near_end = fields.Boolean(
        compute="_compute_depreciation_warning",
        store=False
    )

    depreciation_progress = fields.Float(
        string="Depreciation Progress (%)",
        compute="_compute_depreciation_warning",
        store=False
    )

    @api.depends(
        'depreciation_months_done',
        'depreciation_months_remaining',
        'method_number'
    )
    def _compute_depreciation_warning(self):
        for asset in self:
            if asset.method_number:
                asset.depreciation_progress = (
                    asset.depreciation_months_done / asset.method_number
                ) * 100
            else:
                asset.depreciation_progress = 0.0

            # Flag when less than or equal to 3 months remaining
            asset.depreciation_near_end = (
                asset.depreciation_months_remaining <= 3
                and asset.depreciation_months_remaining > 0
            )

# Asset computation 

MonthData = {
    '1': 'Jan',
    '2': 'Feb',
    '3': 'March',
    '4': 'April',
    '5': 'May',
    '6': 'Jun',
    '7': 'July',
    '8': 'Aug',
    '9': 'Sept',
    '10': 'Oct',
    '11': 'Nov',
    '12': 'Dec',
    }


class AssetComputation(models.TransientModel):
    _name = "asset.computation"
    _description = "Asset Depreciation Computation Wizard"

    selected_month = fields.Selection(
        [(str(k), str(v)) for k, v in MonthData.items()],
        string="Month",
        required=False,
    )

    year = fields.Date(
        string="Year", 
        default=lambda self: fields.Date.today()
    )
    
    fiscal_year_id = fields.Many2one(
        'account.fiscal.year', 
        string="Year",
        required=False, 
    )
    
    current_date = fields.Date(
        string="Use Current Code",
        required=True,
        default=lambda self: fields.Date.today()
    )
    override_the_period = fields.Boolean(
        string="Override Period difference",
        default=False,
    )
    auto_post = fields.Boolean(
        string="Auto post",
        default=False,
    )
    asset_line_ids = fields.Many2many(
        "account.asset",
        string="Assets",
    )

    @api.constrains("month_from", "month_to")
    def _check_month_range(self):
        for rec in self:
            if int(rec.month_to) < int(rec.month_from):
                raise ValidationError("Month To cannot be less than Month From.")

    # -----------------------------------------------------------------------
    # PRINT LABELS
    # -----------------------------------------------------------------------
    def action_print_labels(self):
        if not self.asset_line_ids:
            raise ValidationError("No assets selected.")

        for asset in self.asset_line_ids:
            asset.print_serial_number()  # you already have this method

        return {
            'type': 'ir.actions.act_window_close'
        }

     
    def compute_difference_in_depreciation(self, asset, move, period_start, batch_number):
        ''' Get already existing move for that period, if any modification in asset amount, 
        System should add additional entry'''
        difference_amount = move.amount_total - move.asset_modified_amount # 600 - 700 == if < 0 create new entry to credit the asset account current account  and debit the other account
        if difference_amount < 0:
            move_vals = asset._prepare_move_for_depreciation(
                amount=abs(difference_amount),
                depreciation_date=period_start,
                batch_number=batch_number
            )
            mv_line_ids = move_vals.get('line_ids')
            credit_mv_line = mv_line_ids[0][2]
            debit_mv_line = mv_line_ids[1][2]
            credit_mv_line.update({'account_id': asset.account_depreciation_expense_id.id})
            debit_mv_line.update({'account_id': asset.account_depreciation_id.id})
        elif difference_amount > 0:
            move_vals = asset._prepare_move_for_depreciation(
                amount=difference_amount,
                depreciation_date=period_start,
                batch_number=batch_number
            )
            mv_line_ids = move_vals.get('line_ids')
            credit_mv_line = mv_line_ids[0][2]
            debit_mv_line = mv_line_ids[1][2]
            credit_mv_line.update({'account_id': asset.account_depreciation_id.id})
            debit_mv_line.update({'account_id': asset.account_depreciation_expense_id.id})
        else:
            move_vals = []
        if move_vals:
            # reset back to zero 0
            move = self.env['account.move'].create(move_vals)
            move.action_post()
            move.asset_modified_amount = 0
            return move 
        else:
            return None        

    def button_compute_depreciation(self):
        f_date = self.fiscal_year_id.date_from or fields.Date.today()
        batch_number = f"BATCH/{f_date.year}/{f_date.month}/{f_date.day}/{self.id}/{''.join(random.choice('2301945678') for _ in range(4))}"
        ass_move = []
        if not self.selected_month or not self.fiscal_year_id:
            asset_ids = self.env['account.asset'].sudo().search([('state', 'in', ['open', 'draft'])])
            if not asset_ids:
                return self.env['memo.model'].notification_flag("Ops", f"System could not found any generated asset ready to run for the next period")
            CURRENT_DATE = self.current_date
            
            # .filtered(
            # lambda m: m.mapped('depreciation_move_ids').filtered(lambda m: m.state == 'draft'))
        else:
            year = self.fiscal_year_id.date_from.year
            month = int(self.selected_month)  # e.g. 1 = January
            period_start = date(year, month, 1)
            CURRENT_DATE = period_start
            period_end = period_start + relativedelta(months=1, days=-1)
            asset_with_modification_ids= []
            if self.override_the_period:
                domain = [('state', 'in', ['open'])]
                assets = self.env['account.asset'].sudo().search(domain)
                for rec in assets:
                    for mv in rec.depreciation_move_ids:
                        if mv.date.month == period_start.month and mv.asset_modified_amount > 0 and mv.state != 'cancel' and period_start.year == mv.date.year:
                            asset_with_modification_ids.append(rec.id)
                            # raise ValidationError(f"{[asset_with_modification_ids]} == {rec.name} {mv.date.month} {mv.date.year} == {period_start.month}  {period_start.year}")
                            
                            # got all asset that was modified
                            override_mv = self.compute_difference_in_depreciation(rec, mv, period_start, batch_number)
                            ass_move.append(override_mv)
            domain = [('state', 'in', ['open', 'draft']), ('id', '=', 412)]
            if asset_with_modification_ids:
                domain.append(('id', 'not in', asset_with_modification_ids))
            assets = self.env['account.asset'].sudo().search(domain)
            asset_ids = assets.filtered(
                lambda asset: not asset.depreciation_move_ids.filtered(
                    lambda mv:
                        mv.date
                        and period_start <= mv.date <= period_end
                        and mv.state != 'cancel'
                )
            )  
        asset_line_ids = asset_ids if asset_ids else self.asset_line_ids
        count = 0
        for asset in asset_line_ids: 
            try:
                asset.action_compute_next_month(
                    batch_number, CURRENT_DATE, auto_post= self.auto_post)
                count += 1
            except Exception as e:
                raise ValidationError(f"Asset issue { asset.id} - {e}")
        return self.env['memo.model'].notification_flag("Success", f"You have successfully posted {count} entries. Also override {len(ass_move)} records")
        




