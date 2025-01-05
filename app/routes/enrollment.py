from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.templating import Jinja2Templates
from ..models.enrollment import EnrollmentRequest, EnrollmentResponse, Program, ProgramPricing
from ..services.enrollment_service import EnrollmentService
from ..utils.erp_client import ERPNextClient, get_erp_client

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

# Define available programs
PROGRAMS = [
    Program(
        id="bjj",
        name="Brazilian Jiu-Jitsu",
        description="Traditional BJJ program with Gi",
        pricing=ProgramPricing(
            daily=50.0,
            monthly=400.0,
            six_months=2000.0,
            yearly=3600.0
        )
    ),
    Program(
        id="nogi",
        name="No-Gi Jiu-Jitsu",
        description="No-Gi grappling program",
        pricing=ProgramPricing(
            daily=50.0,
            monthly=400.0,
            six_months=2000.0,
            yearly=3600.0
        )
    )
]

@router.get("/")
async def enrollment_page(request: Request):
    """Render the enrollment form page."""
    return templates.TemplateResponse(
        "enrollment.html",
        {
            "request": request,
            "programs": PROGRAMS
        }
    )

@router.post("/enroll")
async def create_enrollment(
    enrollment: EnrollmentRequest,
    erp_client: ERPNextClient = Depends(get_erp_client)
):
    """Create a new student enrollment."""
    try:
        service = EnrollmentService(erp_client)
        result = await service.create_enrollment(enrollment)
        return EnrollmentResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))