from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.templating import Jinja2Templates
from ..services.attendance_service import AttendanceService
from ..utils.erp_client import ERPNextClient, get_erp_client
import json

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

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