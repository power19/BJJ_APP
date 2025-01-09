from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.templating import Jinja2Templates
from ..utils.erp_client import ERPNextClient, get_erp_client
from datetime import datetime, timedelta
import json

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/overview")
async def get_overview(request: Request, days: int = 7, erp_client: ERPNextClient = Depends(get_erp_client)):
    try:
        # Get all unpaid invoices
        api_endpoint = f"{erp_client.base_url}/api/method/frappe.client.get_list"
        invoice_params = {
            'doctype': 'Sales Invoice',
            'fields': '["*"]',
            'filters': json.dumps({
                'status': ['in', ['Unpaid', 'Overdue']],  # Get both unpaid and overdue invoices
                'docstatus': 1,  # Only submitted invoices
                'outstanding_amount': ['>', 0]  # Only invoices with remaining balance
            }),
            'order_by': 'due_date asc'  # Sort by due date
        }
        
        # Get recent payments for the specified time period
        payment_params = {
            'doctype': 'Payment Entry',
            'fields': '["*"]',
            'filters': json.dumps({
                'payment_type': 'Receive',
                'docstatus': 1,  # Submitted payments
                'posting_date': ['>=', (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')]
            }),
            'order_by': 'creation desc'
        }
        
        print("\nFetching invoices and payments...")
        invoice_response = erp_client.session.get(api_endpoint, params=invoice_params)
        payment_response = erp_client.session.get(api_endpoint, params=payment_params)
        
        print(f"\nInvoice response status: {invoice_response.status_code}")
        print(f"Invoice response: {invoice_response.text[:500]}...")
        
        print(f"\nPayment response status: {payment_response.status_code}")
        print(f"Payment response: {payment_response.text[:500]}...")
        
        invoices = []
        recent_payments = []
        today = datetime.now().date()
        
        # Process invoice data
        if invoice_response.status_code == 200:
            data = invoice_response.json()
            
            for inv in data.get('message', []):
                due_date = datetime.strptime(inv.get('due_date'), '%Y-%m-%d').date()
                days_difference = (due_date - today).days
                is_overdue = days_difference < 0
                
                # Get customer details
                customer = erp_client.search_customer_by_name(inv.get('customer'))
                family_group = erp_client.get_family_group(inv.get('customer')) if customer else None
                
                invoice_data = {
                    'invoice_number': inv.get('name'),
                    'customer_name': inv.get('customer'),
                    'due_date': inv.get('due_date'),
                    'amount': float(inv.get('grand_total', 0)),
                    'outstanding': float(inv.get('outstanding_amount', 0)),
                    'status': 'Overdue' if is_overdue else 'Unpaid',
                    'days_overdue': abs(days_difference) if is_overdue else 0,
                    'days_until_due': days_difference if not is_overdue else 0,
                    'family_group': family_group.get('name') if family_group else None,
                    'family_package': family_group.get('package_type') if family_group else 'Individual',
                    'customer_details': {
                        'belt_rank': customer.get('custom_current_belt_rank') if customer else None,
                        'email': customer.get('email_id'),
                        'phone': customer.get('mobile_no')
                    } if customer else {}
                }
                
                invoices.append(invoice_data)

            # Group and sort invoices
            grouped_invoices = {
                'overdue': sorted(
                    [inv for inv in invoices if inv['status'] == 'Overdue'],
                    key=lambda x: x['days_overdue'],
                    reverse=True
                ),
                'unpaid': sorted(
                    [inv for inv in invoices if inv['status'] == 'Unpaid'],
                    key=lambda x: x['days_until_due']
                )
            }
            
            # Calculate totals
            totals = {
                'overdue': sum(inv['outstanding'] for inv in grouped_invoices['overdue']),
                'unpaid': sum(inv['outstanding'] for inv in grouped_invoices['unpaid']),
                'total': sum(inv['outstanding'] for inv in invoices)
            }
        else:
            grouped_invoices = {'overdue': [], 'unpaid': []}
            totals = {'overdue': 0, 'unpaid': 0, 'total': 0}
        
        # Process payment data
        if payment_response.status_code == 200:
            payments_data = payment_response.json().get('message', [])
            
            for payment in payments_data:
                # Get detailed payment entry
                detail_response = erp_client.session.get(
                    f"{erp_client.base_url}/api/resource/Payment Entry/{payment.get('name')}"
                )
                
                if detail_response.status_code == 200:
                    payment_detail = detail_response.json().get('data', {})
                    
                    # Get staff information - First try authorized_by_staff
                    staff_user_id = payment_detail.get('authorized_by_staff')
                    processed_by = None
                    processed_time = None
                    
                    if staff_user_id:
                        # Look up staff name from User document
                        user_response = erp_client.session.get(
                            f"{erp_client.base_url}/api/resource/User/{staff_user_id}"
                        )
                        if user_response.status_code == 200:
                            user_data = user_response.json().get('data', {})
                            processed_by = user_data.get('full_name')
                            processed_time = payment_detail.get('authorization_time')
                    
                    # If no authorized_by_staff, fall back to owner
                    if not processed_by:
                        owner_id = payment_detail.get('owner')
                        if owner_id:
                            user_response = erp_client.session.get(
                                f"{erp_client.base_url}/api/resource/User/{owner_id}"
                            )
                            if user_response.status_code == 200:
                                user_data = user_response.json().get('data', {})
                                processed_by = user_data.get('full_name')
                                processed_time = payment_detail.get('creation')

                    # Get referenced invoices
                    invoice_refs = []
                    for ref in payment_detail.get('references', []):
                        if ref.get('reference_doctype') == 'Sales Invoice':
                            invoice_refs.append(ref.get('reference_name'))

                    # Build payment data structure
                    payment_data = {
                        'payment_id': payment.get('name'),
                        'customer': payment.get('party'),
                        'amount': float(payment.get('paid_amount', 0)),
                        'date': payment.get('posting_date'),
                        'reference': payment.get('reference_no'),
                        'processed_by': processed_by or 'Unknown',
                        'processed_at': processed_time or payment.get('creation'),
                        'staff_notes': payment_detail.get('staff_notes', ''),
                        'invoices': invoice_refs
                    }
                    
                    print(f"Processed payment data: {json.dumps(payment_data, indent=2)}")
                    recent_payments.append(payment_data)

        # Debug print before returning
        print("\nData being passed to template:")
        print(f"Grouped invoices: {json.dumps(grouped_invoices, indent=2)}")
        print(f"Totals: {json.dumps(totals, indent=2)}")
        print(f"Recent payments count: {len(recent_payments)}")
        if recent_payments:
            print(f"Sample payment: {json.dumps(recent_payments[0], indent=2)}")

        return templates.TemplateResponse(
            "overview.html",
            {
                "request": request,
                "invoices": grouped_invoices,
                "totals": totals,
                "recent_payments": recent_payments,
                "days": days,
                "debug": True
            }
        )
            
    except Exception as e:
        print(f"Error in overview: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))