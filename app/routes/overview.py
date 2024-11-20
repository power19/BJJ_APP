from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.templating import Jinja2Templates
from ..utils.erp_client import ERPNextClient, get_erp_client
from datetime import datetime
import json

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/overview")
async def get_overview(request: Request, erp_client: ERPNextClient = Depends(get_erp_client)):
    try:
        # Get all unpaid invoices
        api_endpoint = f"{erp_client.base_url}/api/method/frappe.client.get_list"
        params = {
            'doctype': 'Sales Invoice',
            'fields': '["*"]',
            'filters': json.dumps({
                'status': ['in', ['Unpaid', 'Overdue']],  # Get both unpaid and overdue invoices
                'docstatus': 1,  # Only submitted invoices
                'outstanding_amount': ['>', 0]  # Only invoices with remaining balance
            }),
            'order_by': 'due_date asc'  # Sort by due date
        }
        
        response = erp_client.session.get(api_endpoint, params=params)
        
        if response.status_code == 200:
            data = response.json()
            invoices = []
            today = datetime.now().date()
            
            for inv in data.get('message', []):
                due_date = datetime.strptime(inv.get('due_date'), '%Y-%m-%d').date()
                
                # Calculate days overdue or days until due
                days_difference = (due_date - today).days
                
                # Determine if invoice is overdue
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

            # Group invoices by status
            grouped_invoices = {
                'overdue': [inv for inv in invoices if inv['status'] == 'Overdue'],
                'unpaid': [inv for inv in invoices if inv['status'] == 'Unpaid']
            }
            
            # Sort by days overdue/until due
            grouped_invoices['overdue'] = sorted(grouped_invoices['overdue'], 
                                               key=lambda x: x['days_overdue'], 
                                               reverse=True)
            grouped_invoices['unpaid'] = sorted(grouped_invoices['unpaid'], 
                                              key=lambda x: x['days_until_due'])
            
            # Calculate totals
            totals = {
                'overdue': sum(inv['outstanding'] for inv in grouped_invoices['overdue']),
                'unpaid': sum(inv['outstanding'] for inv in grouped_invoices['unpaid']),
                'total': sum(inv['outstanding'] for inv in invoices)
            }

            return templates.TemplateResponse(
                "overview.html",
                {
                    "request": request,
                    "invoices": grouped_invoices,
                    "totals": totals
                }
            )
            
    except Exception as e:
        print(f"Error in overview: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))
