# -*- coding: utf-8 -*-
{
    'name': "EHA Material Requisition EXT",

    'summary': """
        EHA Material Requisition EXT module.""",

    'description': """
        This module is designed to extend the features of the material request
    """,

    'author': "EHA Clinic Ltd",
    'website': "https://www.eha.ng",
    'license': 'LGPL-3',
    'category': 'Uncategorized',
    'version': '0.1',

    'depends': [
        'base',
        'material_request',
    ],

    'data': [
        'wizard/make_warehouse_transfer_view.xml',
        'views/material_request_view.xml',
        'views/product_template_views.xml',
        'views/picking_views.xml',
    ],
}