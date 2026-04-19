# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

{
    "name" : "Purchase Order Integration with Budget in Odoo(Community Edition)",
    "version" : "13.0.0.1",
    'summary': "App for integrate budget with purchase Analytic account restrict and override budget amount purchase Accounting budget purchase integration purchase account budgeting purchase budget management vendor bill budget vendor bill costing purchase budget costing",
    "description": """
    
    Odoo Purchase order budget Integration Purchase order Integration with budget app,
    Odoo Purchase order budget Integration odoo app override Purchase order budget amount allow override Purchase order budget amount,
    odoo restrict override Purchase order budget amount

Odoo Purchase Budgets Management Invoicing Budgets management vendor bill Budgets management
Odoo Purchase Analytic Account Budget management
Odoo purchases budget management in odoo
Odoo purchase Analytic Accounts link with account budget management
Odoo purchase Analytic Account link with budget management Analytic Accounts budgeting
Odoo Accounting budget Management with purchase integration purchase account budgeting in Odoo
odoo puchase budget planning Accounting Analytic budget planning
Odoo Accounting Analytic budget in purchase

Odoo Purchase Order Budgets Management Invoicing Budgets management vendor bill Budgets management
Odoo Purchase Order Analytic Account Budget management
Odoo purchase Order budget management in odoo
Odoo purchase Order Analytic Accounts link with account budget management
Odoo purchase Order Analytic Account link with budget management Analytic Accounts budgeting
Odoo Accounting budget Management with purchase Order integration purchase Order account budgeting in Odoo
odoo puchase Order budget planning Accounting Analytic budget planning
Odoo Accounting Analytic budget in purchase orders

Odoo supplier invoice Analytic Account Budget management
Odoo supplier invoice budget management in odoo
Odoo supplier invoice Analytic Accounts link with account budget management
Odoo supplier invoice Analytic Account link with supplier invoice budget management Analytic Accounts budgeting
Odoo Accounting budget Management with supplier invoice integration supplier invoice account budgeting in Odoo
odoo supplier invoice budget planning Accounting Analytic budget planning supplier invoices
Odoo Accounting Analytic budget in supplier invoices 

Odoo vendor bill Analytic Account Budget management
Odoo vendor bill budget management in odoo
Odoo vendor bill Analytic Accounts link with account budget management
Odoo vendor bill Analytic Account link with vendor bill budget management Analytic Accounts budgeting
Odoo Accounting budget Management with vendor bill integration vendor bill account budgeting in Odoo
odoo vendor bill budget planning Accounting Analytic budget planning vendor bills
Odoo Accounting Analytic budget in vendor bills

Odoo purchase analytic account project budget management
Odoo purchase project analytic account management
Odoo purchase analytic account plan with budget management
odoo purchase budget management
odoo puchase budget with analytic account

Odoo purchase order analytic account project budget management
Odoo purchase order project analytic account management
Odoo purchase order analytic account plan with budget management
odoo purchase order budget management
odoo puchase order budget with analytic account


Odoo vendor bills analytic account project budget management
Odoo vendor bill project analytic account management
Odoo vendor bill analytic account plan with budget management
odoo vendor bill budget management
odoo vendor bill with analytic account
After installing this apps you can have option to allow and restrict validation of purchase order against budget amount. 
If you restrict override budget amount then once the purchase order or vendor bills amount is threshold limit against budget planned amount then user not allow to confirm or validate those purchase/vendor bills. 
But if you allow the override limit on purchase order then user can able to confirm or validate purchase order or vendor bill after the threshold or exhausted budget planned amount and you will see the actual amount on more than planned budget. 
This apps is very useful to plan your periodically accounting budget of your company.


 Budgets are defined (in Invoicing/Budgets/Budgets), the Project Managers
can set the planned amount on each Analytic Account.
 budget management in odoo
 Analytic Accounts budget 
 Analytic Accounts budgeting
 Accounting budget Management
 account budgeting in Odoo
 budget planning
 
 Accounting Analytic budget planning
 Accounting Analytic budget in 
The accountant has the possibility to see the total of amount planned for each
Budget in order to ensure the total planned is not greater/lower than what he
planned for this Budget. Each list of record can also be switched to a graphical
view of it.

Three reports are available:
analytic account project budget management
project analytic account management
analytic account plan with budget management
purchase budget management
puchase budget with analytic account
----------------------------
    1. The first is available from a list of Budgets. It gives the spreading, for
       these Budgets, of the Analytic Accounts.

    2. The second is a summary of the previous one, it only gives the spreading,
       for the selected Budgets, of the Analytic Accounts.

    3. The last one is available from the Analytic Chart of Accounts. It gives
       the spreading, for the selected Analytic Accounts of Budgets.
       budget planning
       financial accounting budget planning
       accounting financial planning
       account budget
       accounts budgets
       financial budget
       odoo12 budget management
       account budget odoo12
       odoo12 account budget management
       odoo12 budget analytic account
       odoo 12 analytic account budget management
       odoo12 analytic account budgett management
       odoo 12 account budget
       account budget management for odoo12
       account budget for odoo12
       account budget odoo12
       account budget odoo 12
       budget account odoo12
       budget account odoo 12
       account budget management odoo 12
                 
    """,
    "author": "BrowseInfo",
    "website" : "https://www.browseinfo.in",
    "price": 60,
    'license': 'LGPL-3',
    "currency": 'EUR',
    "depends" : ['base','bi_account_budget','purchase','account'],
    "data": ['views/purchase.xml'],
    'demo': [],
    'qweb': [],
    "auto_install": False,
    "installable": True,
    "live_test_url":'https://youtu.be/i2ArKYxywHA',
    "images":["static/description/Banner.png"],
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
