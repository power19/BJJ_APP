from fastapi import APIRouter, Request, HTTPException, Depends, Body
from fastapi.templating import Jinja2Templates
from ..utils.erp_client import ERPNextClient, get_erp_client
from pydantic import BaseModel, ValidationError
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json
import uuid
from ..services.payment_service import PaymentService
from ..services.handover_service import HandoverService

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
    staff_rfid: str  # Required for staff authorization

class StaffAuthRequest(BaseModel):
    staff_rfid: str
    staff_name: Optional[str] = None

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
            "invoices": session.get('invoices', []),
            "family_group": session.get('family_group'),
            "session_id": session_id,
            "customer_type": session.get('customer_type', 'individual')
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

        # Store the authorized staff info in the session
        return {
            "status": "success", 
            "authorized": True,
            "staff_name": staff_result.get("name"),
            "staff_rfid": auth_request.staff_rfid,  # Include RFID in response
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
        print(f"\nProcessing payment request: {payment_request}")
        
        # Verify staff authorization first
        staff_auth = erp_client.verify_staff_rfid(payment_request.staff_rfid)
        if not staff_auth.get("verified"):
            raise HTTPException(
                status_code=401,
                detail="Staff authorization required before processing payment"
            )
            
        payment_service = PaymentService(erp_client)
        result = await payment_service.process_payment(payment_request)
        return result

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
                "date": payment_data.get("posting_date"),
                "authorized_by": payment_data.get("authorized_by_staff"),
                "authorization_time": payment_data.get("authorization_time"),
                "staff_notes": payment_data.get("staff_notes")
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
@router.get("/history")
async def payment_history(
    request: Request,
    days: int = 30,
    erp_client: ERPNextClient = Depends(get_erp_client)
):
    """View payment history with handover status"""
    try:
        # Use the handover service to get comprehensive payment history
        from ..services.handover_service import HandoverService
        handover_service = HandoverService(erp_client)
        payment_history = await handover_service.get_payment_history(days)
        
        # Calculate date ranges for the view
        from datetime import datetime, timedelta
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        end_date = datetime.now().strftime('%Y-%m-%d')
        
        return templates.TemplateResponse(
            "payment/history.html",
            {
                "request": request,
                "payments": payment_history,
                "days": days,
                "start_date": start_date,
                "end_date": end_date
            }
        )
    except Exception as e:
        print(f"Error in payment history: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/details/{payment_id}")
async def payment_details(
    request: Request,
    payment_id: str,
    erp_client: ERPNextClient = Depends(get_erp_client)
):
    """View detailed payment information"""
    try:
        # Get payment details
        response = erp_client.session.get(
            f"{erp_client.base_url}/api/resource/Payment Entry/{payment_id}"
        )
        
        if response.status_code != 200:
            print(f"Error getting payment: {response.text}")
            return templates.TemplateResponse(
                "payment/error.html",
                {
                    "request": request,
                    "error": "Payment not found"
                }
            )
            
        payment_data = response.json().get("data", {})
        
        # Get staff details
        staff_name = payment_data.get("authorized_by_staff")
        if not staff_name:
            staff_user = payment_data.get("owner")
            if staff_user:
                user_response = erp_client.session.get(
                    f"{erp_client.base_url}/api/resource/User/{staff_user}"
                )
                if user_response.status_code == 200:
                    user_data = user_response.json().get("data", {})
                    staff_name = user_data.get("full_name")
        
        # Get invoice details
        invoice_details = []
        for ref in payment_data.get("references", []):
            if ref.get("reference_doctype") == "Sales Invoice":
                invoice_id = ref.get("reference_name")
                invoice_response = erp_client.session.get(
                    f"{erp_client.base_url}/api/resource/Sales Invoice/{invoice_id}"
                )
                if invoice_response.status_code == 200:
                    invoice_data = invoice_response.json().get("data", {})
                    invoice_details.append({
                        "invoice_id": invoice_id,
                        "amount": ref.get("allocated_amount"),
                        "invoice_date": invoice_data.get("posting_date"),
                        "due_date": invoice_data.get("due_date"),
                        "items": invoice_data.get("items", [])
                    })
        
        return templates.TemplateResponse(
            "payment/details.html",
            {
                "request": request,
                "payment": payment_data,
                "staff_name": staff_name,
                "invoice_details": invoice_details,
                "auth_time": payment_data.get("authorization_time"),
                "staff_notes": payment_data.get("staff_notes")
            }
        )

    except Exception as e:
        print(f"Error displaying payment details: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return templates.TemplateResponse(
            "payment/error.html",
            {
                "request": request,
                "error": "Failed to load payment details"
            }
        )