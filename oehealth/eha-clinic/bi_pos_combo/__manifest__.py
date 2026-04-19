# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

{
    "name" : "POS Combo in Odoo",
    "version" : "13.0.0.5",
    "category" : "Point of Sale",
    "depends" : ['base','point_of_sale','pos_restaurant'],
    "author": "BrowseInfo",
    'summary': 'App used for pos several products for sale as one combined product in POS product combo pos product pack pos pack pos bundle pos pack pos combo pack point of sales combo pack pos item combo pos item pack pos combo offer pos bundle product',
    "price":8 ,
    "currency": 'EUR',
    'license': 'LGPL-3',
    "description": """
    BrowseInfo developed a new odoo/OpenERP module apps.    
    Purpose :- 
    
    pos bundle pack pos combo combo pos pos pack pos item pack pos item combo pos product combo pos kit product kit pos
    pos combo kit point of sales combo 
POS product bundling is offering several products for sale as one combined product. 
It is a common feature in many imperfectly competitive product markets where price plays important roles, using these module you can act set competitive price for same or different products and variants to increase your sales graph.
Point Of sales Product Bundle POS product bundle point of sales pack  point of sales bundle item
point of sale Pack POS product pack Point of sale product pack Custom pack on POS
Combined product on POS Product Pack Custom Combo Product Bundle Product Customized product Group product Custom product bundle Custom Product Pack
Pack Price Bundle price Bundle Discount Bundle Offer


point of sales bundle pack point of sales combo combo point of sales point of sales pack point of sales item pack point of sales item combo point of sales product combo point of sales kit product kit point of sales
point of sales combo kit point of sale combo 
point of sales product bundling is offering point of sale several products for sale as point of sale one combined product. 
point of sales product markets point of sales bundle price pos bundle price
Point Of sale Product Bundle point of sales product bundle point of sale pack  point of sale bundle item
point of sales Pack point of sale product pack Point of sales product pack point of sales Custom pack on point of sales
point of sales Combined product on point of sales Product Pack  point of sales Custom Combo Product point of sales Bundle Product pos Customized product pos Group product pos Custom product bundle pos Custom Product Pack
point of sales Pack Price Bundle point of sales price Bundle point of sales Discount Bundle Offer pos Discount Bundle Offer pos Bundle Offer 

pos Pack pos product pack pos product pack pos Custom pack on point of sales
pos Combined product on pos Product Pack pos Custom Combo Product pos Bundle Product point of sale Customized product point of sale Group product point of sale Custom product bundle point of sales Custom Product Pack point of sales
pos Pack Price Bundle pos price Bundle pos Discount Bundle Offer point of sale Discount Bundle Offer point of sale Bundle Offer 
    """,
    "website" : "https://www.browseinfo.in",
    "data": [
        'security/ir.model.access.csv',
        'views/custom_pos_view.xml',
    ],
    'qweb': [
        'static/src/xml/bi_pos_combo.xml',
    ],
    'assets': {'point_of_sale.assets': [
        '/bi_pos_combo/static/src/js/bi_pos_combo.js',
        '/bi_pos_combo/static/src/css/custom.css',
	]},
    "auto_install": False,
    "installable": True,
    'live_test_url':'https://youtu.be/g0XPtpDmrDs',
    "images":['static/description/Banner.png'],
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
