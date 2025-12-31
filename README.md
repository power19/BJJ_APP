# Invictus BJJ

A FastAPI-based web application for managing operations at Invictus Brazilian Jiu-Jitsu gym. The system integrates with ERPNext for backend data management and provides features for payments, attendance tracking, billing, student enrollment, and payment handover workflows.

## Features

- **Payment Processing** - RFID-based customer scanning, invoice selection, and payment handling
- **Payment Handover** - Track payment transfers from coaches to treasurers with full audit trail
- **Attendance Tracking** - RFID-based check-in with weekly calendar views
- **Billing Management** - Customer billing information and invoice management
- **Student Enrollment** - New student registration with automatic invoice generation
- **Family Group Support** - Consolidated billing for family members

## Technology Stack

- **Framework**: FastAPI 0.104.1
- **Server**: Uvicorn 0.24.0
- **Templating**: Jinja2 3.1.2
- **Validation**: Pydantic 2.4.2
- **HTTP Client**: Requests 2.31.0
- **Backend Integration**: ERPNext

## Prerequisites

- Python 3.9+
- Access to an ERPNext instance
- ERPNext API credentials (API Key and Secret)

## Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd BJJ_APP
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**

   Create a `.env` file in the project root:
   ```env
   ERPNEXT_URL=https://your-erpnext-instance.com
   ERPNEXT_API_KEY=your_api_key
   ERPNEXT_API_SECRET=your_api_secret
   ```

5. **Run the application**
   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

   The application will be available at `http://localhost:8000`

## Project Structure

```
BJJ_APP/
├── main.py                    # FastAPI application entry point
├── requirements.txt           # Python dependencies
├── .env                       # Environment configuration (not in repo)
├── app/
│   ├── models/               # Pydantic data models
│   │   ├── customer.py
│   │   ├── payment.py
│   │   ├── billing.py
│   │   └── enrollment.py
│   ├── routes/               # API endpoint handlers
│   │   ├── main.py
│   │   ├── payment.py
│   │   ├── handover.py
│   │   ├── billing.py
│   │   ├── attendance.py
│   │   ├── overview.py
│   │   ├── customers.py
│   │   ├── enrollment.py
│   │   └── files.py
│   ├── services/             # Business logic layer
│   │   ├── payment_service.py
│   │   ├── handover_service.py
│   │   ├── billing_service.py
│   │   ├── attendance_service.py
│   │   └── enrollment_service.py
│   ├── utils/
│   │   ├── erp_client.py     # ERPNext API client
│   │   └── db.py
│   ├── static/               # Static assets (CSS, JS, images)
│   └── templates/            # Jinja2 HTML templates
```

## ERPNext Integration

The application requires the following ERPNext configuration:

### Custom Fields
- `Customer.custom_customer_rfid` - RFID card number for customers
- `Customer.custom_attendance` - JSON field for attendance records
- `Customer.custom_current_belt_rank` - Belt rank tracking
- `Customer.custom_registration_fee` - Registration fee amount
- `User.custom_user_rfid` - RFID card number for staff members

### Custom Doctypes
- **Family Group** - Links family members with a primary payer
- **Payment Handover** - Tracks payment transfers between staff

### Required Roles
- **Accounts User** - Can authorize payments
- **Treasurer** - Can confirm payment handovers
- **Head Coach** - Can confirm payment handovers
- **System Manager** - Full access

## Currency

The application uses **SRD (Surinamese Dollar)** as the default currency.

## Quick Start

1. Access the homepage at `http://localhost:8000`
2. Navigate to different features:
   - `/api/v1/payment/` - Payment processing
   - `/api/v1/attendance` - Attendance scanning
   - `/api/v1/enrollment/` - Student enrollment
   - `/overview` - Dashboard with unpaid invoices
   - `/api/v1/payment/handover/dashboard` - Payment handover management

## Documentation

- [API Documentation](API.md) - Complete API endpoint reference
- [Payment Handover Guide](PAYMENT_HANDOVER.md) - Payment handover workflow details
- [User Guide](USER_GUIDE.md) - Staff usage instructions
- [Developer Guide](DEVELOPER.md) - Technical documentation for developers

## License

Proprietary - Invictus BJJ
