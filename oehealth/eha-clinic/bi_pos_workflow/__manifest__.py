# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

{
	"name" : "POS Auto Workflow Management",
	"version" : "13.0.1.1",
	"category" : "Point of Sale",
	"depends" : ['base','sale_management','point_of_sale','purchase', 'account'],
	"author": "BrowseInfo",
	'summary': 'Create Quotation from pos create Sales Order from Point of Sale screen pos backend automate POS Auto Invoice pos automate process POS Invoice Automate Point of Sales auto payment auto pos backend process pos auto process point of sale auto workflow pos ',
	"price": 69,
	"currency": 'EUR',
    'license': 'LGPL-3',
	"description": """
	Odoo pos workflow management.
	odoo point of sale workflow management pos Auto Payment pos Invoice Payment pos Auto Invoice Payment
	odoo pos Auto Order Confirmation pos Sale Confirmation pos Order Auto Done pos Order Auto paid Invoice Paid from pos, 
	odoo pos Auto Confirm Quotation pos Auto Create Invoice pos Auto Validate Invoice
	odoo pos Auto Create Payment POS Confirm Quotation
	odoo POS Confirm Quotation And Create Invoice pos Confirm Quotation And Validate Invoice
	odoo pos Confirm Quotation And Validate Invoice and Create Payment
	odoo AutoPay in pos pos Backend Auto Operation pos Backend Auto Operation pos automatic workflow
	odoo pos configurable workflow pos auto payment odoo pos auto invoice pos auto workflow
	
	
	odoo point of sale Auto Payment point of sale Invoice Payment point of sale Auto Invoice Payment
	odoo point of sale Auto Order Confirmation point of Sale Confirmation point of sale Order Auto Done
	odoo point of sale Order Auto paid Auto Invoice Paid from point of sale, 
	odoo point of sale Auto Confirm Quotation point of sale Auto Create Invoice point of sale Auto Validate Invoice
	odoo point of sale Auto Create Payment point of sale Confirm Quotation
	odoo POS Confirm Quotation And Create Invoice point of sale Confirm Quotation And Validate Invoice
	odoo point of sale Confirm Quotation And Validate Invoice and Create Payment
	odoo AutoPay in point of sales point of sale Backend Auto Operation point of sale automatic workflow
	odoo point of sale configurable workflow odoo point of sale auto payment odoo point of sale auto invoice
	odoo point of sale auto workflow   
	""",
	"website" : "https://www.browseinfo.in",
	"data": [
		'views/pos_workflow_view.xml',
	],
	'qweb': [
		'static/src/xml/pos_workflow.xml',
	],
	"auto_install": False,
	"installable": True,
	"live_test_url": "https://youtu.be/2FIyT8OHHlA",
	"images":['static/description/Banner.png'],
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
