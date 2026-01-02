# app/routes/members.py
"""
Clean URL routes for member pages.
UI pages at /members, API endpoints stay at /api/v1/members
"""
from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse
import requests
from pydantic import BaseModel
from typing import Optional
from datetime import date

from app.utils.config import get_config

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


def get_erpnext_client():
    """Get ERPNext connection details."""
    config = get_config()
    if not config.is_configured():
        return None, None, False

    erp_config = config.get_erpnext_config()
    url = erp_config.get('url', '')
    api_key = erp_config.get('api_key', '')
    api_secret = erp_config.get('api_secret', '')

    headers = {
        'Authorization': f'token {api_key}:{api_secret}',
        'Content-Type': 'application/json'
    }

    return url, headers, True


# ============================================================================
# UI Pages (Clean URLs)
# ============================================================================

@router.get("")
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
        "members/list.html",
        {
            "request": request,
            "connected": connected,
            "members": members,
            "belt_ranks": belt_ranks
        }
    )


@router.get("/new")
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

            # Fetch existing adult members (for optional parent linking)
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
        "members/enroll.html",
        {
            "request": request,
            "connected": connected,
            "membership_types": membership_types,
            "belt_ranks": belt_ranks,
            "existing_members": existing_members
        }
    )


@router.get("/{member_id}")
async def member_detail_page(request: Request, member_id: str):
    """Render the member detail page."""
    url, headers, connected = get_erpnext_client()

    member = None
    belt_ranks = {}
    attendance_history = []
    membership_types = []

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

            # Fetch membership types
            resp = requests.get(
                f"{url}/api/resource/Membership Type",
                headers=headers,
                params={
                    "filters": '[["is_active", "=", 1]]',
                    "fields": '["name", "membership_name", "price", "membership_category", "is_recurring"]',
                    "limit_page_length": 100
                },
                timeout=10
            )
            if resp.status_code == 200:
                membership_types = resp.json().get("data", [])

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
        "members/detail.html",
        {
            "request": request,
            "connected": connected,
            "member": member,
            "belt_ranks": belt_ranks,
            "membership_types": membership_types,
            "attendance_history": attendance_history
        }
    )


@router.get("/{member_id}/edit")
async def member_edit_page(request: Request, member_id: str):
    """Render the member edit page."""
    url, headers, connected = get_erpnext_client()

    member = None

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

        except Exception as e:
            print(f"Error fetching member: {e}")

    if not member:
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/members", status_code=302)

    return templates.TemplateResponse(
        "members/edit.html",
        {
            "request": request,
            "connected": connected,
            "member": member
        }
    )


# ============================================================================
# API Endpoints
# ============================================================================

class EnrollmentRequest(BaseModel):
    """Enrollment request model."""
    first_name: str
    last_name: str
    member_type: str = "Adult"
    phone: str
    email: Optional[str] = None
    date_of_birth: Optional[str] = None
    gender: Optional[str] = None
    address: Optional[str] = None
    emergency_contact: Optional[str] = None
    emergency_phone: Optional[str] = None
    # Parent member (optional - for linking to existing member)
    parent_member: Optional[str] = None
    # Guardian info (for non-member parents)
    guardian_name: Optional[str] = None
    guardian_phone: Optional[str] = None
    guardian_email: Optional[str] = None
    guardian_relationship: Optional[str] = None
    # Membership
    rfid_tag: Optional[str] = None
    membership_type: Optional[str] = None
    photo: Optional[str] = None


class MemberUpdateRequest(BaseModel):
    """Request to update member details."""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    date_of_birth: Optional[str] = None
    gender: Optional[str] = None
    address: Optional[str] = None
    emergency_contact: Optional[str] = None
    emergency_phone: Optional[str] = None
    rfid_tag: Optional[str] = None
    guardian_name: Optional[str] = None
    guardian_phone: Optional[str] = None
    guardian_email: Optional[str] = None
    guardian_relationship: Optional[str] = None


class StatusUpdateRequest(BaseModel):
    """Request to update member status."""
    status: str


class MembershipUpdateRequest(BaseModel):
    """Request to update member's subscription."""
    membership_type: str
    payment_status: Optional[str] = None


@router.post("/api/create")
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
        # Guardian info for non-member parents
        if enrollment.guardian_name:
            member_data["guardian_name"] = enrollment.guardian_name
        if enrollment.guardian_phone:
            member_data["guardian_phone"] = enrollment.guardian_phone
        if enrollment.guardian_email:
            member_data["guardian_email"] = enrollment.guardian_email
        if enrollment.guardian_relationship:
            member_data["guardian_relationship"] = enrollment.guardian_relationship
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


@router.post("/api/{member_id}/update-status")
async def update_member_status(member_id: str, req: StatusUpdateRequest):
    """Update a member's status."""
    url, headers, connected = get_erpnext_client()

    if not connected:
        return JSONResponse({"success": False, "error": "ERPNext not connected"}, status_code=503)

    valid_statuses = ["Active", "Suspended", "Cancelled", "Expired"]
    if req.status not in valid_statuses:
        return JSONResponse({
            "success": False,
            "error": f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
        }, status_code=400)

    try:
        resp = requests.put(
            f"{url}/api/resource/Gym Member/{member_id}",
            headers=headers,
            json={"status": req.status},
            timeout=10
        )

        if resp.status_code == 200:
            action = {
                "Active": "reactivated",
                "Suspended": "suspended",
                "Cancelled": "cancelled",
                "Expired": "marked as expired"
            }.get(req.status, "updated")

            return JSONResponse({
                "success": True,
                "message": f"Member {action} successfully"
            })
        else:
            error_msg = resp.json().get("exc", resp.text)
            return JSONResponse({
                "success": False,
                "error": f"Failed to update status: {error_msg[:200]}"
            }, status_code=400)

    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@router.post("/api/{member_id}/update-membership")
async def update_member_membership(member_id: str, req: MembershipUpdateRequest):
    """Update a member's subscription type."""
    url, headers, connected = get_erpnext_client()

    if not connected:
        return JSONResponse({"success": False, "error": "ERPNext not connected"}, status_code=503)

    try:
        update_data = {"current_membership_type": req.membership_type}
        if req.payment_status:
            update_data["payment_status"] = req.payment_status

        resp = requests.put(
            f"{url}/api/resource/Gym Member/{member_id}",
            headers=headers,
            json=update_data,
            timeout=10
        )

        if resp.status_code == 200:
            return JSONResponse({
                "success": True,
                "message": "Membership updated successfully"
            })
        else:
            return JSONResponse({
                "success": False,
                "error": "Failed to update membership"
            }, status_code=400)

    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@router.post("/api/{member_id}/update-payment-status")
async def update_payment_status(member_id: str, payment_status: str):
    """Update a member's payment status."""
    url, headers, connected = get_erpnext_client()

    if not connected:
        return JSONResponse({"success": False, "error": "ERPNext not connected"}, status_code=503)

    valid_statuses = ["Current", "Overdue", "None"]
    if payment_status not in valid_statuses:
        return JSONResponse({
            "success": False,
            "error": f"Invalid payment status"
        }, status_code=400)

    try:
        resp = requests.put(
            f"{url}/api/resource/Gym Member/{member_id}",
            headers=headers,
            json={"payment_status": payment_status},
            timeout=10
        )

        if resp.status_code == 200:
            return JSONResponse({
                "success": True,
                "message": "Payment status updated"
            })
        else:
            return JSONResponse({
                "success": False,
                "error": "Failed to update payment status"
            }, status_code=400)

    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@router.get("/api/check-rfid/{rfid_tag}")
async def check_rfid(rfid_tag: str):
    """Check if an RFID tag is already in use."""
    url, headers, connected = get_erpnext_client()

    if not connected:
        return JSONResponse({"success": False, "error": "Not connected"}, status_code=503)

    try:
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

        return JSONResponse({"success": True, "in_use": False})

    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@router.put("/api/{member_id}/update")
async def update_member(member_id: str, req: MemberUpdateRequest):
    """Update a member's details."""
    url, headers, connected = get_erpnext_client()

    if not connected:
        return JSONResponse({"success": False, "error": "ERPNext not connected"}, status_code=503)

    try:
        # Build update data from non-None fields
        update_data = {}

        if req.first_name is not None:
            update_data["first_name"] = req.first_name
        if req.last_name is not None:
            update_data["last_name"] = req.last_name
        if req.first_name is not None or req.last_name is not None:
            # Need to fetch current values if only one is provided
            if req.first_name is None or req.last_name is None:
                current = requests.get(
                    f"{url}/api/resource/Gym Member/{member_id}",
                    headers=headers,
                    params={"fields": '["first_name", "last_name"]'},
                    timeout=10
                )
                if current.status_code == 200:
                    data = current.json().get("data", {})
                    first = req.first_name or data.get("first_name", "")
                    last = req.last_name or data.get("last_name", "")
                    update_data["full_name"] = f"{first} {last}"
            else:
                update_data["full_name"] = f"{req.first_name} {req.last_name}"

        if req.phone is not None:
            update_data["phone"] = req.phone
        if req.email is not None:
            update_data["email"] = req.email
        if req.date_of_birth is not None:
            update_data["date_of_birth"] = req.date_of_birth if req.date_of_birth else None
        if req.gender is not None:
            update_data["gender"] = req.gender
        if req.address is not None:
            update_data["address"] = req.address
        if req.emergency_contact is not None:
            update_data["emergency_contact"] = req.emergency_contact
        if req.emergency_phone is not None:
            update_data["emergency_phone"] = req.emergency_phone
        if req.rfid_tag is not None:
            update_data["rfid_tag"] = req.rfid_tag
        if req.guardian_name is not None:
            update_data["guardian_name"] = req.guardian_name
        if req.guardian_phone is not None:
            update_data["guardian_phone"] = req.guardian_phone
        if req.guardian_email is not None:
            update_data["guardian_email"] = req.guardian_email
        if req.guardian_relationship is not None:
            update_data["guardian_relationship"] = req.guardian_relationship

        if not update_data:
            return JSONResponse({
                "success": False,
                "error": "No fields to update"
            }, status_code=400)

        resp = requests.put(
            f"{url}/api/resource/Gym Member/{member_id}",
            headers=headers,
            json=update_data,
            timeout=15
        )

        if resp.status_code == 200:
            return JSONResponse({
                "success": True,
                "message": "Member updated successfully"
            })
        else:
            error_msg = resp.json().get("exc", resp.text)
            if "Duplicate" in str(error_msg) and "rfid" in str(error_msg).lower():
                return JSONResponse({
                    "success": False,
                    "error": "This RFID tag is already assigned to another member"
                }, status_code=400)
            return JSONResponse({
                "success": False,
                "error": f"Failed to update member: {str(error_msg)[:200]}"
            }, status_code=400)

    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@router.delete("/api/{member_id}/delete")
async def delete_member(member_id: str):
    """Delete a member."""
    url, headers, connected = get_erpnext_client()

    if not connected:
        return JSONResponse({"success": False, "error": "ERPNext not connected"}, status_code=503)

    try:
        resp = requests.delete(
            f"{url}/api/resource/Gym Member/{member_id}",
            headers=headers,
            timeout=15
        )

        if resp.status_code == 200:
            return JSONResponse({
                "success": True,
                "message": "Member deleted successfully"
            })
        elif resp.status_code == 404:
            return JSONResponse({
                "success": False,
                "error": "Member not found"
            }, status_code=404)
        else:
            error_msg = resp.json().get("exc", resp.text)
            # Check for linked records
            if "Cannot delete" in str(error_msg) or "linked" in str(error_msg).lower():
                return JSONResponse({
                    "success": False,
                    "error": "Cannot delete member with linked records (attendance, payments, etc.). Consider marking as Cancelled instead."
                }, status_code=400)
            return JSONResponse({
                "success": False,
                "error": f"Failed to delete member: {str(error_msg)[:200]}"
            }, status_code=400)

    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)
