# app/routes/handover.py
from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.templating import Jinja2Templates
from typing import Dict, Any, Optional
from pydantic import BaseModel

from ..services.handover_service import HandoverService
from ..models.payment import PaymentHandoverRequest
from ..utils.erp_client import ERPNextClient, get_erp_client

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

class RFIDInput(BaseModel):
    rfid: str
    payment_id: str
    notes: Optional[str] = None

@router.get("/dashboard")
async def handover_dashboard(
    request: Request,
    erp_client: ERPNextClient = Depends(get_erp_client)
):
    """Dashboard showing payments awaiting handover from coaches to treasurers"""
    try:
        handover_service = HandoverService(erp_client)
        pending_handovers = await handover_service.get_pending_handovers()
        
        return templates.TemplateResponse(
            "payment/handover_dashboard.html",
            {
                "request": request,
                "pending_handovers": pending_handovers
            }
        )
    except Exception as e:
        print(f"Error in handover dashboard: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/process/{payment_id}")
async def handover_confirmation(
    request: Request,
    payment_id: str,
    erp_client: ERPNextClient = Depends(get_erp_client)
):
    """Screen for treasurer to confirm receipt of payment"""
    try:
        # Get payment details
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
        
        # Get staff details
        staff_user_id = payment_data.get('authorized_by_staff', payment_data.get('owner'))
        staff_name = "Unknown"
        
        if staff_user_id:
            user_response = erp_client.session.get(
                f"{erp_client.base_url}/api/resource/User/{staff_user_id}"
            )
            if user_response.status_code == 200:
                user_data = user_response.json().get('data', {})
                staff_name = user_data.get('full_name')
        
        # Get invoice references
        invoice_details = []
        for ref in payment_data.get('references', []):
            if ref.get('reference_doctype') == 'Sales Invoice':
                invoice_id = ref.get('reference_name')
                invoice_response = erp_client.session.get(
                    f"{erp_client.base_url}/api/resource/Sales Invoice/{invoice_id}"
                )
                if invoice_response.status_code == 200:
                    invoice_data = invoice_response.json().get('data', {})
                    invoice_details.append({
                        "invoice_id": invoice_id,
                        "amount": ref.get('allocated_amount'),
                        "invoice_date": invoice_data.get("posting_date"),
                        "due_date": invoice_data.get("due_date"),
                        "items": invoice_data.get("items", [])
                    })
                    
        return templates.TemplateResponse(
            "payment/handover_confirmation.html",
            {
                "request": request,
                "payment": payment_data,
                "staff_name": staff_name,
                "invoice_details": invoice_details,
                "payment_id": payment_id
            }
        )
    except Exception as e:
        print(f"Error in handover confirmation: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return templates.TemplateResponse(
            "payment/error.html",
            {
                "request": request,
                "error": f"Error loading payment details: {str(e)}"
            }
        )

@router.post("/confirm")
async def process_handover(
    rfid_input: RFIDInput,
    erp_client: ERPNextClient = Depends(get_erp_client)
):
    """Process handover from coach to treasurer"""
    try:
        if not rfid_input.rfid:
            raise HTTPException(status_code=400, detail="Treasurer RFID required")
            
        if not rfid_input.payment_id:
            raise HTTPException(status_code=400, detail="Payment ID required")
            
        # Create handover request
        handover_request = PaymentHandoverRequest(
            payment_id=rfid_input.payment_id,
            treasurer_rfid=rfid_input.rfid,
            handover_notes=rfid_input.notes
        )
        
        # Process handover
        handover_service = HandoverService(erp_client)
        result = await handover_service.process_handover(handover_request)
        
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("message"))
            
        return {
            "success": True,
            "payment_id": rfid_input.payment_id,
            "message": result.get("message"),
            "redirect_url": "/api/v1/payment/handover/success"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error processing handover: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Error processing handover: {str(e)}")

@router.get("/success")
async def handover_success(request: Request):
    """Success page after successful handover"""
    return templates.TemplateResponse(
        "payment/handover_success.html",
        {"request": request}
    )

@router.get("/history")
async def payment_history(
    request: Request,
    days: int = 30,
    erp_client: ERPNextClient = Depends(get_erp_client)
):
    """View payment history with handover status"""
    try:
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