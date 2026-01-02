# app/routes/billing.py
from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from typing import Dict, Any
import json
from ..services.billing_service import BillingService
from ..services.auto_billing import get_billing_service
from ..utils.erp_client import ERPNextClient, get_erp_client

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


# =============================================================================
# Auto-Billing Endpoints
# =============================================================================

@router.get("/auto/preview")
async def preview_billing():
    """
    Preview upcoming invoices without creating them.
    Shows which members are due for billing and the expected amounts.
    """
    billing_service = get_billing_service()
    preview = billing_service.preview_billing_cycle()
    return JSONResponse(preview)


@router.post("/auto/run")
async def run_billing_cycle():
    """
    Run the billing cycle - generate invoices for all members due.
    Creates Sales Invoices in ERPNext for members with recurring memberships.
    """
    billing_service = get_billing_service()
    result = billing_service.run_billing_cycle()
    return JSONResponse(result)


@router.get("/auto/due")
async def get_members_due():
    """Get list of members due for billing today."""
    billing_service = get_billing_service()
    if not billing_service._setup_connection():
        return JSONResponse({"success": False, "error": "ERPNext not connected"})

    members = billing_service.get_members_due_for_billing()
    return JSONResponse({
        "success": True,
        "count": len(members),
        "members": members
    })


@router.get("/auto/test-invoice")
async def test_invoice_creation():
    """Test invoice creation with a single member to see detailed errors."""
    import requests
    from app.utils.config import get_config

    config = get_config()
    if not config.is_configured():
        return JSONResponse({"success": False, "error": "Not configured"})

    erp_config = config.get_erpnext_config()
    url = erp_config.get('url', '')
    headers = {
        'Authorization': f"token {erp_config.get('api_key', '')}:{erp_config.get('api_secret', '')}",
        'Content-Type': 'application/json'
    }
    company = config.get_company()

    # If company not configured, fetch from ERPNext
    if not company:
        try:
            resp = requests.get(
                f"{url}/api/resource/Company",
                headers=headers,
                params={"fields": '["name"]', "limit_page_length": 1},
                timeout=10
            )
            if resp.status_code == 200:
                companies = resp.json().get("data", [])
                if companies:
                    company = companies[0].get("name")
        except:
            pass

    results = {"steps": [], "company": company}

    # Step 1: Check if Item Group "Services" exists
    try:
        resp = requests.get(
            f"{url}/api/resource/Item Group/Services",
            headers=headers,
            timeout=10
        )
        results["steps"].append({
            "step": "Check Item Group 'Services'",
            "exists": resp.status_code == 200
        })

        if resp.status_code != 200:
            # Try to find available item groups
            resp2 = requests.get(
                f"{url}/api/resource/Item Group",
                headers=headers,
                params={"fields": '["name"]', "limit_page_length": 20},
                timeout=10
            )
            if resp2.status_code == 200:
                results["available_item_groups"] = [g["name"] for g in resp2.json().get("data", [])]
    except Exception as e:
        results["steps"].append({"step": "Check Item Group", "error": str(e)})

    # Step 2: Check for a test customer
    try:
        resp = requests.get(
            f"{url}/api/resource/Customer",
            headers=headers,
            params={"fields": '["name", "customer_name"]', "limit_page_length": 1},
            timeout=10
        )
        if resp.status_code == 200:
            customers = resp.json().get("data", [])
            results["steps"].append({
                "step": "Check Customers",
                "found": len(customers),
                "first_customer": customers[0] if customers else None
            })
    except Exception as e:
        results["steps"].append({"step": "Check Customers", "error": str(e)})

    # Step 3: Try to create a test invoice
    try:
        test_customer = results["steps"][-1].get("first_customer", {}).get("name") if results["steps"] else None
        if test_customer:
            # First ensure we have an item
            item_resp = requests.get(
                f"{url}/api/resource/Item",
                headers=headers,
                params={"fields": '["name", "item_code"]', "limit_page_length": 1},
                timeout=10
            )
            items = item_resp.json().get("data", []) if item_resp.status_code == 200 else []

            if items:
                item_code = items[0].get("item_code") or items[0].get("name")

                invoice_data = {
                    "doctype": "Sales Invoice",
                    "customer": test_customer,
                    "company": company,
                    "items": [{"item_code": item_code, "qty": 1, "rate": 100}]
                }

                resp = requests.post(
                    f"{url}/api/resource/Sales Invoice",
                    headers=headers,
                    json=invoice_data,
                    timeout=15
                )

                if resp.status_code in [200, 201]:
                    invoice_name = resp.json().get("data", {}).get("name")

                    # Try to submit the invoice
                    submit_resp = requests.post(
                        f"{url}/api/method/run_doc_method",
                        headers=headers,
                        json={"dt": "Sales Invoice", "dn": invoice_name, "method": "submit"},
                        timeout=10
                    )

                    results["steps"].append({
                        "step": "Create Test Invoice",
                        "status_code": resp.status_code,
                        "invoice_name": invoice_name,
                        "submit_status": submit_resp.status_code,
                        "submitted": submit_resp.status_code == 200,
                        "submit_response": submit_resp.json() if submit_resp.status_code == 200 else submit_resp.text[:500]
                    })
                else:
                    results["steps"].append({
                        "step": "Create Test Invoice",
                        "status_code": resp.status_code,
                        "response": resp.json() if resp.status_code != 500 else resp.text[:1000]
                    })
            else:
                results["steps"].append({"step": "Create Test Invoice", "error": "No items found in system"})
        else:
            results["steps"].append({"step": "Create Test Invoice", "error": "No customers found"})
    except Exception as e:
        results["steps"].append({"step": "Create Test Invoice", "error": str(e)})

    return JSONResponse(results)


# =============================================================================
# Customer Billing Endpoints
# =============================================================================

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

@router.get("/debug/payment/{payment_id}")
async def debug_payment(
    payment_id: str,
    erp_client: ERPNextClient = Depends(get_erp_client)
):
    """Debug endpoint to check raw payment entry data"""
    try:
        # First get the basic payment entry
        response = erp_client.session.get(
            f"{erp_client.base_url}/api/resource/Payment Entry/{payment_id}"
        )
        
        if response.status_code != 200:
            return {"error": "Failed to fetch payment entry"}

        payment_data = response.json()
        
        # Get doctype metadata to see available fields
        meta_response = erp_client.session.get(
            f"{erp_client.base_url}/api/method/frappe.desk.form.meta.get_meta",
            params={"doctype": "Payment Entry"}
        )
        
        # Get any custom fields
        custom_fields_response = erp_client.session.get(
            f"{erp_client.base_url}/api/resource/Custom Field",
            params={
                'filters': json.dumps([["dt", "=", "Payment Entry"]]),
                'fields': '["*"]'
            }
        )
        
        # Get document's version history
        version_response = erp_client.session.get(
            f"{erp_client.base_url}/api/method/frappe.core.page.version.version.get_version_timeline",
            params={
                "docname": payment_id,
                "doctype": "Payment Entry"
            }
        )

        return {
            "payment_entry": payment_data,
            "metadata": meta_response.json() if meta_response.status_code == 200 else None,
            "custom_fields": custom_fields_response.json() if custom_fields_response.status_code == 200 else None,
            "versions": version_response.json() if version_response.status_code == 200 else None
        }
        
    except Exception as e:
        print(f"Error in debug payment: {str(e)}")
        return {"error": str(e)}

@router.get("/debug/user/{user_id}")
async def debug_user(
    user_id: str,
    erp_client: ERPNextClient = Depends(get_erp_client)
):
    """Debug endpoint to check user data"""
    try:
        # Get user document
        response = erp_client.session.get(
            f"{erp_client.base_url}/api/resource/User/{user_id}"
        )
        
        if response.status_code != 200:
            return {"error": "Failed to fetch user"}

        user_data = response.json()
        
        # Get user's roles
        roles_response = erp_client.session.get(
            f"{erp_client.base_url}/api/resource/Has Role",
            params={
                'filters': json.dumps([["parent", "=", user_id]]),
                'fields': '["*"]'
            }
        )
        
        # Get user's login history
        login_response = erp_client.session.get(
            f"{erp_client.base_url}/api/method/frappe.core.doctype.user.user.get_user_info",
            params={"user": user_id}
        )

        return {
            "user": user_data,
            "roles": roles_response.json() if roles_response.status_code == 200 else None,
            "login_info": login_response.json() if login_response.status_code == 200 else None
        }
        
    except Exception as e:
        print(f"Error in debug user: {str(e)}")
        return {"error": str(e)}