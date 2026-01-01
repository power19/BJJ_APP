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


# ============================================================
# NEW RFID-BASED PAYMENT SYSTEM (Gym Members)
# ============================================================

from ..utils.config import get_config
import requests as http_requests
from fastapi.responses import JSONResponse

def get_erpnext_connection():
    """Get ERPNext connection for new payment system."""
    config = get_config()
    if not config.is_configured():
        return None, None, False

    erp_config = config.get_erpnext_config()
    url = erp_config.get('url', '')
    headers = {
        'Authorization': f"token {erp_config.get('api_key', '')}:{erp_config.get('api_secret', '')}",
        'Content-Type': 'application/json'
    }
    return url, headers, True


@router.get("/rfid")
async def rfid_payment_page(request: Request):
    """RFID-based payment processing page."""
    config = get_config()
    return templates.TemplateResponse("payment/rfid_payment.html", {
        "request": request,
        "is_connected": config.is_configured()
    })


@router.get("/rfid/member/{rfid_tag}")
async def lookup_member_for_payment(rfid_tag: str):
    """Look up member by RFID for payment processing."""
    url, headers, connected = get_erpnext_connection()

    if not connected:
        return JSONResponse({"success": False, "error": "ERPNext not connected"}, status_code=503)

    try:
        # Get member details
        response = http_requests.get(
            f"{url}/api/resource/Gym Member",
            headers=headers,
            params={
                "filters": f'[["rfid_tag", "=", "{rfid_tag}"]]',
                "fields": '["name", "first_name", "last_name", "full_name", "photo", "status", "payment_status", "current_membership_type", "membership_end_date", "remaining_sessions"]'
            },
            timeout=10
        )

        if response.status_code != 200:
            return JSONResponse({"success": False, "error": "Failed to query ERPNext"}, status_code=500)

        members = response.json().get("data", [])
        if not members:
            return JSONResponse({"success": False, "error": "Member not found"}, status_code=404)

        member = members[0]
        member_id = member.get("name")

        # Get membership type details if available
        membership_info = None
        if member.get("current_membership_type"):
            mem_response = http_requests.get(
                f"{url}/api/resource/Membership Type/{member['current_membership_type']}",
                headers=headers,
                timeout=10
            )
            if mem_response.status_code == 200:
                mem_data = mem_response.json().get("data", {})
                membership_info = {
                    "name": mem_data.get("membership_name"),
                    "price": mem_data.get("price"),
                    "category": mem_data.get("membership_category")
                }

        # Get pending payments for this member
        payments_response = http_requests.get(
            f"{url}/api/resource/Gym Payment",
            headers=headers,
            params={
                "filters": f'[["member", "=", "{member_id}"], ["status", "=", "Pending"]]',
                "fields": '["name", "payment_date", "payment_type", "amount", "status"]',
                "order_by": "payment_date desc"
            },
            timeout=10
        )

        pending_payments = []
        if payments_response.status_code == 200:
            pending_payments = payments_response.json().get("data", [])

        # Get available membership types for new payment
        types_response = http_requests.get(
            f"{url}/api/resource/Membership Type",
            headers=headers,
            params={
                "filters": '[["is_active", "=", 1]]',
                "fields": '["membership_name", "price", "membership_category", "description"]'
            },
            timeout=10
        )

        membership_types = []
        if types_response.status_code == 200:
            membership_types = types_response.json().get("data", [])

        return JSONResponse({
            "success": True,
            "member": {
                "id": member_id,
                "first_name": member.get("first_name"),
                "last_name": member.get("last_name"),
                "full_name": member.get("full_name") or f"{member.get('first_name', '')} {member.get('last_name', '')}".strip(),
                "photo": member.get("photo"),
                "status": member.get("status"),
                "payment_status": member.get("payment_status"),
                "membership": membership_info,
                "membership_end_date": member.get("membership_end_date"),
                "remaining_sessions": member.get("remaining_sessions", 0)
            },
            "pending_payments": pending_payments,
            "membership_types": membership_types
        })

    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@router.get("/rfid/staff/{rfid_tag}")
async def verify_staff_for_payment(rfid_tag: str):
    """Verify staff RFID for payment authorization."""
    url, headers, connected = get_erpnext_connection()

    if not connected:
        return JSONResponse({"success": False, "error": "ERPNext not connected"}, status_code=503)

    try:
        response = http_requests.get(
            f"{url}/api/resource/Gym Staff",
            headers=headers,
            params={
                "filters": f'[["rfid_tag", "=", "{rfid_tag}"], ["is_active", "=", 1]]',
                "fields": '["name", "staff_name", "role", "can_process_payments", "photo"]'
            },
            timeout=10
        )

        if response.status_code != 200:
            return JSONResponse({"success": False, "error": "Failed to query ERPNext"}, status_code=500)

        staff_list = response.json().get("data", [])
        if not staff_list:
            return JSONResponse({"success": False, "error": "Staff not found or inactive"}, status_code=404)

        staff = staff_list[0]

        if not staff.get("can_process_payments"):
            return JSONResponse({
                "success": False,
                "error": "Staff not authorized for payments",
                "staff_name": staff.get("staff_name")
            }, status_code=403)

        return JSONResponse({
            "success": True,
            "staff": {
                "id": staff.get("name"),
                "name": staff.get("staff_name"),
                "role": staff.get("role"),
                "photo": staff.get("photo")
            }
        })

    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@router.post("/rfid/process")
async def process_rfid_payment(request: Request):
    """Process a payment with RFID verification."""
    url, headers, connected = get_erpnext_connection()

    if not connected:
        return JSONResponse({"success": False, "error": "ERPNext not connected"}, status_code=503)

    try:
        body = await request.json()
        member_id = body.get("member_id")
        staff_id = body.get("staff_id")
        payment_type = body.get("payment_type")
        amount = body.get("amount")
        payment_method = body.get("payment_method", "Cash")
        notes = body.get("notes", "")
        membership_type = body.get("membership_type")  # For new membership payments

        if not all([member_id, staff_id, payment_type, amount]):
            return JSONResponse({
                "success": False,
                "error": "Missing required fields: member_id, staff_id, payment_type, amount"
            }, status_code=400)

        # Create the payment record
        from datetime import date as date_module
        payment_data = {
            "doctype": "Gym Payment",
            "member": member_id,
            "payment_date": date_module.today().isoformat(),
            "payment_type": payment_type,
            "amount": float(amount),
            "payment_method": payment_method,
            "processed_by": staff_id,
            "processor_rfid_verified": 1,
            "status": "Completed",
            "notes": notes
        }

        create_response = http_requests.post(
            f"{url}/api/resource/Gym Payment",
            headers=headers,
            json=payment_data,
            timeout=10
        )

        if create_response.status_code not in [200, 201]:
            error_text = create_response.text[:200]
            return JSONResponse({
                "success": False,
                "error": f"Failed to create payment: {error_text}"
            }, status_code=500)

        payment_result = create_response.json().get("data", {})
        payment_id = payment_result.get("name")

        # Update member's payment status
        member_update = {"payment_status": "Current"}

        # If it's a membership payment, update membership details
        if membership_type and payment_type in ["Monthly Subscription", "Registration"]:
            from datetime import timedelta
            today = date_module.today()

            # Get membership type details
            type_response = http_requests.get(
                f"{url}/api/resource/Membership Type/{membership_type}",
                headers=headers,
                timeout=10
            )

            if type_response.status_code == 200:
                type_data = type_response.json().get("data", {})
                duration_months = type_data.get("duration_months", 1)
                sessions = type_data.get("sessions_included", 0)

                if duration_months > 0:
                    # Calculate end date
                    end_date = today + timedelta(days=duration_months * 30)
                    member_update.update({
                        "current_membership_type": membership_type,
                        "membership_start_date": today.isoformat(),
                        "membership_end_date": end_date.isoformat()
                    })

                if sessions > 0:
                    member_update["remaining_sessions"] = sessions

        # Update member record
        http_requests.put(
            f"{url}/api/resource/Gym Member/{member_id}",
            headers=headers,
            json=member_update,
            timeout=10
        )

        # Get member name for response
        member_response = http_requests.get(
            f"{url}/api/resource/Gym Member/{member_id}",
            headers=headers,
            params={"fields": '["full_name", "first_name", "last_name"]'},
            timeout=10
        )

        member_name = "Member"
        if member_response.status_code == 200:
            m_data = member_response.json().get("data", {})
            member_name = m_data.get("full_name") or f"{m_data.get('first_name', '')} {m_data.get('last_name', '')}".strip()

        return JSONResponse({
            "success": True,
            "payment_id": payment_id,
            "member_name": member_name,
            "amount": amount,
            "payment_type": payment_type,
            "message": "Payment processed successfully"
        })

    except Exception as e:
        import traceback
        print(f"Payment error: {traceback.format_exc()}")
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)