# -*- coding: utf-8 -*-
# Part of Browseinfo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _

from odoo.exceptions import ValidationError



class CrossoveredBudget(models.Model):
    _inherit = "crossovered.budget"



    restrict_allow = fields.Selection([('allow','Allow'),('restrict' , 'Restrict')],string="Allow/Restrict Override Amount",default="restrict")


class CrossoveredBudgetLines(models.Model):
    _inherit = "crossovered.budget.lines"


    
    def _compute_practical_amount(self):


        res = super(CrossoveredBudgetLines, self)._compute_practical_amount()
        for line in self:
            result = 0.0
            
            date_to = self.env.context.get('wizard_date_to') or line.date_to
            date_from = self.env.context.get('wizard_date_from') or line.date_from
            line.practical_amount = 0

            purchase_res = self.env['purchase.order'].search([('date_order','>=',date_from),
                                                ('date_order','<=',date_to),
                                                ('analytic_account_id','=',line.analytic_account_id.id),
                                                ('company_id','=',line.company_id.id),
                                                ('state','in',['purchase','done'])])


            
            for purchase in purchase_res :

                invoice_rec = self.env['account.move'].search([('invoice_origin','=',purchase.name)])

                
                amount = purchase.currency_id._convert(purchase.amount_untaxed, line.company_id.currency_id, line.company_id, purchase.date_order.date() or fields.Date.today())
               
                
                result  = result + amount
                

                inv_total = 0
                for inv in invoice_rec :
                    
                    inv_total = inv_total + purchase.currency_id._convert(inv.amount_untaxed, line.company_id.currency_id, line.company_id, inv.invoice_date or fields.Date.today())
                
                
                

                if invoice_rec :

                    amount_diff = inv_total - amount

                    result = result + amount_diff

            
                

            line.practical_amount = -result
            
            invoice_vendor = self.env['account.move'].search([('invoice_date','>=',date_from),
                                                ('invoice_date','<=',date_to),('type','=','in_invoice'),('state','not in',['draft','cancel'])])
            

            total_bill = 0

            for bill in invoice_vendor :
                purchase_id = self.env['purchase.order'].search([('name','>=',bill.invoice_origin)])

                if not purchase_id :

                    for in_line in bill.invoice_line_ids :
                        if in_line.analytic_account_id.id == line.analytic_account_id.id :
                            
                            total_bill = total_bill + in_line.price_subtotal

            

            line.practical_amount = line.practical_amount + total_bill

            
            credit_vendor = self.env['account.move'].search([('invoice_date','>=',date_from),
                                                ('invoice_date','<=',date_to),('type','=','in_refund'),('state','not in',['draft','cancel'])])
            total_refund = 0
            for ref in credit_vendor :
                
                for in_line in ref.invoice_line_ids :
                    if in_line.analytic_account_id.id == line.analytic_account_id.id :
                        total_refund = total_refund + in_line.price_subtotal

            line.practical_amount = line.practical_amount - total_refund


            
