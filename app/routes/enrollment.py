# app/routes/enrollment.py
"""Member enrollment routes for the gym management system."""
from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime
import requests

from ..utils.config import get_config


router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


def get_erpnext_client():
    """Get ERPNext connection details."""
    config = get_config()
    if not config.is_configured():
        return None, None, False

    erp_config = config.get_erpnext_config()
    url = erp_config.get('url', '')
    headers = {
        'Authorization': f"token {erp_config.get('api_key')}:{erp_config.get('api_secret')}",
        'Content-Type': 'application/json'
    }
    return url, headers, True


class EnrollmentRequest(BaseModel):
    """Member enrollment request model."""
    # Personal Info
    first_name: str
    last_name: str
    member_type: str = "Adult"  # Adult, Teenager, Child
    date_of_birth: Optional[str] = None
    gender: Optional[str] = None

    # Contact
    phone: str
    email: Optional[str] = None
    address: Optional[str] = None

    # Emergency Contact
    emergency_contact: Optional[str] = None
    emergency_phone: Optional[str] = None

    # Parent/Guardian (for minors)
    parent_member: Optional[str] = None

    # Membership
    membership_type: Optional[str] = None

    # RFID
    rfid_tag: Optional[str] = None

    # Photo
    photo: Optional[str] = None


@router.get("/list")
async def members_list_page(request: Request):
    """Render the members list page."""
    url, headers, connected = get_erpnext_client()

    members = []
    belt_ranks = {}

    if connected:
        try:
            # Fetch all members
            resp = requests.get(
                f"{url}/api/resource/Gym Member",
                headers=headers,
                params={
                    "fields": '["name", "full_name", "phone", "email", "member_type", "status", "current_rank", "current_stripes", "payment_status", "join_date", "rfid_tag", "photo"]',
                    "order_by": "full_name asc",
                    "limit_page_length": 500
                },
                timeout=15
            )
            if resp.status_code == 200:
                members = resp.json().get("data", [])

            # Fetch belt ranks for display
            resp = requests.get(
                f"{url}/api/resource/Belt Rank",
                headers=headers,
                params={"fields": '["name", "rank_name", "color"]', "limit_page_length": 100},
                timeout=10
            )
            if resp.status_code == 200:
                ranks = resp.json().get("data", [])
                belt_ranks = {r["name"]: r for r in ranks}

        except Exception as e:
            print(f"Error fetching members: {e}")

    return templates.TemplateResponse(
        "enrollment/members_list.html",
        {
            "request": request,
            "connected": connected,
            "members": members,
            "belt_ranks": belt_ranks
        }
    )


@router.get("/member/{member_id}")
async def member_detail_page(request: Request, member_id: str):
    """Render the member detail page."""
    url, headers, connected = get_erpnext_client()

    member = None
    belt_ranks = {}
    attendance_history = []

    if connected:
        try:
            # Fetch member details
            resp = requests.get(
                f"{url}/api/resource/Gym Member/{member_id}",
                headers=headers,
                timeout=10
            )
            if resp.status_code == 200:
                member = resp.json().get("data", {})

            # Fetch belt ranks for display
            resp = requests.get(
                f"{url}/api/resource/Belt Rank",
                headers=headers,
                params={"fields": '["name", "rank_name", "color"]', "limit_page_length": 100},
                timeout=10
            )
            if resp.status_code == 200:
                ranks = resp.json().get("data", [])
                belt_ranks = {r["name"]: r for r in ranks}

            # Fetch recent attendance
            resp = requests.get(
                f"{url}/api/resource/Gym Attendance",
                headers=headers,
                params={
                    "filters": f'[["member", "=", "{member_id}"]]',
                    "fields": '["name", "check_in_time", "training_counted"]',
                    "order_by": "check_in_time desc",
                    "limit_page_length": 20
                },
                timeout=10
            )
            if resp.status_code == 200:
                attendance_history = resp.json().get("data", [])

        except Exception as e:
            print(f"Error fetching member details: {e}")

    return templates.TemplateResponse(
        "enrollment/member_detail.html",
        {
            "request": request,
            "connected": connected,
            "member": member,
            "belt_ranks": belt_ranks,
            "attendance_history": attendance_history
        }
    )


@router.get("/")
async def enrollment_page(request: Request):
    """Render the enrollment form page."""
    url, headers, connected = get_erpnext_client()

    membership_types = []
    belt_ranks = []
    existing_members = []

    if connected:
        try:
            # Fetch membership types
            resp = requests.get(
                f"{url}/api/resource/Membership Type",
                headers=headers,
                params={"filters": '[["is_active", "=", 1]]', "fields": '["name", "membership_name", "price", "membership_category"]'},
                timeout=10
            )
            if resp.status_code == 200:
                membership_types = resp.json().get("data", [])

            # Fetch belt ranks (for initial rank - just white belt)
            resp = requests.get(
                f"{url}/api/resource/Belt Rank",
                headers=headers,
                params={"filters": '[["rank_order", "=", 10]]', "fields": '["name", "rank_name", "color"]'},
                timeout=10
            )
            if resp.status_code == 200:
                belt_ranks = resp.json().get("data", [])

            # Fetch existing adult members (for parent linking)
            resp = requests.get(
                f"{url}/api/resource/Gym Member",
                headers=headers,
                params={
                    "filters": '[["member_type", "=", "Adult"], ["status", "=", "Active"]]',
                    "fields": '["name", "full_name", "phone"]',
                    "limit_page_length": 500
                },
                timeout=10
            )
            if resp.status_code == 200:
                existing_members = resp.json().get("data", [])

        except Exception as e:
            print(f"Error fetching data: {e}")

    return templates.TemplateResponse(
        "enrollment/enroll.html",
        {
            "request": request,
            "connected": connected,
            "membership_types": membership_types,
            "belt_ranks": belt_ranks,
            "existing_members": existing_members
        }
    )


@router.post("/create")
async def create_member(enrollment: EnrollmentRequest):
    """Create a new gym member."""
    url, headers, connected = get_erpnext_client()

    if not connected:
        return JSONResponse({"success": False, "error": "ERPNext not connected"}, status_code=503)

    config = get_config()
    company = config.get_company()

    try:
        # Get white belt rank
        white_belt = None
        resp = requests.get(
            f"{url}/api/resource/Belt Rank",
            headers=headers,
            params={"filters": '[["rank_order", "=", 10]]', "fields": '["name"]'},
            timeout=10
        )
        if resp.status_code == 200:
            ranks = resp.json().get("data", [])
            if ranks:
                white_belt = ranks[0].get("name")

        # Build member data
        member_data = {
            "doctype": "Gym Member",
            "first_name": enrollment.first_name,
            "last_name": enrollment.last_name,
            "full_name": f"{enrollment.first_name} {enrollment.last_name}",
            "member_type": enrollment.member_type,
            "phone": enrollment.phone,
            "status": "Active",
            "join_date": date.today().isoformat(),
            "current_rank": white_belt,
            "current_stripes": 0,
            "days_at_current_rank": 0,
            "total_training_days": 0,
            "payment_status": "Current"
        }

        # Add optional fields
        if enrollment.email:
            member_data["email"] = enrollment.email
        if enrollment.date_of_birth:
            member_data["date_of_birth"] = enrollment.date_of_birth
        if enrollment.gender:
            member_data["gender"] = enrollment.gender
        if enrollment.address:
            member_data["address"] = enrollment.address
        if enrollment.emergency_contact:
            member_data["emergency_contact"] = enrollment.emergency_contact
        if enrollment.emergency_phone:
            member_data["emergency_phone"] = enrollment.emergency_phone
        if enrollment.parent_member:
            member_data["parent_member"] = enrollment.parent_member
        if enrollment.rfid_tag:
            member_data["rfid_tag"] = enrollment.rfid_tag
        if enrollment.membership_type:
            member_data["current_membership_type"] = enrollment.membership_type
        if enrollment.photo:
            member_data["photo"] = enrollment.photo
        if company:
            member_data["company"] = company

        # Create the member
        resp = requests.post(
            f"{url}/api/resource/Gym Member",
            headers=headers,
            json=member_data,
            timeout=15
        )

        if resp.status_code in [200, 201]:
            result = resp.json()
            member_id = result.get("data", {}).get("name")
            return JSONResponse({
                "success": True,
                "message": f"Member {enrollment.first_name} {enrollment.last_name} enrolled successfully",
                "member_id": member_id
            })
        else:
            error_msg = resp.json().get("exc", resp.text)
            # Check for duplicate RFID
            if "Duplicate" in str(error_msg) and "rfid" in str(error_msg).lower():
                return JSONResponse({
                    "success": False,
                    "error": "This RFID tag is already assigned to another member"
                }, status_code=400)
            return JSONResponse({
                "success": False,
                "error": f"Failed to create member: {error_msg[:200]}"
            }, status_code=400)

    except Exception as e:
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)


@router.get("/check-rfid/{rfid_tag}")
async def check_rfid(rfid_tag: str):
    """Check if an RFID tag is already in use."""
    url, headers, connected = get_erpnext_client()

    if not connected:
        return JSONResponse({"success": False, "error": "Not connected"}, status_code=503)

    try:
        # Check Gym Member
        resp = requests.get(
            f"{url}/api/resource/Gym Member",
            headers=headers,
            params={"filters": f'[["rfid_tag", "=", "{rfid_tag}"]]', "fields": '["name", "full_name"]'},
            timeout=10
        )

        if resp.status_code == 200:
            members = resp.json().get("data", [])
            if members:
                return JSONResponse({
                    "success": True,
                    "in_use": True,
                    "used_by": members[0].get("full_name", "Unknown")
                })

        # Check Gym Staff
        resp = requests.get(
            f"{url}/api/resource/Gym Staff",
            headers=headers,
            params={"filters": f'[["rfid_tag", "=", "{rfid_tag}"]]', "fields": '["name", "staff_name"]'},
            timeout=10
        )

        if resp.status_code == 200:
            staff = resp.json().get("data", [])
            if staff:
                return JSONResponse({
                    "success": True,
                    "in_use": True,
                    "used_by": f"Staff: {staff[0].get('staff_name', 'Unknown')}"
                })

        return JSONResponse({
            "success": True,
            "in_use": False
        })

    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@router.get("/search-parent")
async def search_parent(q: str = ""):
    """Search for potential parent members."""
    url, headers, connected = get_erpnext_client()

    if not connected:
        return JSONResponse({"success": False, "error": "Not connected"}, status_code=503)

    try:
        filters = '[["member_type", "=", "Adult"], ["status", "=", "Active"]]'
        if q:
            filters = f'[["member_type", "=", "Adult"], ["status", "=", "Active"], ["full_name", "like", "%{q}%"]]'

        resp = requests.get(
            f"{url}/api/resource/Gym Member",
            headers=headers,
            params={
                "filters": filters,
                "fields": '["name", "full_name", "phone"]',
                "limit_page_length": 20
            },
            timeout=10
        )

        if resp.status_code == 200:
            members = resp.json().get("data", [])
            return JSONResponse({
                "success": True,
                "members": members
            })

        return JSONResponse({"success": False, "members": []})

    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)
