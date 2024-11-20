# app/routes/billing.py
from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.templating import Jinja2Templates
from typing import Dict, Any
import json
from ..services.billing_service import BillingService
from ..utils.erp_client import ERPNextClient, get_erp_client

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/customer/{customer_name}")
async def get_billing_page(
    request: Request,
    customer_name: str,
    erp_client: ERPNextClient = Depends(get_erp_client)
):
    print(f"DEBUG: Accessing billing for customer: {customer_name}")
    try:
        billing_service = BillingService(erp_client)
        billing_info = await billing_service.get_customer_billing(customer_name)
        
        # Debug print
        print(f"DEBUG: Billing info received: {json.dumps(billing_info, indent=2)}")
        
        return templates.TemplateResponse(
            "billing.html",
            {
                "request": request, 
                "billing_info": billing_info,
                "debug": True  # Enable debug output in template
            }
        )
    except Exception as e:
        print(f"ERROR in billing page: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/customer/ui/{customer_name}")
async def get_billing_page(
    request: Request,
    customer_name: str,
    erp_client: ERPNextClient = Depends(get_erp_client)
):
    try:
        billing_service = BillingService(erp_client)
        billing_info = await billing_service.get_customer_billing(customer_name)
        return templates.TemplateResponse(
            "billing.html",
            {"request": request, "billing_info": billing_info}
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/test/search/{customer_name}")
async def test_customer_search(
    customer_name: str,
    erp_client: ERPNextClient = Depends(get_erp_client)
):
    try:
        print(f"\nTesting search for: {customer_name}")
        
        # Test connection
        test_endpoint = f"{erp_client.base_url}/api/method/frappe.auth.get_logged_user"
        test_response = erp_client.session.get(test_endpoint)
        print(f"Connection test response: {test_response.status_code}")
        
        # Search for customer
        customer = erp_client.search_customer_by_name(customer_name)
        
        # Get list of all customers
        endpoint = f"{erp_client.base_url}/api/resource/Customer"
        response = erp_client.session.get(
            endpoint,
            params={'fields': '["name", "customer_name", "email_id", "mobile_no"]'}
        )
        all_customers = response.json()
        
        return {
            "connection_status": test_response.status_code,
            "search_term": customer_name,
            "customer_found": bool(customer),
            "customer_details": customer,
            "all_customers": all_customers.get("data", [])[:20],  # Show first 20 customers
            "erp_url": erp_client.base_url
        }
        
    except Exception as e:
        return {
            "error": str(e),
            "stage": "search test",
            "erp_url": erp_client.base_url
        }
# app/routes/billing.py
@router.get("/debug/transactions/{customer_name}")
async def debug_transactions(
    customer_name: str,
    erp_client: ERPNextClient = Depends(get_erp_client)
):
    """Debug endpoint to see raw transaction data"""
    try:
        # Get customer
        customer = erp_client.search_customer_by_name(customer_name)
        if not customer:
            return {"error": "Customer not found"}

        # Get raw transaction data
        transactions = erp_client.get_customer_transactions(customer["customer_name"])
        
        return {
            "customer": customer,
            "raw_transactions": transactions,
            "transaction_count": len(transactions.get("data", [])),
            "types_found": list(set(t["type"] for t in transactions.get("data", []) if isinstance(t, dict)))
        }
    except Exception as e:
        return {"error": str(e)}
    
# app/routes/billing.py
@router.get("/debug/invoices/{customer_name}")
async def debug_invoices(
    customer_name: str,
    erp_client: ERPNextClient = Depends(get_erp_client)
):
    """Debug endpoint to check sales invoices directly"""
    try:
        # Get customer
        customer = erp_client.search_customer_by_name(customer_name)
        if not customer:
            return {"error": "Customer not found"}
            
        # Get raw invoice data
        endpoint = f"{erp_client.base_url}/api/resource/Sales Invoice"
        
        # Try different filter combinations
        filters = [
            ["or", 
                ["customer", "=", customer["name"]],
                ["customer", "=", customer["customer_name"]],
                ["customer_name", "=", customer["customer_name"]]
            ]
        ]
        
        params = {
            'fields': '["*"]',
            'filters': json.dumps(filters)
        }
        
        response = erp_client.session.get(endpoint, params=params)
        invoices_data = response.json()
        
        return {
            "customer": {
                "id": customer["name"],
                "name": customer["customer_name"]
            },
            "params_used": params,
            "raw_response": invoices_data,
            "invoice_count": len(invoices_data.get("data", [])),
            "invoices_found": [
                {
                    "number": inv.get("name"),
                    "date": inv.get("posting_date"),
                    "amount": inv.get("grand_total"),
                    "status": inv.get("status")
                }
                for inv in invoices_data.get("data", [])
            ]
        }
    except Exception as e:
        return {
            "error": str(e),
            "customer_name": customer_name
        }

# app/routes/billing.py
@router.get("/debug/doctypes")
async def debug_doctypes(
    erp_client: ERPNextClient = Depends(get_erp_client)
):
    """Debug endpoint to check available doctypes"""
    try:
        # Check available doctypes
        doctype_endpoint = f"{erp_client.base_url}/api/method/frappe.desk.desktop.get_doctypes"
        doctype_response = erp_client.session.get(doctype_endpoint)
        
        # Try a basic list endpoint
        list_endpoint = f"{erp_client.base_url}/api/resource/DocType"
        list_response = erp_client.session.get(list_endpoint)
        
        return {
            "doctype_response": doctype_response.json() if doctype_response.status_code == 200 else None,
            "list_response": list_response.json() if list_response.status_code == 200 else None,
            "status": {
                "doctype_status": doctype_response.status_code,
                "list_status": list_response.status_code
            }
        }
    except Exception as e:
        return {"error": str(e)}

@router.get("/debug/test-endpoints")
async def test_endpoints(
    erp_client: ERPNextClient = Depends(get_erp_client)
):
    """Test various ERPNext endpoints"""
    results = {}
    
    # Test various endpoints
    endpoints = [
        "/api/resource/Sales Invoice",
        "/api/resource/Invoice",
        "/api/resource/Sales Order",
        "/api/method/frappe.desk.desktop.get_doctypes"
    ]
    
    for endpoint in endpoints:
        try:
            full_url = f"{erp_client.base_url}{endpoint}"
            response = erp_client.session.get(full_url)
            results[endpoint] = {
                "status": response.status_code,
                "content": response.json() if response.status_code == 200 else None
            }
        except Exception as e:
            results[endpoint] = {
                "error": str(e)
            }
            
    return results

# app/routes/billing.py
@router.get("/debug/api-test/{customer_name}")
async def test_api_methods(
    customer_name: str,
    erp_client: ERPNextClient = Depends(get_erp_client)
):
    """Test various API methods"""
    try:
        # Get customer first
        customer = erp_client.search_customer_by_name(customer_name)
        if not customer:
            return {"error": "Customer not found"}

        results = {}
        
        # Test different API methods
        methods = [
            {
                "name": "get_list",
                "endpoint": "/api/method/frappe.client.get_list",
                "params": {
                    "doctype": "Sales Invoice",
                    "fields": '["*"]',
                    "filters": json.dumps({
                        "customer": customer["name"]
                    })
                }
            },
            {
                "name": "get_value",
                "endpoint": "/api/method/frappe.client.get_value",
                "params": {
                    "doctype": "Sales Invoice",
                    "filters": json.dumps({
                        "customer": customer["name"]
                    }),
                    "fieldname": '["name", "grand_total", "status"]'
                }
            },
            {
                "name": "count",
                "endpoint": "/api/method/frappe.client.get_count",
                "params": {
                    "doctype": "Sales Invoice",
                    "filters": json.dumps({
                        "customer": customer["name"]
                    })
                }
            }
        ]
        
        for method in methods:
            try:
                full_url = f"{erp_client.base_url}{method['endpoint']}"
                response = erp_client.session.get(full_url, params=method["params"])
                results[method["name"]] = {
                    "status": response.status_code,
                    "content": response.json() if response.status_code == 200 else response.text,
                    "url": full_url,
                    "params": method["params"]
                }
            except Exception as e:
                results[method["name"]] = {
                    "error": str(e)
                }

        return {
            "customer": {
                "id": customer["name"],
                "name": customer["customer_name"]
            },
            "results": results
        }
                
    except Exception as e:
        return {"error": str(e)}