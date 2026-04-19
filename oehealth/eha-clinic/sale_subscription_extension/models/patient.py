from odoo import api, fields, models


class OeHealthPatient(models.Model):
    _inherit = 'oeh.medical.patient'
    active_subscription = fields.Many2many(
        'sale.order', compute="_compute_active_subscription", store=True, index=True, string='Active Subscription')
    beneficiary_migrated = fields.Boolean(string='Migrated Beneficiary')
    plan_id = fields.Many2one(
        'sale.subscription.plan', string="Subscription Plan", compute="_compute_active_subscription")

    @api.depends('active_subscription')
    def _compute_active_subscription(self):
        for record in self:
            close_stage = self.get_close_stage()
            if record.partner_id:
                subscriptions = self.env['sale.order'].search([
                    ('partner_id', '=', record.partner_id.id),
                ])
                record.active_subscription = subscriptions
                active_subscriptions = subscriptions.filtered(lambda subscription: subscription.stage_id and subscription.stage_id.id != close_stage)
                if active_subscriptions:
                    line = record.mapped('active_subscription')[0]
                    record.plan_id = line.plan_id and line.plan_id.id or False
                else:
                    record.plan_id = False

    def get_close_stage(self):
        stage = None
        stages = self.env['sale.order.stage'].search(
            [('name', '=', 'Closed')], limit=1)
        for rec in stages:
            stage = rec.id
        return stage
