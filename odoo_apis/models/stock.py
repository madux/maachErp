from odoo import models, fields

class stockpicking(models.Model):
    _inherit = 'stock.picking'
    
    assigned_delivery_man = fields.Many2one(
        "res.users", 
        string="Delivery person")
    order_delivery_status = fields.Selection([
        ('not_enabled', 'Delivery Not Enabled'),
        ('in_progress', 'Delivery In Progress'),
        ('delivered', 'Delivered')],
        string="Delivery Status",
        default="not_enabled"
        )
    is_acknowledge = fields.Boolean('Is acknowledged?', default=False)
    acknowledge_note = fields.Text('Acknowledgement note')
    
     