# -*- coding: utf-8 -*-
# Copyright 2015 Grupo ESOC Ingeniería de Servicios, S.L.U. - Jairo Llopis
# Copyright 2015 Antiun Ingenieria S.L. - Antonio Espinosa
# Copyright 2017 Tecnativa - Pedro M. Baeza
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

{
    "name": "Partner second last name",
    "summary": "Have split first and second lastnames",
    "version": "11.0.1.0.0",
    "license": "AGPL-3",
    "website": "https://www.tecnativa.com",
    "author": "Tecnativa, "
              "Odoo Community Association (OCA) / Braincrew Apps(Migrated to Odoo 12)",
    "category": "Partner Management",
    "depends": [
        "base", "partner_firstname",
    ],
    "data": [
        "views/res_partner.xml",
        "views/res_user.xml",
    ],
    "installable": True,
}
