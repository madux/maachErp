import json
import requests
from datetime import timedelta
from werkzeug import urls
from odoo import models, fields, tools, _
from odoo.exceptions import UserError


class GoogleCalendar(models.AbstractModel):
    STR_SERVICE = 'calendar.sync'
    _inherit = 'google.%s' % STR_SERVICE

    def generate_data(self, event, isCreating=False):
        data = super(GoogleCalendar, self).generate_data(
            event=event, isCreating=isCreating)
        data.update({
            "conferenceData": {
                "createRequest": {
                    "requestId": "teleHealth1",
                    "conferenceSolutionKey": {
                        "type": "hangoutsMeet"
                    }
                }
            }
        })
        return data

    def create_an_event(self, event):
        """ Create a new event in google calendar from the given event in Odoo.
            :param event : record of calendar.event to export to google calendar
        """
        data = self.generate_data(event, isCreating=True)
        url = "/calendar/v3/calendars/%s/events?fields=%s&access_token=%s&conferenceDataVersion=1&sendNotifications=true&sendUpdates=all" % (
            'primary', urls.url_quote('id,updated'), self.get_token())
        headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
        data_json = json.dumps(data)
        try:
            return self.env['google.service']._do_request(url, data_json, headers, type='POST')
        except requests.HTTPError as e:
            try:
                response = e.response.json()
                error = response.get('error', {}).get('message')
            except Exception:
                error = None
            if not error:
                raise e
            message = _('The event "%s", %s (ID: %s) cannot be synchronized because of the following error: %s') % (
                event.name, event.start, event.id, error
            )
            raise UserError(message)

    def generate_data(self, event, isCreating=False):
        if event.allday:
            start_date = fields.Date.to_string(event.start_date)
            final_date = fields.Date.to_string(
                event.stop_date + timedelta(days=1))
            type = 'date'
            vstype = 'dateTime'
        else:
            start_date = fields.Datetime.context_timestamp(
                self, event.start + timedelta(hours=-1)).isoformat('T')
            final_date = fields.Datetime.context_timestamp(
                self, event.stop + timedelta(hours=-1)).isoformat('T')
            type = 'dateTime'
            vstype = 'date'
        attendee_list = []
        for attendee in event.attendee_ids:
            email = tools.email_split(attendee.email)
            email = email[0] if email else 'NoEmail@mail.com'
            attendee_list.append({
                'email': email,
                'displayName': attendee.partner_id.name,
                'responseStatus': attendee.state or 'needsAction',
            })

        reminders = []
        for alarm in event.alarm_ids:
            reminders.append({
                "method": "email" if alarm.alarm_type == "email" else "popup",
                "minutes": alarm.duration_minutes
            })
        data = {
            "summary": event.name or '',
            "description": event.description or '',
            "start": {
                type: start_date,
                vstype: None,
                'timeZone': self.env.context.get('tz') or self.env.user.tz or 'UTC',
            },
            "end": {
                type: final_date,
                vstype: None,
                'timeZone': self.env.context.get('tz') or self.env.user.tz or 'UTC',
            },
            "attendees": attendee_list,
            "conferenceData": {
                "createRequest": {
                    "requestId": "teleHealth1",
                    "conferenceSolutionKey": {
                        "type": "hangoutsMeet"
                    }
                },
            },
            "location": event.location or '',
            "visibility": event['privacy'] or 'public',
        }
        if event.recurrency and event.rrule:
            data["recurrence"] = ["RRULE:" + event.rrule]

        if not event.active:
            data["state"] = "cancelled"

        if not self.get_need_synchro_attendee():
            data.pop("attendees")
        if isCreating:
            other_google_ids = [other_att.google_internal_event_id for other_att in event.attendee_ids
                                if other_att.google_internal_event_id and not other_att.google_internal_event_id.startswith('_')]
            if other_google_ids:
                data["id"] = other_google_ids[0]
        return data
