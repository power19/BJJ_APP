from fastapi import APIRouter, Request, HTTPException, Depends , Body
from fastapi.templating import Jinja2Templates
from ..utils.erp_client import ERPNextClient, get_erp_client
from pydantic import BaseModel, ValidationError
from datetime import datetime ,timedelta
import json
import uuid
from typing import Dict, List, Optional

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

# Models
class RFIDInput(BaseModel):
    rfid: str

class PaymentRequest(BaseModel):
    invoices: List[str]
    invoice_amounts: Dict[str, float]
    total_amount: float
    customer_name: str

class StaffAuthRequest(BaseModel):
    staff_rfid: str
    invoices: List[str]

# Session storage
active_sessions: Dict[str, dict] = {}

@router.get("/")
async def payment_home(request: Request):
    return templates.TemplateResponse(
        "payment/scan_customer.html",
        {"request": request}
    )

@router.post("/scan")
async def process_scan(rfid_input: RFIDInput, erp_client: ERPNextClient = Depends(get_erp_client)):
    try:
        if not rfid_input.rfid:
            raise HTTPException(status_code=400, detail="RFID input required")
            
        print(f"Searching for customer with RFID: {rfid_input.rfid}")
        customer_data = erp_client.search_customer(rfid_input.rfid)
        
        if not customer_data:
            print("No customer found")
            raise HTTPException(status_code=404, detail="Customer not found")
        
        if not customer_data.get("customer"):
            print("Invalid customer data structure")
            raise HTTPException(status_code=404, detail="Invalid customer data")

        session_id = str(uuid.uuid4())
        active_sessions[session_id] = {
            "customer": customer_data,
            "timestamp": datetime.now()
        }
        
        print(f"Created session {session_id} for customer")
        return {
            "status": "success",
            "session_id": session_id,
            "redirect_url": f"/api/v1/payment/process/{session_id}"
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"Detailed scan error: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="Error processing customer scan")

@router.get("/process/{session_id}")
async def process_payment(request: Request, session_id: str, erp_client: ERPNextClient = Depends(get_erp_client)):
    try:
        if session_id not in active_sessions:
            return templates.TemplateResponse(
                "payment/scan_customer.html",
                {"request": request, "error": "Session expired"}
            )

        session = active_sessions[session_id]
        customer = session["customer"]["customer"]
        transactions = erp_client.get_customer_transactions(customer["customer_name"])

        return templates.TemplateResponse(
            "payment/invoice_selection.html",
            {
                "request": request,
                "customer": session["customer"],
                "transactions": transactions.get("data", []),
                "session_id": session_id
            }
        )

    except Exception as e:
        print(f"Payment process error: {str(e)}")
        return templates.TemplateResponse(
            "payment/scan_customer.html",
            {"request": request, "error": str(e)}
        )

# payment.py routes

@router.post("/authorize-staff")
async def authorize_staff(auth_request: StaffAuthRequest, erp_client: ERPNextClient = Depends(get_erp_client)):
    try:
        print(f"Authorizing staff with RFID: {auth_request.staff_rfid}")
        
        if not auth_request.staff_rfid:
            raise HTTPException(status_code=400, detail="Staff RFID required")

        staff_result = erp_client.verify_staff_rfid(auth_request.staff_rfid)
        print(f"Staff verification result: {staff_result}")
        
        if not staff_result.get("verified"):
            raise HTTPException(
                status_code=401, 
                detail=staff_result.get("error", "Staff not authorized")
            )

        return {
            "status": "success", 
            "authorized": True,
            "staff_name": staff_result.get("name"),
            "roles": staff_result.get("roles", [])
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"Staff authorization error: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="Authorization failed")

@router.post("/process-payment")
async def process_payment_submission(payment_request: PaymentRequest, erp_client: ERPNextClient = Depends(get_erp_client)):
    try:
        print("\n=== Payment Processing Debug ===")
        print(f"Payment Request Data: {payment_request.dict()}")

        # First, get customer's family group info
        family_group = erp_client.get_family_group(payment_request.customer_name)
        print(f"\nFamily Group Info:")
        print(json.dumps(family_group, indent=2))

        # Get the primary payer
        primary_payer = None
        if family_group:
            primary_payer = family_group.get("primary_payer")
            print(f"Primary payer: {primary_payer}")

        # For each invoice, verify ownership
        invoice_refs = []
        total_allocated = 0
        
        for invoice_id in payment_request.invoices:
            # Get invoice details
            response = erp_client.session.get(
                f"{erp_client.base_url}/api/resource/Sales Invoice/{invoice_id}",
                params={'fields': '["name", "customer", "grand_total", "outstanding_amount"]'}
            )
            
            if response.status_code != 200:
                raise HTTPException(status_code=404, detail=f"Invoice {invoice_id} not found")
                
            invoice_data = response.json().get('data', {})
            invoice_customer = invoice_data.get('customer')
            
            print(f"\nInvoice {invoice_id}:")
            print(f"Invoice customer: {invoice_customer}")
            print(f"Payment customer: {payment_request.customer_name}")
            print(f"Primary payer: {primary_payer}")
            
            # Check if customer is authorized to pay this invoice
            if invoice_customer != payment_request.customer_name and invoice_customer != primary_payer:
                if not (primary_payer and invoice_customer == primary_payer):
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invoice {invoice_id} cannot be paid by {payment_request.customer_name}"
                    )

            # Use invoice customer (primary payer) for payment
            amount = payment_request.invoice_amounts[invoice_id]
            total_allocated += amount
            
            invoice_refs.append({
                "reference_doctype": "Sales Invoice",
                "reference_name": invoice_id,
                "total_amount": float(invoice_data.get('grand_total', 0)),
                "outstanding_amount": float(invoice_data.get('outstanding_amount', 0)),
                "allocated_amount": amount
            })

        # Create payment entry using primary payer
        payment_data = {
            "doctype": "Payment Entry",
            "naming_series": "ACC-PAY-.YYYY.-",
            "payment_type": "Receive",
            "posting_date": datetime.now().strftime('%Y-%m-%d'),
            "company": "INVICTUS BJJ",
            "mode_of_payment": "Cash",
            "party_type": "Customer",
            "party": primary_payer or payment_request.customer_name,  # Use primary payer if available
            "party_name": primary_payer or payment_request.customer_name,
            "paid_from": "Debtors - IB",
            "paid_from_account_type": "Receivable",
            "paid_from_account_currency": "SRD",
            "paid_to": "Cash - IB",
            "paid_to_account_type": "Cash",
            "paid_to_account_currency": "SRD",
            "paid_amount": payment_request.total_amount,
            "source_exchange_rate": 1,
            "base_paid_amount": payment_request.total_amount,
            "received_amount": payment_request.total_amount,
            "target_exchange_rate": 1,
            "base_received_amount": payment_request.total_amount,
            "reference_no": f"PMT-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}",
            "reference_date": datetime.now().strftime('%Y-%m-%d'),
            "references": invoice_refs,
            "total_allocated_amount": total_allocated,
            "unallocated_amount": 0,
            "remarks": f"Amount SRD {payment_request.total_amount} received for family member {payment_request.customer_name}"
        }

        print("\nPayment Entry Data:")
        print(json.dumps(payment_data, indent=2))

        # Create payment entry
        response = erp_client.session.post(
            f"{erp_client.base_url}/api/method/frappe.client.insert",
            json={"doc": payment_data}
        )

        print("\nPayment creation response:")
        print(f"Status: {response.status_code}")
        print(f"Content: {response.text}")

        if response.status_code not in (200, 201):
            error_detail = "Failed to create payment entry"
            try:
                error_json = response.json()
                if error_json.get("exc"):
                    error_detail = error_json["exc"].split("\n")[-2]
            except:
                pass
            raise HTTPException(status_code=500, detail=error_detail)

        payment_entry = response.json()
        payment_name = payment_entry.get("message", {}).get("name")

        if not payment_name:
            raise HTTPException(status_code=500, detail="Failed to get payment entry name")

        print(f"\nSubmitting payment entry: {payment_name}")

        # Get the full document first
        doc_response = erp_client.session.get(
            f"{erp_client.base_url}/api/resource/Payment Entry/{payment_name}"
        )
        
        if doc_response.status_code != 200:
            raise HTTPException(status_code=500, detail="Failed to get payment document")
            
        doc_data = doc_response.json().get("data", {})

        # Submit the payment using the client submit method
        submit_response = erp_client.session.post(
            f"{erp_client.base_url}/api/method/frappe.client.submit",
            json={
                "doc": doc_data  # Pass the full document
            }
        )

        print("\nSubmit response:")
        print(f"Status: {submit_response.status_code}")
        print(f"Content: {submit_response.text}")

        if submit_response.status_code not in (200, 201):
            error_detail = "Failed to submit payment entry"
            try:
                error_json = submit_response.json()
                if error_json.get("exc"):
                    error_detail = error_json["exc"].split("\n")[-2]
            except:
                pass
            
            # Try to clean up the draft payment
            try:
                cancel_response = erp_client.session.delete(
                    f"{erp_client.base_url}/api/resource/Payment Entry/{payment_name}"
                )
                print("\nCancellation response:")
                print(f"Status: {cancel_response.status_code}")
                print(f"Content: {cancel_response.text}")
            except:
                print("Failed to cancel draft payment entry")
                
            raise HTTPException(status_code=500, detail=error_detail)

        # Verify submission
        verify_response = erp_client.session.get(
            f"{erp_client.base_url}/api/resource/Payment Entry/{payment_name}"
        )
        
        if verify_response.status_code == 200:
            verified_data = verify_response.json().get("data", {})
            print(f"\nVerification data: {json.dumps(verified_data, indent=2)}")
            
            if verified_data.get("docstatus") != 1:
                raise HTTPException(status_code=500, detail="Payment entry was not properly submitted")

        return {
            "status": "success",
            "payment_id": payment_name,
            "amount": payment_request.total_amount,
            "currency": "SRD"
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"Payment processing error: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))
        
@router.get("/success/{payment_id}")
async def payment_success(
    request: Request, 
    payment_id: str,
    erp_client: ERPNextClient = Depends(get_erp_client)
):
    try:
        # Verify payment status
        response = erp_client.session.get(
            f"{erp_client.base_url}/api/resource/Payment Entry/{payment_id}"
        )
        
        if response.status_code != 200:
            return templates.TemplateResponse(
                "payment/error.html",
                {
                    "request": request,
                    "error": "Payment not found"
                }
            )
            
        payment_data = response.json().get("data", {})
        
        if payment_data.get("docstatus") != 1:
            return templates.TemplateResponse(
                "payment/error.html",
                {
                    "request": request,
                    "error": "Payment is not submitted"
                }
            )
        
        return templates.TemplateResponse(
            "payment/success.html",
            {
                "request": request,
                "payment_id": payment_id,
                "amount": payment_data.get("paid_amount"),
                "currency": payment_data.get("paid_from_account_currency"),
                "customer": payment_data.get("party_name"),
                "date": payment_data.get("posting_date")
            }
        )
    except Exception as e:
        print(f"Error displaying success page: {str(e)}")
        return templates.TemplateResponse(
            "payment/error.html",
            {
                "request": request,
                "error": "Failed to load payment details"
            }
        )

# app/routes/payment.py 
# Add these new routes

@router.get("/history")
async def payment_history(
    request: Request,
    days: int = 7,  # Default to last 7 days
    erp_client: ERPNextClient = Depends(get_erp_client)
):
    try:
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Get payment entries
        response = erp_client.session.get(
            f"{erp_client.base_url}/api/resource/Payment Entry",
            params={
                'fields': json.dumps([
                    "name", "posting_date", "party", "paid_amount", 
                    "reference_no", "remarks", "owner", "modified_by",
                    "creation", "modified"
                ]),
                'filters': json.dumps([
                    ["docstatus", "=", 1],  # Submitted payments
                    ["posting_date", "between", [
                        start_date.strftime('%Y-%m-%d'),
                        end_date.strftime('%Y-%m-%d')
                    ]],
                    ["payment_type", "=", "Receive"]
                ]),
                'order_by': 'creation desc'
            }
        )

        if response.status_code != 200:
            raise HTTPException(status_code=500, detail="Failed to fetch payment history")

        payments = response.json().get("data", [])

        # Get staff details for each payment
        for payment in payments:
            # Get user details
            user_response = erp_client.session.get(
                f"{erp_client.base_url}/api/resource/User/{payment['modified_by']}"
            )
            if user_response.status_code == 200:
                user_data = user_response.json().get("data", {})
                payment["staff_name"] = user_data.get("full_name")
                
            # Get referenced invoices
            payment_doc_response = erp_client.session.get(
                f"{erp_client.base_url}/api/resource/Payment Entry/{payment['name']}"
            )
            if payment_doc_response.status_code == 200:
                payment_doc = payment_doc_response.json().get("data", {})
                payment["references"] = payment_doc.get("references", [])

        return templates.TemplateResponse(
            "payment/history.html",
            {
                "request": request,
                "payments": payments,
                "start_date": start_date.strftime('%Y-%m-%d'),
                "end_date": end_date.strftime('%Y-%m-%d'),
                "days": days
            }
        )

    except Exception as e:
        print(f"Error fetching payment history: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history/details/{payment_id}")
async def payment_details(
    request: Request,
    payment_id: str,
    erp_client: ERPNextClient = Depends(get_erp_client)
):
    try:
        # Get payment details
        response = erp_client.session.get(
            f"{erp_client.base_url}/api/resource/Payment Entry/{payment_id}"
        )
        
        if response.status_code != 200:
            raise HTTPException(status_code=404, detail="Payment not found")

        payment = response.json().get("data", {})

        # Get staff details
        user_response = erp_client.session.get(
            f"{erp_client.base_url}/api/resource/User/{payment['modified_by']}"
        )
        if user_response.status_code == 200:
            user_data = user_response.json().get("data", {})
            payment["staff_name"] = user_data.get("full_name")

        # Get invoice details for each reference
        for ref in payment.get("references", []):
            invoice_response = erp_client.session.get(
                f"{erp_client.base_url}/api/resource/Sales Invoice/{ref['reference_name']}"
            )
            if invoice_response.status_code == 200:
                ref["invoice_details"] = invoice_response.json().get("data", {})

        return templates.TemplateResponse(
            "payment/details.html",
            {
                "request": request,
                "payment": payment
            }
        )

    except Exception as e:
        print(f"Error fetching payment details: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))