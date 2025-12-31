# Developer Guide

This document provides technical documentation for developers working on the Invictus BJJ application.

## Architecture Overview

The application follows a layered architecture:

```
┌─────────────────────────────────────────────────────────┐
│                     FastAPI Routes                       │
│              (app/routes/*.py)                          │
├─────────────────────────────────────────────────────────┤
│                    Service Layer                         │
│              (app/services/*.py)                         │
├─────────────────────────────────────────────────────────┤
│                   ERPNext Client                         │
│              (app/utils/erp_client.py)                   │
├─────────────────────────────────────────────────────────┤
│                     ERPNext API                          │
│                 (External System)                        │
└─────────────────────────────────────────────────────────┘
```

## Project Structure

```
BJJ_APP/
├── main.py                     # Application entry point
├── requirements.txt            # Python dependencies
├── app/
│   ├── models/                 # Pydantic data models
│   │   ├── customer.py         # Customer-related models
│   │   ├── payment.py          # Payment status and handover models
│   │   ├── billing.py          # Billing data models
│   │   └── enrollment.py       # Enrollment request/response models
│   ├── routes/                 # API endpoint handlers
│   │   ├── main.py             # Main page routes
│   │   ├── payment.py          # Payment processing endpoints
│   │   ├── handover.py         # Payment handover endpoints
│   │   ├── billing.py          # Billing query endpoints
│   │   ├── attendance.py       # Attendance tracking endpoints
│   │   ├── overview.py         # Dashboard endpoints
│   │   ├── customers.py        # Customer search endpoints
│   │   ├── enrollment.py       # Student enrollment endpoints
│   │   └── files.py            # File download endpoints
│   ├── services/               # Business logic
│   │   ├── payment_service.py  # Payment processing logic
│   │   ├── handover_service.py # Handover workflow logic
│   │   ├── billing_service.py  # Billing calculations
│   │   ├── attendance_service.py # Attendance tracking
│   │   └── enrollment_service.py # Enrollment processing
│   ├── utils/
│   │   ├── erp_client.py       # ERPNext API client
│   │   └── db.py               # Database utilities
│   ├── static/                 # Static assets
│   │   ├── css/                # Stylesheets
│   │   ├── js/                 # JavaScript files
│   │   └── images/             # Logo and images
│   └── templates/              # Jinja2 HTML templates
│       ├── base.html           # Base template
│       ├── index.html          # Homepage
│       ├── billing.html        # Billing page
│       ├── attendance.html     # Attendance page
│       ├── overview.html       # Dashboard
│       ├── enrollment.html     # Enrollment form
│       └── payment/            # Payment-related templates
```

## Development Setup

### Prerequisites

- Python 3.9+
- pip
- Access to ERPNext instance (development or production)

### Local Development

1. **Clone and setup**
   ```bash
   git clone <repository-url>
   cd BJJ_APP
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your ERPNext credentials
   ```

3. **Run development server**
   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `ERPNEXT_URL` | Base URL of ERPNext instance | Yes |
| `ERPNEXT_API_KEY` | API Key for authentication | Yes |
| `ERPNEXT_API_SECRET` | API Secret for authentication | Yes |

## Key Components

### ERPNext Client (`app/utils/erp_client.py`)

The `ERPNextClient` class handles all communication with ERPNext:

```python
class ERPNextClient:
    def __init__(self, base_url: str, api_key: str, api_secret: str):
        # Initialize with token-based authentication

    def search_customer(self, search_term: str) -> Dict[str, Any]:
        # Search customer by RFID

    def search_customer_by_name(self, customer_name: str) -> Dict[str, Any]:
        # Search customer by name

    def get_family_group(self, customer_name: str) -> Dict[str, Any]:
        # Get family group information

    def verify_staff_rfid(self, rfid: str) -> Dict[str, Any]:
        # Verify staff member and roles

    def get_customer_transactions(self, payer_name: str) -> Dict[str, Any]:
        # Get unpaid invoices for customer
```

### Dependency Injection

The ERPNext client is injected into route handlers using FastAPI's dependency injection:

```python
from ..utils.erp_client import ERPNextClient, get_erp_client

@router.get("/endpoint")
async def my_endpoint(erp_client: ERPNextClient = Depends(get_erp_client)):
    # erp_client is automatically injected
    pass
```

### Service Layer

Services contain business logic and are instantiated with the ERPNext client:

```python
class PaymentService:
    def __init__(self, erp_client: ERPNextClient):
        self.erp_client = erp_client

    async def process_payment(self, payment_request):
        # Business logic here
        pass
```

## Data Models

### Payment Models (`app/models/payment.py`)

```python
class PaymentStatus(str, Enum):
    PENDING = "pending"
    RECEIVED = "received"
    TRANSFERRED = "transferred"
    COMPLETED = "completed"

class PaymentHandoverRequest(BaseModel):
    payment_id: str
    treasurer_rfid: str
    handover_notes: Optional[str] = None
```

### Enrollment Models (`app/models/enrollment.py`)

```python
class ProgramType(str, Enum):
    BJJ = "bjj"
    NOGI = "nogi"

class BillingCycle(str, Enum):
    DAILY = "daily"
    MONTHLY = "monthly"
    SIX_MONTHS = "six_months"
    YEARLY = "yearly"

class EnrollmentRequest(BaseModel):
    student_name: str
    email: str
    phone: str
    date_of_birth: str
    program_type: ProgramType
    billing_cycle: BillingCycle
    start_date: str
```

## ERPNext Integration

### Authentication

All requests to ERPNext use token-based authentication:

```python
headers = {
    'Authorization': f'token {api_key}:{api_secret}',
    'Content-Type': 'application/json'
}
```

### Common API Patterns

**Get List**:
```python
endpoint = f"{base_url}/api/method/frappe.client.get_list"
params = {
    'doctype': 'Sales Invoice',
    'fields': '["*"]',
    'filters': json.dumps({'customer': customer_name})
}
response = session.get(endpoint, params=params)
```

**Create Document**:
```python
endpoint = f"{base_url}/api/method/frappe.client.insert"
data = {"doc": document_data}
response = session.post(endpoint, json=data)
```

**Submit Document**:
```python
endpoint = f"{base_url}/api/method/frappe.client.submit"
data = {"doc": document}
response = session.post(endpoint, json=data)
```

### Custom Fields

The application expects these custom fields in ERPNext:

| Doctype | Field | Type | Description |
|---------|-------|------|-------------|
| Customer | custom_customer_rfid | Data | RFID card number |
| Customer | custom_attendance | Text | JSON attendance data |
| Customer | custom_current_belt_rank | Select | Belt rank |
| Customer | custom_registration_fee | Currency | Registration fee |
| User | custom_user_rfid | Data | Staff RFID |

### Custom Doctypes

**Family Group**:
- `name`: Group identifier
- `primary_payer`: Link to Customer
- `family_members`: Child table with member links
- `status`: Active/Inactive

**Payment Handover**:
- `payment_entry`: Link to Payment Entry
- `received_by`: Link to User
- `received_at`: Datetime
- `transferred_to`: Link to User
- `transferred_at`: Datetime
- `handover_notes`: Text
- `status`: Select

## Templates

Templates use Jinja2 and extend a base template:

```html
{% extends "base.html" %}

{% block content %}
<!-- Page content here -->
{% endblock %}
```

### Template Variables

Common variables passed to templates:

```python
return templates.TemplateResponse(
    "template.html",
    {
        "request": request,  # Required by FastAPI
        "customer": customer_data,
        "invoices": invoice_list,
        # Additional data...
    }
)
```

## Adding New Features

### 1. Add Route

Create or modify route handler in `app/routes/`:

```python
@router.get("/new-feature")
async def new_feature(
    request: Request,
    erp_client: ERPNextClient = Depends(get_erp_client)
):
    service = MyService(erp_client)
    data = await service.get_data()
    return templates.TemplateResponse(
        "new_feature.html",
        {"request": request, "data": data}
    )
```

### 2. Add Service

Create service class in `app/services/`:

```python
class MyService:
    def __init__(self, erp_client: ERPNextClient):
        self.erp_client = erp_client

    async def get_data(self):
        # Business logic
        pass
```

### 3. Add Model (if needed)

Create Pydantic model in `app/models/`:

```python
from pydantic import BaseModel

class MyRequest(BaseModel):
    field1: str
    field2: Optional[int] = None
```

### 4. Register Route

Add router to `main.py`:

```python
from app.routes import new_feature
app.include_router(new_feature.router, prefix="/api/v1/new-feature")
```

## Error Handling

### Route-Level Error Handling

```python
@router.get("/endpoint")
async def endpoint(request: Request):
    try:
        # Logic here
        return result
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
```

### Service-Level Error Handling

Services should catch exceptions and return meaningful error data:

```python
async def process_data(self):
    try:
        # Logic
        return {"success": True, "data": result}
    except Exception as e:
        return {"success": False, "error": str(e)}
```

## Debugging

### Debug Endpoints

The application includes debug endpoints in `app/routes/billing.py`:

- `/debug/transactions/{customer}` - Raw transaction data
- `/debug/invoices/{customer}` - Invoice data
- `/debug/payment/{payment_id}` - Payment entry details
- `/debug/user/{user_id}` - User data and roles

### Logging

Use print statements for development debugging:

```python
print(f"DEBUG: Processing {data}")
print(f"Response: {response.text}")
```

For production, consider implementing proper logging.

## Testing

### Manual Testing

1. Start the development server
2. Use browser to access endpoints
3. Use ERPNext to verify data changes

### API Testing

Use curl or a tool like Postman:

```bash
# Test customer scan
curl -X POST http://localhost:8000/api/v1/payment/scan \
  -H "Content-Type: application/json" \
  -d '{"rfid": "12345"}'
```

## Deployment

### Production Considerations

1. **Environment Variables**: Use secure storage for credentials
2. **HTTPS**: Configure SSL/TLS
3. **Process Manager**: Use gunicorn or supervisor
4. **Reverse Proxy**: Use nginx for static files and SSL termination

### Example Production Command

```bash
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

## Common Issues

### ERPNext Connection Issues

- Verify credentials in `.env`
- Check ERPNext URL is accessible
- Verify API user has necessary permissions

### RFID Not Found

- Check `custom_customer_rfid` or `custom_user_rfid` field values
- Verify customer/user is enabled

### Role Verification Failing

- Check user has required roles in ERPNext
- Verify role names match exactly (case-sensitive)
