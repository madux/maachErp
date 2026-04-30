import json
import logging
from datetime import datetime

from odoo import http, _
from odoo.http import request, Response

_logger = logging.getLogger(__name__)


def _json_response(data, status=200):
    """Return a clean JSON response."""
    return Response(
        json.dumps(data, default=str),
        status=status,
        content_type='application/json',
    )


def _error(message, status=400, code=None):
    return _json_response({'success': False, 'error': message, 'code': code or status}, status)


def _authenticate_api_key(func):
    """Decorator: validate X-API-Key header against res.users api_key or use HTTP Basic."""
    def wrapper(self, *args, **kwargs):
        # Support HTTP Basic Auth (username:password) OR X-API-Key header
        api_key = request.httprequest.headers.get('token')
        auth_header = request.httprequest.headers.get('Authorization', '')

        user = None
        if api_key:
            # Validate against Odoo API keys (Settings > API Keys)
            try:
                user = request.env['res.users'].sudo().search(
                    [('api_key', '=', api_key)], limit=1
                )
            except Exception:
                pass

        if not user and auth_header.startswith('Basic '):
            import base64
            try:
                decoded = base64.b64decode(auth_header[6:]).decode()
                login, password = decoded.split(':', 1)
                uid = request.session.authenticate(request.db, login, password)
                if uid:
                    user = request.env['res.users'].sudo().browse(uid)
            except Exception:
                pass

        if not user:
            return _error('Authentication required. Provide X-API-Key header or Basic Auth.', 401)

        request._booking_api_user = user
        return func(self, *args, **kwargs)
    return wrapper


class BookingAPIController(http.Controller):

    # ══════════════════════════════════════════════════════════════════════
    # ──  POST /api/v1/bookings  ──  Create a booking
    # ══════════════════════════════════════════════════════════════════════
    @http.route('/api/v1/create-booking', type='http', auth='none', methods=['POST'], csrf=False)
    def create_booking(self, **kwargs):
        """
        Create a new booking.

        Body (JSON):
        {
            "patient_name": "John Doe",          // used if patient_email not found
            "patient_email": "john@example.com",
            "patient_phone": "08012345678",
            "category_id": 1,
            "branch_id": 2,
            "booking_date": "2025-07-15",
            "time_slot_id": 3,
            "notes": "Optional note"
        }
        """
        try:
            body = json.loads(request.httprequest.data or '{}')
        except json.JSONDecodeError:
            return _error('Invalid JSON body.')

        # --- Auth (simple API key via header) ---
        api_key = request.httprequest.headers.get('X-API-Key')
        if not api_key:
            return _error('X-API-Key header is required.', 401)
        # Validate key against a config parameter for simplicity
        stored_key = request.env['ir.config_parameter'].sudo().get_param(
            'medical_booking.api_key', ''
        )
        if not stored_key or api_key != stored_key:
            return _error('Invalid API key.', 401)

        # --- Required fields ---
        required = ['category_id', 'branch_id', 'booking_date', 'time_slot_id']
        for f in required:
            if not body.get(f):
                return _error(f'Field "{f}" is required.')

        env = request.env

        # --- Resolve or create patient ---
        partner = None
        if body.get('patient_email'):
            partner = env['res.partner'].sudo().search(
                [('email', '=', body['patient_email'])], limit=1
            )
        if not partner and body.get('patient_name'):
            partner = env['res.partner'].sudo().create({
                'name': body['patient_name'],
                'email': body.get('patient_email', ''),
                'phone': body.get('patient_phone', ''),
            })
        if not partner:
            return _error('Cannot identify patient. Provide patient_email or patient_name.')

        # --- Validate related records ---
        category = env['booking.category'].sudo().browse(int(body['category_id']))
        if not category.exists():
            return _error(f'booking.category id={body["category_id"]} not found.', 404)

        branch = env['multi.branch'].sudo().browse(int(body['branch_id']))
        if not branch.exists():
            return _error(f'booking branch id={body["branch_id"]} not found.', 404)

        time_slot = env['booking.time.slot'].sudo().browse(int(body['time_slot_id']))
        if not time_slot.exists():
            return _error(f'booking.time.slot id={body["time_slot_id"]} not found.', 404)

        # --- Validate date ---
        try:
            booking_date = datetime.strptime(body['booking_date'], '%Y-%m-%d').date()
        except ValueError:
            return _error('booking_date must be YYYY-MM-DD.')
        if booking_date < datetime.today().date():
            return _error('booking_date cannot be in the past.')

        # --- Build available doctors from branch ---
        available_doctors = branch.doctor_ids

        # --- Create booking ---
        try:
            booking = env['booking.record'].sudo().create({
                'patient_id': partner.id,
                'category_id': category.id,
                'branch_id': branch.id,
                'booking_date': booking_date,
                'time_slot_id': time_slot.id,
                'available_doctor_ids': [(6, 0, available_doctors.ids)],
                'notes': body.get('notes', ''),
                'state': 'confirmed',
            })
        except Exception as e:
            _logger.error('API booking creation error: %s', e)
            return _error(str(e), 500)

        return _json_response({
            'success': True,
            'message': 'Booking created successfully.',
            'booking': booking._to_api_dict(),
        }, 201)

    # ══════════════════════════════════════════════════════════════════════
    # ──  GET /api/v1/bookings/<serial>  ──  Check booking status
    # ══════════════════════════════════════════════════════════════════════
    @http.route('/api/v1/bookings/<string:serial>', type='http', auth='none', methods=['GET'], csrf=False)
    def get_booking_status(self, serial, **kwargs):
        """
        Check status of a booking by serial number.
        No auth required – patient uses their serial + email as verification.

        Query params:
            email  (required for verification)
        """
        email = request.httprequest.args.get('email', '').strip().lower()
        if not email:
            return _error('Query param "email" is required to verify ownership.', 400)

        booking = request.env['booking.record'].sudo().search(
            [('serial_number', '=', serial)], limit=1
        )
        if not booking:
            return _error('Booking not found.', 404)

        if (booking.patient_id.email or '').lower() != email:
            return _error('Email does not match booking records.', 403)

        return _json_response({
            'success': True,
            'booking': booking._to_api_dict(),
        })

    # ══════════════════════════════════════════════════════════════════════
    # ──  GET /api/v1/bookings  ──  List all bookings (manager only)
    # ══════════════════════════════════════════════════════════════════════
    @http.route('/api/v1/bookings', type='http', auth='none', methods=['GET'], csrf=False)
    def list_bookings(self, **kwargs):
        """
        List bookings. Requires X-API-Key.

        Query params (all optional):
            state       – filter by state (draft/confirmed/done/cancelled)
            branch_id   – filter by branch
            date_from   – YYYY-MM-DD
            date_to     – YYYY-MM-DD
            limit       – default 50, max 200
            offset      – default 0
        """
        api_key = request.httprequest.headers.get('X-API-Key')
        stored_key = request.env['ir.config_parameter'].sudo().get_param(
            'medical_booking.api_key', ''
        )
        if not stored_key or api_key != stored_key:
            return _error('Invalid or missing X-API-Key.', 401)

        args = request.httprequest.args
        domain = []

        if args.get('state'):
            domain.append(('state', '=', args['state']))
        if args.get('branch_id'):
            domain.append(('branch_id', '=', int(args['branch_id'])))
        if args.get('date_from'):
            domain.append(('booking_date', '>=', args['date_from']))
        if args.get('date_to'):
            domain.append(('booking_date', '<=', args['date_to']))

        limit = min(int(args.get('limit', 50)), 200)
        offset = int(args.get('offset', 0))

        bookings = request.env['booking.record'].sudo().search(
            domain, limit=limit, offset=offset, order='booking_date desc'
        )
        total = request.env['booking.record'].sudo().search_count(domain)

        return _json_response({
            'success': True,
            'total': total,
            'limit': limit,
            'offset': offset,
            'bookings': [b._to_api_dict() for b in bookings],
        })

    # ══════════════════════════════════════════════════════════════════════
    # ──  GET /api/v1/booking-categories  ──  List categories + schedules
    # ══════════════════════════════════════════════════════════════════════
    @http.route('/api/v1/booking-categories', type='http', auth='none', methods=['GET'], csrf=False)
    def list_categories(self, **kwargs):
        """
        List all active booking categories with their weekday schedules and time slots.
        Public endpoint – no auth required.
        """
        categories = request.env['booking.category'].sudo().search(
            [('active', '=', True)]
        )
        result = []
        for cat in categories:
            weekdays = []
            for wd in cat.weekday_ids:
                slots = [
                    {
                        'id': s.id,
                        'name': s.name,
                        'start_time': s.start_time,
                        'end_time': s.end_time,
                    }
                    for s in wd.time_slot_ids
                ]
                weekdays.append({
                    'weekday': wd.weekday,
                    'weekday_label': dict(wd._fields['weekday'].selection).get(wd.weekday),
                    'is_available': wd.is_available,
                    'time_slots': slots,
                })
            result.append({
                'id': cat.id,
                'name': cat.name,
                'code': cat.code,
                'type': cat.category_type,
                'description': cat.description or '',
                'slot_duration_min': cat.slot_duration,
                'reminder_hours': cat.reminder_hours,
                'auto_assign_doctor': cat.auto_assign_doctor,
                'schedule': weekdays,
            })
        return _json_response({'success': True, 'categories': result})

    # ══════════════════════════════════════════════════════════════════════
    # ──  GET /api/v1/doctors  ──  List doctors (optionally by branch)
    # ══════════════════════════════════════════════════════════════════════
    @http.route('/api/v1/doctors', type='http', auth='none', methods=['GET'], csrf=False)
    def list_doctors(self, **kwargs):
        """
        List doctors.

        Query params:
            branch_id  – filter doctors by branch
        """
        args = request.httprequest.args
        domain = [('is_doctor', '=', True), ('active', '=', True)]
        if args.get('branch_id'):
            branch = request.env['multi.branch'].sudo().browse(int(args['branch_id']))
            if not branch.exists():
                return _error('Branch not found.', 404)
            doctor_ids = branch.doctor_ids.ids
            domain.append(('id', 'in', doctor_ids))

        doctors = request.env['res.users'].sudo().search(domain)
        result = [
            {
                'id': d.id,
                'name': d.name,
                'email': d.email or '',
                'speciality': d.medical_speciality or '',
                'branches': [{'id': b.id, 'name': b.name} for b in d.branch_ids],
            }
            for d in doctors
        ]
        return _json_response({'success': True, 'doctors': result})

    # ══════════════════════════════════════════════════════════════════════
    # ──  GET /api/v1/branches  ──  List branches
    # ══════════════════════════════════════════════════════════════════════
    @http.route('/api/v1/branches', type='http', auth='none', methods=['GET'], csrf=False)
    def list_branches(self, **kwargs):
        """List all active branches."""
        branches = request.env['multi.branch'].sudo().search([('active', '=', True)])
        result = [
            {
                'id': b.id,
                'name': b.name,
                'code': b.code,
                'address': b.street or '',
                'phone': b.telephone_no or '',
                'doctor_count': len(b.doctor_ids),
            }
            for b in branches
        ]
        return _json_response({'success': True, 'branches': result})

    # ══════════════════════════════════════════════════════════════════════
    # ──  GET /api/v1/available-slots  ──  Get available time slots for date
    # ══════════════════════════════════════════════════════════════════════
    @http.route('/api/v1/available-slots', type='http', auth='none', methods=['GET'], csrf=False)
    def available_slots(self, **kwargs):
        """
        Get available time slots for a given category and date.

        Query params (required):
            category_id
            date          – YYYY-MM-DD
            branch_id     – optional, to further filter
        """
        args = request.httprequest.args
        if not args.get('category_id') or not args.get('date'):
            return _error('category_id and date are required.')

        try:
            date_obj = datetime.strptime(args['date'], '%Y-%m-%d').date()
        except ValueError:
            return _error('date must be YYYY-MM-DD.')

        category = request.env['booking.category'].sudo().browse(int(args['category_id']))
        if not category.exists():
            return _error('Category not found.', 404)

        slots = category.get_available_slots(args['date'])

        # Filter out already-full slots
        booked_domain = [
            ('category_id', '=', category.id),
            ('booking_date', '=', args['date']),
            ('state', 'in', ['confirmed', 'in_progress']),
        ]
        if args.get('branch_id'):
            booked_domain.append(('branch_id', '=', int(args['branch_id'])))

        existing_bookings = request.env['booking.record'].sudo().search(booked_domain)
        slot_booking_count = {}
        for b in existing_bookings:
            slot_booking_count[b.time_slot_id.id] = slot_booking_count.get(b.time_slot_id.id, 0) + 1

        max_per_slot = category.max_bookings_per_slot or 1
        available = []
        for slot in slots:
            count = slot_booking_count.get(slot['id'], 0)
            slot['available_spots'] = max_per_slot - count
            slot['is_full'] = slot['available_spots'] <= 0
            available.append(slot)

        return _json_response({
            'success': True,
            'category_id': category.id,
            'date': args['date'],
            'slots': available,
        })

    # ══════════════════════════════════════════════════════════════════════
    # ──  PATCH /api/v1/bookings/<serial>/cancel  ──  Cancel a booking
    # ══════════════════════════════════════════════════════════════════════
    @http.route('/api/v1/bookings/<string:serial>/cancel', type='http', auth='none', methods=['POST', 'PATCH'], csrf=False)
    def cancel_booking(self, serial, **kwargs):
        """
        Cancel a booking.

        Body (JSON):
        {
            "email": "patient@example.com",
            "reason": "Cannot attend"
        }
        """
        try:
            body = json.loads(request.httprequest.data or '{}')
        except json.JSONDecodeError:
            return _error('Invalid JSON body.')

        email = body.get('email', '').strip().lower()
        if not email:
            return _error('"email" is required for verification.')

        booking = request.env['booking.record'].sudo().search(
            [('serial_number', '=', serial)], limit=1
        )
        if not booking:
            return _error('Booking not found.', 404)
        if (booking.patient_id.email or '').lower() != email:
            return _error('Email does not match booking records.', 403)
        if booking.state in ('done', 'cancelled'):
            return _error(f'Cannot cancel a booking in state "{booking.state}".', 409)

        booking.write({
            'state': 'cancelled',
            'cancellation_reason': body.get('reason', ''),
        })
        return _json_response({
            'success': True,
            'message': 'Booking cancelled.',
            'booking': booking._to_api_dict(),
        })
