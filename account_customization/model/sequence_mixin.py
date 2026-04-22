from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class SequenceMixin(models.AbstractModel):
    """Mechanism used to have an editable sequence number.

    Be careful of how you use this regarding the prefixes. More info in the
    docstring of _get_last_sequence.
    """

    _inherit = 'sequence.mixin'
    _description = "Automatic sequence"
    
    @api.constrains(lambda self: (self._sequence_field, self._sequence_date_field))
    def _constrains_date_sequence(self):
        # Make it possible to bypass the constraint to allow edition of already messed up documents.
        # /!\ Do not use this to completely disable the constraint as it will make this mixin unreliable.
        constraint_date = fields.Date.to_date(self.env['ir.config_parameter'].sudo().get_param(
            'sequence.mixin.constraint_start_date',
            '1970-01-01'
        ))
        for record in self:
            if not record._must_check_constrains_date_sequence():
                continue
            date = fields.Date.to_date(record[record._sequence_date_field])
            sequence = record[record._sequence_field]
            if sequence and date and date > constraint_date:
                format_values = record._get_sequence_format_param(sequence)[1]
                if (
                    format_values['year'] and format_values['year'] != date.year % 10**len(str(format_values['year']))
                    or format_values['month'] and format_values['month'] != date.month
                ):
                    pass
                    # raise ValidationError(_(
                    #     "The %(date_field)s (%(date)s) doesn't match the sequence number of the related %(model)s (%(sequence)s)\n"
                    #     "You will need to clear the %(model)s's %(sequence_field)s to proceed.\n"
                    #     "In doing so, you might want to resequence your entries in order to maintain a continuous date-based sequence.",
                    #     date=format_date(self.env, date),
                    #     sequence=sequence,
                    #     date_field=record._fields[record._sequence_date_field]._description_string(self.env),
                    #     sequence_field=record._fields[record._sequence_field]._description_string(self.env),
                    #     model=self.env['ir.model']._get(record._name).display_name,
                    # ))