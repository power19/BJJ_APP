# Payment Handover System

The Payment Handover system provides a complete audit trail for tracking cash payments as they move from coaches to treasurers. This ensures accountability and transparency in payment handling.

## Overview

When a student makes a cash payment at the gym, a coach typically receives the money. This payment must then be transferred to the treasurer or head coach for proper accounting. The handover system tracks:

1. **Who received the payment** - The coach/staff member who collected the payment
2. **When it was received** - Timestamp of the original payment
3. **Who confirmed the handover** - The treasurer/head coach who received the money
4. **When it was transferred** - Timestamp of the handover
5. **Any notes** - Optional notes about the handover

## Payment Flow

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│    CUSTOMER     │────>│     COACH       │────>│   TREASURER     │
│  Makes Payment  │     │ Receives Cash   │     │ Confirms Receipt│
└─────────────────┘     └─────────────────┘     └─────────────────┘
                              │                        │
                              ▼                        ▼
                        ┌───────────┐           ┌───────────┐
                        │  PENDING  │──────────>│TRANSFERRED│
                        └───────────┘           └───────────┘
```

## Payment Status States

| Status | Description |
|--------|-------------|
| `PENDING` | Payment received by coach, awaiting handover to treasurer |
| `RECEIVED` | Coach has acknowledged receiving the payment |
| `TRANSFERRED` | Treasurer/Head Coach has confirmed receiving the payment |
| `COMPLETED` | Payment fully processed in the accounting system |

## User Roles

### Who Can Receive Payments (Coaches)
- Any staff member with `Accounts User` role
- Staff must have a valid RFID card configured in ERPNext

### Who Can Confirm Handovers (Treasurers)
Only the following roles can confirm payment handovers:
- `Treasurer`
- `Head Coach`
- `Accounts User`
- `System Manager`
- `Administrator`

## How It Works

### Step 1: Coach Receives Payment

1. Customer scans their RFID card at `/api/v1/payment/`
2. System displays unpaid invoices for the customer
3. Customer selects invoices to pay
4. Coach scans their RFID card to authorize the payment
5. Payment Entry is created in ERPNext with status `PENDING`

### Step 2: Treasurer Confirms Handover

1. Treasurer accesses the Handover Dashboard at `/api/v1/payment/handover/dashboard`
2. Dashboard shows all pending payments awaiting handover
3. Treasurer clicks on a payment to view details
4. Treasurer scans their RFID card to confirm receipt
5. System creates a `Payment Handover` record in ERPNext
6. Payment status changes to `TRANSFERRED`

## API Endpoints

### Handover Dashboard
```
GET /api/v1/payment/handover/dashboard
```
Shows all payments pending handover with:
- Payment ID and date
- Customer name
- Amount
- Coach who received it
- Related invoices

### Process Handover
```
GET /api/v1/payment/handover/process/{payment_id}
```
Displays confirmation screen with:
- Full payment details
- Invoice breakdown
- Coach information
- RFID input for treasurer

### Confirm Handover
```
POST /api/v1/payment/handover/confirm
```
Request body:
```json
{
  "rfid": "treasurer-rfid",
  "payment_id": "PE-00001",
  "notes": "Optional handover notes"
}
```

### Payment History
```
GET /api/v1/payment/handover/history?days=30
```
Shows historical payments with handover status.

## ERPNext Integration

### Custom Doctype: Payment Handover

The system creates a `Payment Handover` document in ERPNext with the following fields:

| Field | Type | Description |
|-------|------|-------------|
| `payment_entry` | Link | Reference to the Payment Entry |
| `received_by` | Link (User) | Staff member who received payment |
| `received_at` | Datetime | When payment was received |
| `transferred_to` | Link (User) | Treasurer who confirmed handover |
| `transferred_at` | Datetime | When handover was confirmed |
| `handover_notes` | Text | Optional notes |
| `status` | Select | Current status (Transferred) |

### Workflow

1. When a payment is created, it has no associated `Payment Handover` record
2. The system queries for payments without handover records to populate the dashboard
3. Upon confirmation, a new `Payment Handover` document is created and submitted
4. The handover record links back to the original Payment Entry

## Security

### RFID Verification
- All operations require valid RFID authentication
- Staff RFID must be registered in ERPNext (`User.custom_user_rfid`)
- System verifies user roles before allowing operations

### Role-Based Access
- Only authorized roles can confirm handovers
- System checks role membership before processing
- Unauthorized attempts are rejected with appropriate error messages

## Viewing Handover History

### Payment History Page
Access at `/api/v1/payment/history` to view:
- All payments within specified date range
- Handover status for each payment
- Who received and who transferred
- Timestamps for all actions

### History Data
Each payment entry shows:
```json
{
  "payment_id": "PE-00001",
  "date": "2024-01-15",
  "customer_name": "John Doe",
  "amount": 400.00,
  "received_by": "Coach Name",
  "transferred_to": "Treasurer Name",
  "transferred_at": "2024-01-15 15:30:00",
  "status": "transferred",
  "handover_notes": "End of day handover"
}
```

## Best Practices

1. **Daily Handovers** - Coaches should hand over payments to treasurers at the end of each day
2. **Verify Amounts** - Treasurers should verify physical cash matches the system amount before confirming
3. **Add Notes** - Use handover notes for any discrepancies or special circumstances
4. **Regular Audits** - Review payment history regularly to ensure all payments are accounted for

## Troubleshooting

### Payment Not Appearing in Dashboard
- Verify the Payment Entry is submitted (docstatus = 1)
- Check that payment_type is "Receive"
- Ensure no existing Payment Handover record exists

### Handover Confirmation Fails
- Verify treasurer RFID is correct
- Check treasurer has required role
- Ensure Payment Entry still exists

### History Not Showing Payments
- Adjust the `days` parameter for wider date range
- Check ERPNext connection is working
- Verify Payment Handover records are submitted
