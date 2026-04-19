# -*- coding: utf-8 -*-
# display version
from odoo import http
import json

class version(http.Controller):
    @http.route('/version',methods = ['POST','GET'], type='http', auth="none",cors="*", csrf=False)
    def server_version(self,**kw):
        try:
            with open('/var/run/clinics/REVISION') as fp:
                REVISION = fp.read().strip()
        except Exception:
            REVISION = ''
        try:
            return json.dumps({'revision': REVISION})
        except Exception as e:
            return json.dumps({"error": e, "title": "Error"})




