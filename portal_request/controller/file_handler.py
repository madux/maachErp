from odoo import http
from odoo.http import request
import json
import base64
import logging

_logger = logging.getLogger(__name__)


class MemoAttachmentController(http.Controller):
    
    @http.route('/memo/attachment/upload', type='json', auth='user', methods=['POST'], csrf=False)
    def upload_attachment(
        self, 
        name=None, 
        data=None, 
        res_model='memo.model', 
        res_id=None, **kwargs):
        """
        Upload attachment to Odoo
        Expected params:
        - name: filename
        - data: base64 encoded file data
        - res_model: model name (e.g., 'memo.model')
        - res_id: record ID (0 for new records)
        """
        _logger.info(f"Attachment getting ready for creation={kwargs}")
        
        try:
            if not res_id:
                return {
                    'status': 'error',
                    'message': 'Missing required parameters: res_id or record ID Not provided'
                }
            if not name or not data:
                return {
                    'status': 'error',
                    'message': 'Missing required parameters: name and data'
                }
            
            # Create attachment
            attachment = request.env['ir.attachment'].sudo().create({
                'name': name,
                'datas': data,
                'res_model': res_model,
                'res_id': res_id,
                'type': 'binary',
            })
            
            _logger.info(f"""
            Attachment created successfully: ID={attachment.id}, Name={name}, {res_id}, {res_model}
            """)
            
            return {
                'status': 'success',
                'id': attachment.id,
                'name': attachment.name,
                'result': {
                    'id': attachment.id,
                    'name': attachment.name,
                    'file_size': attachment.file_size,
                    'mimetype': attachment.mimetype,
                }
            }
            
        except Exception as e:
            _logger.error(f"Error uploading attachment: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }

    @http.route('/memo/attachment/delete/<int:attachment_id>', type='json', auth='user', methods=['POST'], csrf=False)
    def delete_attachment(self, attachment_id, **kwargs):
        """
        Delete attachment from Odoo
        """
        try:
            attachment = request.env['ir.attachment'].sudo().browse(attachment_id)
            
            if not attachment.exists():
                return {
                    'status': 'error',
                    'message': f'Attachment {attachment_id} not found'
                }
            
            # Check if user has permission to delete
            if attachment.res_model and attachment.res_id:
                # You can add additional permission checks here
                pass
            
            attachment_name = attachment.name
            attachment.unlink()
            
            _logger.info(f"Attachment deleted successfully: ID={attachment_id}, Name={attachment_name}")
            
            return {
                'status': 'success',
                'message': 'Attachment deleted successfully'
            }
            
        except Exception as e:
            _logger.error(f"Error deleting attachment: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }
    
    @http.route('/memo/attachment/get/<int:attachment_id>', type='http', auth='user', methods=['GET'])
    def get_attachment(self, attachment_id, **kwargs):
        """
        Get attachment file (for download/view)
        """
        try:
            attachment = request.env['ir.attachment'].sudo().browse(attachment_id)
            
            if not attachment.exists():
                return request.not_found()
            
            # Return the file
            return request.make_response(
                base64.b64decode(attachment.datas),
                headers=[
                    ('Content-Type', attachment.mimetype or 'application/octet-stream'),
                    ('Content-Disposition', f'attachment; filename="{attachment.name}"')
                ]
            )
            
        except Exception as e:
            _logger.error(f"Error getting attachment: {str(e)}")
            return request.not_found()
    
    @http.route('/memo/form/save-complete', type='http', auth='user', methods=['POST'], csrf=False)
    def save_memo(self, **post):
        """
        Save memo with attachments
        """
        try:
            # Parse attachment_ids from JSON string
            attachment_ids_str = post.get('attachment_ids', '[]')
            try:
                attachment_ids = json.loads(attachment_ids_str)
            except:
                attachment_ids = []
            
            # Get other form data
            subject = post.get('subject', '')
            description = post.get('description', '')
            department = post.get('department', '')
            priority = post.get('priority', 'medium')
            due_date = post.get('due_date', False)
            memo_id = post.get('memo_id', False)
            
            # Prepare memo values
            memo_vals = {
                'subject': subject,
                'description': description,
                'department': department,
                'priority': priority,
                'due_date': due_date if due_date else False,
                'attachment_ids': [(6, 0, attachment_ids)],  # Replace all attachments
            }
            
            # Create or update memo
            if memo_id:
                # Update existing memo
                memo = request.env['memo.model'].browse(int(memo_id))
                if memo.exists():
                    memo.write(memo_vals)
                    _logger.info(f"Memo updated successfully: ID={memo.id}")
                else:
                    raise ValueError(f"Memo {memo_id} not found")
            else:
                # Create new memo
                memo = request.env['memo.model'].create(memo_vals)
                memo_id = memo.id
                _logger.info(f"Memo created successfully: ID={memo.id}")
            
            # Update attachment res_id if it was 0
            if attachment_ids:
                attachments = request.env['ir.attachment'].sudo().browse(attachment_ids)
                attachments.filtered(lambda a: a.res_id == 0).write({
                    'res_id': memo_id
                })
            
            return json.dumps({
                'status': 'success',
                'memo_id': memo_id,
                'message': 'Memo saved successfully'
            })
            
        except Exception as e:
            _logger.error(f"Error saving memo: {str(e)}")
            return json.dumps({
                'status': 'error',
                'message': str(e)
            })
    
    @http.route('/memo/form/get/<int:memo_id>', type='json', auth='user', methods=['GET'])
    def get_memo(self, memo_id, **kwargs):
        """
        Get memo data including attachments
        """
        try:
            memo = request.env['memo.model'].browse(memo_id)
            
            if not memo.exists():
                return {
                    'status': 'error',
                    'message': f'Memo {memo_id} not found'
                }
            
            return {
                'status': 'success',
                'memo_id': memo.id,
                'subject': memo.subject or '',
                'description': memo.description or '',
                'department': memo.department or '',
                'priority': memo.priority or 'medium',
                'due_date': memo.due_date.strftime('%Y-%m-%d') if memo.due_date else '',
                'attachment_ids': memo.attachment_ids.ids,
                'attachment_count': len(memo.attachment_ids),
            }
            
        except Exception as e:
            _logger.error(f"Error getting memo: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }