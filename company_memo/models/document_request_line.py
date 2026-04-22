from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class DocumentRequestLine(models.Model):
    _name = "document.request.line"
    _description = "Document Request line"
    
    @api.model
    def default_get(self, fields):
        res = super(DocumentRequestLine, self).default_get(fields)
        user_branch = self.env.user.branch_id.id
        user_branch_ids = self.env.user.branch_ids.ids
        branches = user_branch_ids + [user_branch]
        document_folders = self.env['documents.folder'].search([('branch_id', 'in', branches)])
        res.update({
            'dummy_request_to_document_folder_ids': [(6, 0, [rec.id for rec in  document_folders])],
            })
        return res
    
    name = fields.Char(string="Document Name")
    memo_document_request_id = fields.Many2one(
        "memo.model", 
        string="Request from"
    )
    request_from_document_folder = fields.Many2one(
        "documents.folder", 
        string="Request from"
    )
    
    request_to_document_folder = fields.Many2one(
        "documents.folder", 
        string="Target Folder",
    )
    
    dummy_request_from_document_folder_ids = fields.Many2many(
        "documents.folder",
        string="Dummy Request from IDs"
        )
    dummy_request_to_document_folder_ids = fields.Many2many(
        "documents.folder",
        "document_folder_to_request_line_rel",
        "document_request_to_id",
        "document_folder_id",
        string="Dummy Request to IDs"
        )
    attachment_ids = fields.Many2many(
        'ir.attachment', 
        'document_request_ir_attachment_rel',
        'document_request_ir_attachment_id',
        'ir_attachment_document_reques_id',
        string='Attachment', 
        store=True,
        domain="[('res_model', '=', 'memo.model')]"
        )
    
    ##TODO domain to consider <branch, record rule and groups>
    document_documents_ids = fields.Many2many(
        'documents.document', 
        'document_request_document_rel',
        'document_request_document_id',
        'document_document_reques_id',
        string='Documents', 
        store=True,
        )
    
    memo_state = fields.Char(string="Request State", compute="compute_memo_state")
    
    @api.depends('memo_document_request_id')
    def compute_memo_state(self):
        for rec in self:
            if rec.memo_document_request_id:
                rec.memo_state = rec.memo_document_request_id.state
            else:
                rec.memo_state = ""
    
    def view_related_file_system(self):
        pass 
        # action_ref = 'documents.document_action'
        # search_view_ref = 'documents.document_view_search'
        # action = self.env["ir.actions.act_window"]._for_xml_id(action_ref)
        
        # # action = self.env["ir.actions.actions"]._for_xml_id(action_ref)
        # action['display_name'] = f"{self.memo_document_request_id.name}: Documents"
        # if search_view_ref:
        #     action['search_view_id'] = self.env.ref(search_view_ref).read()[0]
        # action['views'] = [(False, view) for view in action['view_mode'].split(",")]
        # folder_id = self.request_to_document_folder
        # documents = self.env['documents.document'].search([
        #     ('folder_id', '=', folder_id.id),
        #     ('attachment_id', 'in', self.attachment_ids.ids),
        #     ])
        # domain = f"[('id', 'in', {documents.ids})]"
        # # action['domain'] = eval(domain)
        # action['domain'] = [('id', 'in', documents.ids)]
        # # return {'action': action}
        # return action
            
     
    @api.onchange('request_from_document_folder')
    def suitable_document_ids(self):
        if self.request_from_document_folder:
            user_branch = self.env.user.branch_id.id
            user_branch_ids = self.env.user.branch_ids.ids
            branches = user_branch_ids + [user_branch]
            document_folders = self.env['documents.folder'].search([('branch_id', 'in', branches)])
            document_folders = []
            for r in document_folders:
                if r.id != self.request_from_document_folder.id:
                    document_folders.append(r.id)
            self.dummy_request_from_document_folder_ids = [(6, 0, document_folders)]
            
    
    
