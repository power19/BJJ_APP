# User Guide

This guide explains how staff members can use the Invictus BJJ application for daily operations.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Processing Payments](#processing-payments)
3. [Payment Handover](#payment-handover)
4. [Attendance Tracking](#attendance-tracking)
5. [Viewing Billing Information](#viewing-billing-information)
6. [Enrolling New Students](#enrolling-new-students)
7. [Dashboard Overview](#dashboard-overview)

---

## Getting Started

### Accessing the System

Open your web browser and navigate to the application URL (typically `http://localhost:8000` or your configured domain).

### Requirements

- **RFID Card**: All staff members need a registered RFID card
- **Role Assignment**: Your ERPNext user account must have appropriate roles assigned
- **Web Browser**: Any modern browser (Chrome, Firefox, Safari, Edge)

### Home Page

The home page provides quick access to all main features:
- Payment Processing
- Attendance Tracking
- Enrollment
- Dashboard Overview

---

## Processing Payments

### Step 1: Customer Scan

1. Navigate to **Payment** section (`/api/v1/payment/`)
2. Have the customer scan their RFID card
3. The system will identify the customer and display their information

### Step 2: Invoice Selection

After the customer scan:
1. View all unpaid invoices for the customer
2. For family members, invoices from the primary payer will also be shown
3. Select which invoices to pay (you can select multiple)
4. Enter the payment amount for each selected invoice
5. Partial payments are supported

### Step 3: Staff Authorization

1. Scan your staff RFID card to authorize the payment
2. The system verifies you have the `Accounts User` role
3. Your name will be recorded as the payment receiver

### Step 4: Payment Confirmation

1. Review the payment summary
2. Confirm the payment
3. A Payment Entry is created in ERPNext
4. The payment will appear in the handover dashboard

### Tips for Payment Processing

- Always verify the customer's identity matches their RFID
- Double-check invoice amounts before confirming
- For family payments, ensure you're applying payment to the correct invoices
- Cash payments will need to be handed over to the treasurer

---

## Payment Handover

### For Coaches (Receiving Payments)

After collecting cash payments:
1. Keep track of all payments received during your shift
2. At the end of your shift, notify the treasurer
3. Payments will appear in the handover dashboard

### For Treasurers (Confirming Handovers)

1. Navigate to **Handover Dashboard** (`/api/v1/payment/handover/dashboard`)
2. View all pending payments from coaches
3. For each payment to confirm:
   - Click on the payment to view details
   - Verify the physical cash matches the amount shown
   - Scan your treasurer RFID card
   - Optionally add notes
   - Confirm the handover

### Viewing Payment History

1. Navigate to **Payment History** (`/api/v1/payment/history`)
2. View all recent payments with their handover status:
   - **Pending**: Awaiting handover to treasurer
   - **Transferred**: Successfully handed over

---

## Attendance Tracking

### Scanning Attendance

1. Navigate to **Attendance** (`/api/v1/attendance`)
2. Have the student scan their RFID card
3. The system records the timestamp automatically
4. Attendance is recorded in the customer's record

### Viewing Attendance Records

1. After scanning, the system displays the student's attendance calendar
2. Use the week navigation to view different weeks
3. Attendance records show:
   - Date and time of each attendance
   - Weekly attendance count
   - Historical attendance data

### Week Navigation

- Use the arrow buttons to navigate between weeks
- Current week is shown by default
- Attendance history is stored indefinitely

---

## Viewing Billing Information

### Customer Billing Page

1. Navigate to **Billing** (`/api/v1/billing/customer/{customer_name}`)
2. View comprehensive billing information:
   - Customer details
   - Belt rank
   - Outstanding invoices
   - Payment history
   - Family group information (if applicable)

### Information Displayed

| Section | Details |
|---------|---------|
| Customer Info | Name, contact details, RFID, belt rank |
| Invoices | All invoices with amounts and due dates |
| Payments | Historical payments and their status |
| Family | Family group membership and primary payer |

---

## Enrolling New Students

### Enrollment Form

1. Navigate to **Enrollment** (`/api/v1/enrollment/`)
2. Fill out the enrollment form:

| Field | Description |
|-------|-------------|
| Student Name | Full legal name |
| Email | Contact email address |
| Phone | Contact phone number |
| Date of Birth | Student's date of birth |
| Program | BJJ or No-Gi |
| Billing Cycle | Daily, Monthly, 6 Months, or Yearly |
| Start Date | When training begins |

### Available Programs

**Brazilian Jiu-Jitsu (BJJ)**
- Traditional BJJ training with Gi
- Pricing varies by billing cycle

**No-Gi Jiu-Jitsu**
- Grappling without the Gi
- Same pricing structure as BJJ

### Billing Cycle Options

| Cycle | Description |
|-------|-------------|
| Daily | Single class drop-in |
| Monthly | Recurring monthly membership |
| 6 Months | 6-month commitment (discounted) |
| Yearly | Annual membership (best value) |

### After Enrollment

1. System creates customer record in ERPNext
2. First invoice is automatically generated
3. Student is ready for training and attendance tracking

---

## Dashboard Overview

### Accessing the Dashboard

Navigate to **Overview** (`/overview`) to see the main dashboard.

### Dashboard Sections

#### Unpaid Invoices
- List of all unpaid invoices
- Shows customer name, amount, and due date
- Days until due or days overdue

#### Overdue Invoices
- Invoices past their due date
- Highlighted for priority attention
- Shows days overdue

#### Recent Payments
- Payments from the last 30 days
- Shows payment amount and date
- Handover status

### Using the Dashboard

1. Check dashboard at the start of each day
2. Follow up on overdue invoices
3. Monitor pending payments awaiting handover
4. Track overall payment activity

---

## Common Tasks Quick Reference

| Task | Location |
|------|----------|
| Process a payment | `/api/v1/payment/` |
| Record attendance | `/api/v1/attendance` |
| View pending handovers | `/api/v1/payment/handover/dashboard` |
| Confirm a handover | `/api/v1/payment/handover/process/{payment_id}` |
| Enroll new student | `/api/v1/enrollment/` |
| View billing info | `/api/v1/billing/customer/{name}` |
| Check dashboard | `/overview` |
| View payment history | `/api/v1/payment/history` |

---

## Troubleshooting

### RFID Not Recognized

1. Ensure the card is properly positioned on the reader
2. Try scanning again slowly
3. Verify the RFID is registered in the system
4. Contact administrator if problem persists

### Payment Not Processing

1. Verify you have the required role
2. Check your RFID is valid
3. Ensure customer has valid invoices
4. Check internet connection to ERPNext

### Customer Not Found

1. Verify customer is registered in ERPNext
2. Check if RFID is correctly linked to customer
3. Try searching by name in billing section

### Need Help?

Contact your system administrator for:
- RFID registration issues
- Role assignment
- ERPNext access problems
- System errors
