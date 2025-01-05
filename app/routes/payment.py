from fastapi import APIRouter, Request, HTTPException, Depends, Body
from fastapi.templating import Jinja2Templates
from ..utils.erp_client import ERPNextClient, get_erp_client
from pydantic import BaseModel, ValidationError
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json
import uuid
from ..services.payment_service import PaymentService  # Add this import

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
        payment_service = PaymentService(erp_client)
        
        result = await payment_service.process_initial_scan(rfid_input.rfid)
        
        if not result:
            print("No customer found")
            raise HTTPException(status_code=404, detail="Customer not found")

        session_id = result.get("session_id")
        
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
        print(f"\nProcessing payment session: {session_id}")
        payment_service = PaymentService(erp_client)
        session = payment_service.get_session(session_id)
        
        if not session:
            print("No valid session found")
            return templates.TemplateResponse(
                "payment/scan_customer.html",
                {
                    "request": request, 
                    "error": "Session expired, please scan card again"
                }
            )
        
        print(f"Session data: {session}")
        customer_type = session.get('customer_type', 'individual')
        print(f"Customer type: {customer_type}")
        
        # Get invoices from session
        invoices = []
        if isinstance(session.get('invoices'), list):
            invoices = session['invoices']
        print(f"Number of invoices: {len(invoices)}")

        template_data = {
            "request": request,
            "customer": session.get('payer', {}),
            "invoices": invoices,
            "family_group": session.get('family_group'),
            "session_id": session_id,
            "customer_type": customer_type
        }

        print(f"Rendering template with data: {template_data}")
        return templates.TemplateResponse(
            "payment/invoice_selection.html",
            template_data
        )
        
    except Exception as e:
        print(f"Payment process error: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return templates.TemplateResponse(
            "payment/scan_customer.html",
            {
                "request": request, 
                "error": f"Error processing payment: {str(e)}"
            }
        )

@router.post("/authorize-staff")
async def authorize_staff(
    auth_request: StaffAuthRequest, 
    erp_client: ERPNextClient = Depends(get_erp_client)
):
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
async def process_payment_submission(
    payment_request: PaymentRequest, 
    erp_client: ERPNextClient = Depends(get_erp_client)
):
    try:
        payment_service = PaymentService(erp_client)
        # Process payment using the service
        return await payment_service.process_payment(payment_request)

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