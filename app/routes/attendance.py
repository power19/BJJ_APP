from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.templating import Jinja2Templates
from ..services.attendance_service import AttendanceService
from ..utils.erp_client import ERPNextClient, get_erp_client
from pydantic import BaseModel
from datetime import datetime
import json

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

class RFIDInput(BaseModel):
    rfid: str

@router.get("")  # Root endpoint for /api/v1/attendance
async def attendance_scanner(request: Request):
    """Main attendance scanner page"""
    return templates.TemplateResponse(
        "attendance.html",
        {
            "request": request,
            "attendance_info": None
        }
    )

@router.get("/customer/{customer_name}")
async def get_customer_attendance(
    request: Request,
    customer_name: str,
    week_offset: int = 0,
    erp_client: ERPNextClient = Depends(get_erp_client)
):
    try:
        print(f"Getting attendance for customer: {customer_name}")
        attendance_service = AttendanceService(erp_client)
        attendance_info = await attendance_service.get_customer_attendance(
            customer_name, 
            week_offset
        )
        
        print(f"Attendance info: {json.dumps(attendance_info, indent=2)}")
        
        return templates.TemplateResponse(
            "attendance.html",
            {
                "request": request,
                "attendance_info": attendance_info,
                "week_offset": week_offset,
                "debug": True  # Enable debug output in template
            }
        )
    except Exception as e:
        print(f"Error in attendance route: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/scan")
async def process_attendance_scan(
    rfid_input: RFIDInput,
    erp_client: ERPNextClient = Depends(get_erp_client)
):
    try:
        print(f"Processing attendance scan for RFID: {rfid_input.rfid}")
        # Search for customer
        customer = erp_client.search_customer(rfid_input.rfid)
        
        if not customer or not customer.get("customer"):
            raise HTTPException(status_code=404, detail="Customer not found")
            
        customer_data = customer["customer"]
        customer_name = customer_data["customer_name"]
        
        # Get current attendance list
        current_attendance = customer_data.get("custom_attendance", "[]")
        try:
            attendance_list = json.loads(current_attendance)
            if not isinstance(attendance_list, list):
                attendance_list = []
        except:
            attendance_list = []
            
        # Add current timestamp
        current_time = datetime.now().isoformat()
        attendance_list.append(current_time)
        
        # Update customer's attendance
        endpoint = f"{erp_client.base_url}/api/resource/Customer/{customer_data['name']}"
        response = erp_client.session.put(
            endpoint,
            json={
                "custom_attendance": json.dumps(attendance_list)
            }
        )
        
        if response.status_code not in (200, 201):
            raise HTTPException(status_code=500, detail="Failed to update attendance")
            
        return {
            "status": "success",
            "customer_name": customer_name,
            "attendance_time": current_time,
            "redirect_url": f"/api/v1/attendance/customer/{customer_name}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error processing attendance scan: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))