# Medical Booking Module — REST API Guide
# ==========================================
# Base URL: https://your-odoo.com
# All endpoints return JSON.
# Authentication: Set X-API-Key header (configured in Odoo > Settings > Technical > Parameters > System Parameters > medical_booking.api_key)

import requests

BASE_URL = "https://your-odoo.com"
API_KEY  = "your-secret-api-key"          # set in ir.config_parameter

HEADERS = {
    "Content-Type": "application/json",
    "X-API-Key": API_KEY,
}


# ══════════════════════════════════════════════════════════════════════════
# 1. LIST BOOKING CATEGORIES  (public – no auth required)
# ══════════════════════════════════════════════════════════════════════════
# GET /api/v1/booking-categories
# Returns all active categories with their weekly schedules and time slots.

resp = requests.get(f"{BASE_URL}/api/v1/booking-categories")
print(resp.json())

# Example response:
# {
#   "success": true,
#   "categories": [
#     {
#       "id": 1,
#       "name": "Doctor's Visit",
#       "code": "DOC",
#       "type": "doctors_visit",
#       "description": "...",
#       "slot_duration_min": 30,
#       "reminder_hours": 24,
#       "auto_assign_doctor": true,
#       "schedule": [
#         {
#           "weekday": "0",
#           "weekday_label": "Monday",
#           "is_available": true,
#           "time_slots": [
#             { "id": 1, "name": "08:00 - 08:30", "start_time": 8.0, "end_time": 8.5 },
#             { "id": 2, "name": "08:30 - 09:00", "start_time": 8.5, "end_time": 9.0 }
#           ]
#         }
#       ]
#     }
#   ]
# }


# ══════════════════════════════════════════════════════════════════════════
# 2. LIST BRANCHES  (public)
# ══════════════════════════════════════════════════════════════════════════
# GET /api/v1/branches

resp = requests.get(f"{BASE_URL}/api/v1/branches")
print(resp.json())

# Example response:
# {
#   "success": true,
#   "branches": [
#     { "id": 1, "name": "Main Clinic", "code": "MCL", "address": "...", "phone": "...", "email": "...", "doctor_count": 4 }
#   ]
# }


# ══════════════════════════════════════════════════════════════════════════
# 3. LIST DOCTORS  (public, optionally filtered by branch)
# ══════════════════════════════════════════════════════════════════════════
# GET /api/v1/doctors
# GET /api/v1/doctors?branch_id=1

resp = requests.get(f"{BASE_URL}/api/v1/doctors", params={"branch_id": 1})
print(resp.json())

# Example response:
# {
#   "success": true,
#   "doctors": [
#     {
#       "id": 5,
#       "name": "Dr. Amaka Obi",
#       "email": "amaka@clinic.com",
#       "speciality": "General Practice",
#       "branches": [{ "id": 1, "name": "Main Clinic" }]
#     }
#   ]
# }


# ══════════════════════════════════════════════════════════════════════════
# 4. CHECK AVAILABLE SLOTS FOR A DATE  (public)
# ══════════════════════════════════════════════════════════════════════════
# GET /api/v1/available-slots?category_id=1&date=2025-07-15&branch_id=1

resp = requests.get(
    f"{BASE_URL}/api/v1/available-slots",
    params={"category_id": 1, "date": "2025-07-15", "branch_id": 1},
)
print(resp.json())

# Example response:
# {
#   "success": true,
#   "category_id": 1,
#   "date": "2025-07-15",
#   "slots": [
#     { "id": 1, "name": "08:00 - 08:30", "start_time": 8.0, "end_time": 8.5, "available_spots": 1, "is_full": false },
#     { "id": 2, "name": "08:30 - 09:00", "start_time": 8.5, "end_time": 9.0, "available_spots": 0, "is_full": true }
#   ]
# }


# ══════════════════════════════════════════════════════════════════════════
# 5. CREATE A BOOKING  (requires X-API-Key)
# ══════════════════════════════════════════════════════════════════════════
# POST /api/v1/bookings

payload = {
    "patient_name":  "Chidi Okeke",           # used to create patient if email not found
    "patient_email": "chidi@example.com",      # used to find/create res.partner
    "patient_phone": "08012345678",
    "category_id":   1,                        # booking.category id
    "branch_id":     1,                        # booking.branch id
    "booking_date":  "2025-07-15",             # YYYY-MM-DD (must be future date)
    "time_slot_id":  1,                        # booking.time.slot id (from available-slots)
    "notes":         "First visit",            # optional
}

resp = requests.post(f"{BASE_URL}/api/v1/bookings", json=payload, headers=HEADERS)
print(resp.status_code)   # 201 on success
print(resp.json())

# Example response (201 Created):
# {
#   "success": true,
#   "message": "Booking created successfully.",
#   "booking": {
#     "id": 42,
#     "serial_number": "BK/2025/07/00042",
#     "state": "confirmed",
#     "patient": { "id": 10, "name": "Chidi Okeke", "email": "chidi@example.com", "phone": "08012345678" },
#     "category": { "id": 1, "name": "Doctor's Visit", "type": "doctors_visit" },
#     "branch": { "id": 1, "name": "Main Clinic" },
#     "booking_date": "2025-07-15",
#     "time_slot": { "id": 1, "name": "08:00 - 08:30", "start_time": 8.0, "end_time": 8.5 },
#     "assigned_doctor": { "id": 5, "name": "Dr. Amaka Obi" },
#     "is_conflicting": false,
#     "reminder_sent": false,
#     "notes": "First visit"
#   }
# }

# SAVE the serial_number — patient needs it to check status.


# ══════════════════════════════════════════════════════════════════════════
# 6. CHECK BOOKING STATUS  (patient self-service, no API key needed)
# ══════════════════════════════════════════════════════════════════════════
# GET /api/v1/bookings/<serial_number>?email=patient@email.com
# Patient provides their serial number + email to verify ownership.

serial = "BK/2025/07/00042"
resp = requests.get(
    f"{BASE_URL}/api/v1/bookings/{serial}",
    params={"email": "chidi@example.com"},
)
print(resp.json())

# Example response:
# {
#   "success": true,
#   "booking": {
#     "serial_number": "BK/2025/07/00042",
#     "state": "confirmed",
#     ... (full booking dict)
#   }
# }


# ══════════════════════════════════════════════════════════════════════════
# 7. LIST ALL BOOKINGS  (manager, requires X-API-Key)
# ══════════════════════════════════════════════════════════════════════════
# GET /api/v1/bookings
# Optional query params: state, branch_id, date_from, date_to, limit, offset

resp = requests.get(
    f"{BASE_URL}/api/v1/bookings",
    headers=HEADERS,
    params={
        "state":     "confirmed",
        "branch_id": 1,
        "date_from": "2025-07-01",
        "date_to":   "2025-07-31",
        "limit":     20,
        "offset":    0,
    },
)
print(resp.json())

# Example response:
# {
#   "success": true,
#   "total": 45,
#   "limit": 20,
#   "offset": 0,
#   "bookings": [ { ... }, { ... } ]
# }


# ══════════════════════════════════════════════════════════════════════════
# 8. CANCEL A BOOKING  (patient self-service)
# ══════════════════════════════════════════════════════════════════════════
# POST /api/v1/bookings/<serial_number>/cancel

serial = "BK/2025/07/00042"
resp = requests.post(
    f"{BASE_URL}/api/v1/bookings/{serial}/cancel",
    json={
        "email":  "chidi@example.com",    # required for verification
        "reason": "Schedule conflict",    # optional
    },
)
print(resp.json())

# Example response:
# {
#   "success": true,
#   "message": "Booking cancelled.",
#   "booking": { "serial_number": "...", "state": "cancelled", ... }
# }


# ══════════════════════════════════════════════════════════════════════════
# ERROR RESPONSES
# ══════════════════════════════════════════════════════════════════════════
# All errors follow the same shape:
# {
#   "success": false,
#   "error": "Human-readable message",
#   "code": 400   // HTTP status code
# }
#
# Common status codes:
#   400 – Bad request / missing fields
#   401 – Missing or invalid API key
#   403 – Email verification failed
#   404 – Record not found
#   409 – Business rule conflict (e.g. cancelling a completed booking)
#   500 – Internal server error


# ══════════════════════════════════════════════════════════════════════════
# POSTMAN QUICK-START
# ══════════════════════════════════════════════════════════════════════════
#
# 1. Import a new Collection in Postman.
# 2. Set a Collection Variable: base_url = https://your-odoo.com
# 3. Set a Collection Variable: api_key  = your-secret-api-key
# 4. For every request that needs auth, add Header:
#       Key:   X-API-Key
#       Value: {{api_key}}
#
# Request examples:
#
#  [GET]  {{base_url}}/api/v1/booking-categories
#  [GET]  {{base_url}}/api/v1/branches
#  [GET]  {{base_url}}/api/v1/doctors?branch_id=1
#  [GET]  {{base_url}}/api/v1/available-slots?category_id=1&date=2025-07-15
#  [POST] {{base_url}}/api/v1/bookings                       + JSON body + X-API-Key
#  [GET]  {{base_url}}/api/v1/bookings/BK%2F2025%2F07%2F00042?email=chidi@example.com
#  [GET]  {{base_url}}/api/v1/bookings                       + X-API-Key + query params
#  [POST] {{base_url}}/api/v1/bookings/BK%2F2025%2F07%2F00042/cancel + JSON body
#
# Note: URL-encode the "/" in serial numbers: BK/2025/07/00042 → BK%2F2025%2F07%2F00042


# ══════════════════════════════════════════════════════════════════════════
# ODOO SETUP CHECKLIST
# ══════════════════════════════════════════════════════════════════════════
#
# After installing the module:
#
# 1. Set your API key:
#    Settings → Technical → Parameters → System Parameters
#    Key:   medical_booking.api_key
#    Value: (your strong random secret)
#
# 2. Create Branches:
#    Medical Booking → Configuration → Branches
#
# 3. Mark users as doctors:
#    Settings → Users → (select user) → Medical Profile tab → check "Is Doctor"
#    Also assign them to branches on the same tab.
#
# 4. Create Booking Categories:
#    Medical Booking → Configuration → Booking Categories
#    - Set type (Doctor's Visit / Telemedicine / etc.)
#    - Add weekday availability lines
#    - Add time slots per weekday (e.g. Mon: 08:00-08:30, 08:30-09:00 …)
#    - Assign confirmation & reminder mail templates
#
# 5. Add users to groups:
#    Settings → Users → Groups → Medical Booking / Booking Manager
#    Settings → Users → Groups → Medical Booking / Doctor Medical Staff
#
# 6. The cron runs every hour automatically.
#    To test manually: Settings → Technical → Scheduled Actions →
#    "Medical Booking: Send Appointment Reminders" → Run Manually
