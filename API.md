# API Documentation

This document describes all available API endpoints in the Invictus BJJ application.

## Base URL

All API endpoints are prefixed with their respective route prefixes as defined in `main.py`.

## Authentication

API requests to ERPNext are authenticated using token-based authentication with API Key and Secret configured in environment variables.

---

## Payment Endpoints

**Prefix**: `/api/v1/payment`

### GET /api/v1/payment/
Renders the payment home page with customer RFID scanning interface.

**Response**: HTML page (`payment/scan_customer.html`)

---

### POST /api/v1/payment/scan
Process customer RFID scan to initiate payment session.

**Request Body**:
```json
{
  "rfid": "string"
}
```

**Response**:
```json
{
  "status": "success",
  "session_id": "uuid-string",
  "redirect_url": "/api/v1/payment/process/{session_id}"
}
```

**Error Responses**:
- `400`: RFID input required
- `404`: Customer not found
- `500`: Error processing customer scan

---

### GET /api/v1/payment/process/{session_id}
Display invoice selection page for the payment session.

**Parameters**:
- `session_id` (path): UUID of the payment session

**Response**: HTML page (`payment/invoice_selection.html`) with customer and invoice data

---

### POST /api/v1/payment/authorize-staff
Authorize staff member to process payment.

**Request Body**:
```json
{
  "staff_rfid": "string",
  "staff_name": "string (optional)"
}
```

**Response**:
```json
{
  "status": "success",
  "authorized": true,
  "staff_name": "Staff Full Name",
  "staff_rfid": "rfid-string",
  "roles": ["Accounts User", "System Manager"]
}
```

**Error Responses**:
- `400`: Staff RFID required
- `401`: Staff not authorized
- `500`: Authorization failed

---

### POST /api/v1/payment/process-payment
Submit and process the payment.

**Request Body**:
```json
{
  "invoices": ["INV-001", "INV-002"],
  "invoice_amounts": {
    "INV-001": 100.00,
    "INV-002": 50.00
  },
  "total_amount": 150.00,
  "customer_name": "Customer Name",
  "staff_rfid": "staff-rfid-string"
}
```

**Response**: Payment processing result with payment entry ID

**Error Responses**:
- `401`: Staff authorization required
- `500`: Payment processing error

---

### GET /api/v1/payment/success/{payment_id}
Display payment success confirmation page.

**Parameters**:
- `payment_id` (path): ID of the payment entry

**Response**: HTML page (`payment/success.html`) with payment details

---

### GET /api/v1/payment/history
View payment history with handover status.

**Query Parameters**:
- `days` (optional, default: 30): Number of days to look back

**Response**: HTML page (`payment/history.html`) with payment history

---

### GET /api/v1/payment/history/details/{payment_id}
View detailed payment information.

**Parameters**:
- `payment_id` (path): ID of the payment entry

**Response**: HTML page (`payment/details.html`) with full payment details

---

## Handover Endpoints

**Prefix**: `/api/v1/payment/handover`

### GET /api/v1/payment/handover/dashboard
Display dashboard showing payments awaiting handover from coaches to treasurers.

**Response**: HTML page (`payment/handover_dashboard.html`) with pending handovers

---

### GET /api/v1/payment/handover/process/{payment_id}
Display screen for treasurer to confirm receipt of payment.

**Parameters**:
- `payment_id` (path): ID of the payment to hand over

**Response**: HTML page (`payment/handover_confirmation.html`) with payment details

---

### POST /api/v1/payment/handover/confirm
Process handover from coach to treasurer.

**Request Body**:
```json
{
  "rfid": "treasurer-rfid-string",
  "payment_id": "payment-entry-id",
  "notes": "optional handover notes"
}
```

**Response**:
```json
{
  "success": true,
  "payment_id": "payment-entry-id",
  "message": "Payment successfully transferred to Treasurer Name",
  "redirect_url": "/api/v1/payment/handover/success"
}
```

**Error Responses**:
- `400`: Treasurer RFID required / Payment ID required / Authorization failed
- `500`: Error processing handover

---

### GET /api/v1/payment/handover/success
Display success page after successful handover.

**Response**: HTML page (`payment/handover_success.html`)

---

### GET /api/v1/payment/handover/history
View payment history with handover status.

**Query Parameters**:
- `days` (optional, default: 30): Number of days to look back

**Response**: HTML page (`payment/history.html`)

---

## Billing Endpoints

**Prefix**: `/api/v1/billing`

### GET /api/v1/billing/customer/{customer_name}
Get billing page for a customer.

**Parameters**:
- `customer_name` (path): Customer name

**Response**: HTML page (`billing.html`) with billing information

---

### GET /api/v1/billing/customer/ui/{customer_name}
Get billing UI page for a customer (alternate endpoint).

**Parameters**:
- `customer_name` (path): Customer name

**Response**: HTML page (`billing.html`)

---

### Debug Endpoints

The following debug endpoints are available for troubleshooting:

| Endpoint | Description |
|----------|-------------|
| `GET /api/v1/billing/test/search/{customer_name}` | Test customer search functionality |
| `GET /api/v1/billing/debug/transactions/{customer_name}` | View raw transaction data |
| `GET /api/v1/billing/debug/invoices/{customer_name}` | Check sales invoices directly |
| `GET /api/v1/billing/debug/doctypes` | Check available ERPNext doctypes |
| `GET /api/v1/billing/debug/test-endpoints` | Test various ERPNext endpoints |
| `GET /api/v1/billing/debug/api-test/{customer_name}` | Test various API methods |
| `GET /api/v1/billing/debug/payment/{payment_id}` | Check raw payment entry data |
| `GET /api/v1/billing/debug/user/{user_id}` | Check user data and roles |

---

## Attendance Endpoints

**Prefix**: `/api/v1/attendance`

### GET /api/v1/attendance
Display main attendance scanner page.

**Response**: HTML page (`attendance.html`)

---

### GET /api/v1/attendance/customer/{customer_name}
Get customer attendance records with weekly calendar view.

**Parameters**:
- `customer_name` (path): Customer name
- `week_offset` (query, optional, default: 0): Week offset for navigation

**Response**: HTML page (`attendance.html`) with attendance data

---

### POST /api/v1/attendance/scan
Process attendance RFID scan.

**Request Body**:
```json
{
  "rfid": "customer-rfid-string"
}
```

**Response**:
```json
{
  "status": "success",
  "customer_name": "Customer Name",
  "attendance_time": "2024-01-15T10:30:00",
  "redirect_url": "/api/v1/attendance/customer/Customer Name"
}
```

**Error Responses**:
- `404`: Customer not found
- `500`: Failed to update attendance

---

## Enrollment Endpoints

**Prefix**: `/api/v1/enrollment`

### GET /api/v1/enrollment/
Display the enrollment form page.

**Response**: HTML page (`enrollment.html`) with available programs

**Available Programs**:
| Program | Description | Daily | Monthly | 6 Months | Yearly |
|---------|-------------|-------|---------|----------|--------|
| BJJ | Traditional BJJ with Gi | 50.0 | 400.0 | 2000.0 | 3600.0 |
| No-Gi | No-Gi grappling | 50.0 | 400.0 | 2000.0 | 3600.0 |

---

### POST /api/v1/enrollment/enroll
Create a new student enrollment.

**Request Body**:
```json
{
  "student_name": "string",
  "email": "email@example.com",
  "phone": "+597-123-4567",
  "date_of_birth": "1990-01-15",
  "program_type": "bjj|nogi",
  "billing_cycle": "daily|monthly|six_months|yearly",
  "start_date": "2024-01-15"
}
```

**Response**:
```json
{
  "customer_id": "CUST-00001",
  "invoice_id": "INV-00001",
  "amount": 400.00,
  "due_date": "2024-02-15",
  "message": "Enrollment successful"
}
```

**Error Responses**:
- `400`: Validation error

---

## Customer Endpoints

**Prefix**: `/api`

### GET /api/customers/search
Search for customers.

**Query Parameters**:
- Various search parameters

**Response**: Customer search results

---

## Overview Endpoint

**No Prefix** (mounted at root)

### GET /overview
Display dashboard with unpaid and overdue invoices.

**Response**: HTML page (`overview.html`) with:
- Unpaid invoices
- Overdue invoices
- Recent payment history
- Customer details

---

## Files Endpoint

**Prefix**: `/api/v1/files`

### GET /api/v1/files/{file_path}
Retrieve private files from ERPNext.

**Parameters**:
- `file_path` (path): Path to the file

**Response**: Streamed file download with proper authentication

---

## Data Models

### PaymentStatus Enum
```python
PENDING = "pending"       # Initial state after customer payment
RECEIVED = "received"     # Coach has received payment
TRANSFERRED = "transferred"  # Treasurer has received from coach
COMPLETED = "completed"   # Payment fully processed
```

### ProgramType Enum
```python
BJJ = "bjj"
NOGI = "nogi"
```

### BillingCycle Enum
```python
DAILY = "daily"
MONTHLY = "monthly"
SIX_MONTHS = "six_months"
YEARLY = "yearly"
```

---

## Error Handling

All endpoints return standard HTTP status codes:

| Code | Description |
|------|-------------|
| 200 | Success |
| 400 | Bad Request - Invalid input |
| 401 | Unauthorized - Authentication failed |
| 404 | Not Found - Resource doesn't exist |
| 500 | Internal Server Error |

Error responses include a `detail` field with the error message:
```json
{
  "detail": "Error description"
}
```
