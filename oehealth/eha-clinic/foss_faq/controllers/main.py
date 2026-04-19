import json
import logging
from odoo import http
import werkzeug.wrappers
from odoo.http import request
_logger = logging.getLogger(__name__)


class Main(http.Controller):

    @http.route(['/api/v1/faqs', '/api/v1/faqs/<int:id>/'], type='http', website=True, auth="public")
    def frequently_asked_questions(self, id=None, *args, **kwargs):
        category = None
        base_url = request.env['ir.config_parameter'].sudo(
        ).get_param('web.base.url')
        if id is not None:
            faq = request.env['faq.faq'].sudo().search([('id', '=', id)])
            return http.request.render('foss_faq.faq_answer', {'faq': faq})
        faqs = request.env['faq.faq'].sudo().search([])
        if kwargs.get("tag"):
            tag = request.env['faq.tag'].sudo().search(
                [('url_slug', '=', kwargs.get('tag'))])
            if tag:
                faq_questions = request.env['faq.faq'].sudo().search(
                    [('tag_ids', 'in', tag.ids)])
                data = [{
                    'question': faq.name,
                    'image': faq._get_faq_image_url(),
                    'answer_url': "{0}/api/v1/faqs/{1}".format(base_url, faq.id),
                    'answer': faq.solution} for faq in faq_questions
                ]
                return werkzeug.wrappers.Response(
                    status=200,
                    content_type="application/json; charset=utf-8",
                    response=json.dumps(data, indent=4),
                )
        if kwargs.get("category"):
            category = kwargs.get("category")
            faqs = faqs.filtered(
                lambda faq: faq.category_id.category_field == category)
        data = [{
            'question': faq.name,
            'image': faq._get_faq_image_url(),
            'answer_url': "{0}/api/v1/faqs/{1}".format(base_url, faq.id),
            'answer': faq.solution} for faq in faqs
        ]
        return werkzeug.wrappers.Response(
            status=200,
            content_type="application/json; charset=utf-8",
            response=json.dumps(data, indent=4),
        )

    @http.route(['/api/v1/faqs/<int:id>/answer'], type='http', website=True, auth="public")
    def faq_answer(self, id=None):
        faq = request.env['faq.faq'].sudo().search(
            [('id', '=', id)], limit=1)
        if not faq:
            return request.not_found()
        return http.request.render('foss_faq.faq_answer', {'faq': faq})

    @http.route('/faq/about-covid-19', type='http', auth="public", website=True)
    def about_covid19(self, **kw):
        faqs = request.env['faq.faq'].sudo().search(
            [('category_id.name', '=', 'COVID-19')])
        return http.request.render('foss_faq.about_covid19', {'faqs': faqs})

    @http.route(['/faq/questions', '/faq/questions/'], type='http', website=True, auth="public", methods=["GET"])
    def faq_questions(self):
        faqs = request.env['faq.faq'].sudo().search(
            [('category_id.name', '=', 'COVID-19')]
        )
        base_url = request.env['ir.config_parameter'].sudo(
        ).get_param('web.base.url')
        data = [{
            'question': q.name,
            'answer_url': "{0}/faq/{1}/answer".format(base_url, q.id),
            'answer': q.solution} for q in faqs if faqs
        ]
        return werkzeug.wrappers.Response(
            status=200,
            content_type="application/json; charset=utf-8",
            response=json.dumps(data, indent=4),
        )

    @http.route(['/faq/<int:id>/answer'], type='http', website=True, auth="public")
    def faq_answer(self, id=None):
        faq = request.env['faq.faq'].sudo().search(
            [('category_id.name', '=', 'COVID-19'), ('id', '=', id)], limit=1)
        if not faq:
            return request.not_found()
        return http.request.render('foss_faq.faq_answer', {'faq': faq})

    @http.route(['/api/v1/faq/tags'], type='http', website=True, auth="public")
    def faq_answer(self):
        tags = request.env['faq.tag'].sudo().search([])
        data = tags.read(['name', 'url_slug'])
        return werkzeug.wrappers.Response(
            status=200,
            content_type="application/json; charset=utf-8",
            response=json.dumps(data, indent=4),
        )
