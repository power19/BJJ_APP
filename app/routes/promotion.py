# app/routes/promotion.py
"""
Belt promotion routes with coach RFID verification.
Handles member rank progression in BJJ belt system.
"""
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from datetime import date
import requests as http_requests

from ..utils.config import get_config

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


def get_erpnext_connection():
    """Get ERPNext connection details."""
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


@router.get("/", response_class=HTMLResponse)
async def promotion_page(request: Request):
    """Display the belt promotion interface."""
    config = get_config()
    return templates.TemplateResponse("promotion/promote.html", {
        "request": request,
        "is_connected": config.is_configured()
    })


@router.get("/member/{rfid_tag}")
async def lookup_member_for_promotion(rfid_tag: str):
    """Look up member by RFID for promotion check."""
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
                "fields": '["name", "first_name", "last_name", "full_name", "photo", "member_type", "status", "current_rank", "current_stripes", "days_at_current_rank", "total_training_days", "payment_status", "eligible_for_promotion", "last_promotion_date"]'
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

        # Get current rank details
        current_rank_info = None
        next_rank_info = None
        days_required = 0

        if member.get("current_rank"):
            rank_response = http_requests.get(
                f"{url}/api/resource/Belt Rank/{member['current_rank']}",
                headers=headers,
                timeout=10
            )
            if rank_response.status_code == 200:
                rank_data = rank_response.json().get("data", {})
                current_rank_info = {
                    "name": rank_data.get("rank_name"),
                    "color": rank_data.get("color"),
                    "order": rank_data.get("rank_order"),
                    "days_required": rank_data.get("days_required", 0),
                    "stripes_available": rank_data.get("stripes_available", 4)
                }
                days_required = rank_data.get("days_required", 0)

                # Find the next rank
                next_order = rank_data.get("rank_order", 0) + 1
                next_response = http_requests.get(
                    f"{url}/api/resource/Belt Rank",
                    headers=headers,
                    params={
                        "filters": f'[["rank_order", "=", {next_order}], ["is_active", "=", 1]]',
                        "fields": '["name", "rank_name", "color", "rank_order", "days_required"]'
                    },
                    timeout=10
                )
                if next_response.status_code == 200:
                    next_ranks = next_response.json().get("data", [])
                    if next_ranks:
                        next_rank_info = {
                            "id": next_ranks[0].get("name"),
                            "name": next_ranks[0].get("rank_name"),
                            "color": next_ranks[0].get("color")
                        }

        # Get all available ranks for manual selection
        all_ranks_response = http_requests.get(
            f"{url}/api/resource/Belt Rank",
            headers=headers,
            params={
                "filters": '[["is_active", "=", 1]]',
                "fields": '["name", "rank_name", "color", "rank_order"]',
                "order_by": "rank_order asc"
            },
            timeout=10
        )

        all_ranks = []
        if all_ranks_response.status_code == 200:
            all_ranks = all_ranks_response.json().get("data", [])

        # Check eligibility
        days_at_rank = member.get("days_at_current_rank", 0)
        payment_current = member.get("payment_status") == "Current"
        meets_days_requirement = days_required > 0 and days_at_rank >= days_required
        is_eligible = meets_days_requirement and payment_current

        return JSONResponse({
            "success": True,
            "member": {
                "id": member_id,
                "first_name": member.get("first_name"),
                "last_name": member.get("last_name"),
                "full_name": member.get("full_name") or f"{member.get('first_name', '')} {member.get('last_name', '')}".strip(),
                "photo": member.get("photo"),
                "member_type": member.get("member_type"),
                "status": member.get("status"),
                "current_stripes": member.get("current_stripes", 0),
                "days_at_current_rank": days_at_rank,
                "total_training_days": member.get("total_training_days", 0),
                "payment_status": member.get("payment_status"),
                "last_promotion_date": member.get("last_promotion_date"),
                "current_rank": current_rank_info,
                "next_rank": next_rank_info
            },
            "eligibility": {
                "is_eligible": is_eligible,
                "days_required": days_required,
                "days_completed": days_at_rank,
                "payment_current": payment_current,
                "meets_days_requirement": meets_days_requirement
            },
            "all_ranks": all_ranks
        })

    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@router.get("/coach/{rfid_tag}")
async def verify_coach_for_promotion(rfid_tag: str):
    """Verify coach RFID for promotion authorization."""
    url, headers, connected = get_erpnext_connection()

    if not connected:
        return JSONResponse({"success": False, "error": "ERPNext not connected"}, status_code=503)

    try:
        response = http_requests.get(
            f"{url}/api/resource/Gym Staff",
            headers=headers,
            params={
                "filters": f'[["rfid_tag", "=", "{rfid_tag}"], ["is_active", "=", 1]]',
                "fields": '["name", "staff_name", "role", "can_promote", "photo", "current_rank"]'
            },
            timeout=10
        )

        if response.status_code != 200:
            return JSONResponse({"success": False, "error": "Failed to query ERPNext"}, status_code=500)

        staff_list = response.json().get("data", [])
        if not staff_list:
            return JSONResponse({"success": False, "error": "Staff not found or inactive"}, status_code=404)

        staff = staff_list[0]

        if not staff.get("can_promote"):
            return JSONResponse({
                "success": False,
                "error": "Not authorized to promote members",
                "staff_name": staff.get("staff_name")
            }, status_code=403)

        # Get staff's rank info if available
        staff_rank = None
        if staff.get("current_rank"):
            rank_response = http_requests.get(
                f"{url}/api/resource/Belt Rank/{staff['current_rank']}",
                headers=headers,
                timeout=10
            )
            if rank_response.status_code == 200:
                rank_data = rank_response.json().get("data", {})
                staff_rank = {
                    "name": rank_data.get("rank_name"),
                    "color": rank_data.get("color")
                }

        return JSONResponse({
            "success": True,
            "coach": {
                "id": staff.get("name"),
                "name": staff.get("staff_name"),
                "role": staff.get("role"),
                "photo": staff.get("photo"),
                "rank": staff_rank
            }
        })

    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@router.post("/promote")
async def promote_member(request: Request):
    """Promote a member to a new belt rank."""
    url, headers, connected = get_erpnext_connection()

    if not connected:
        return JSONResponse({"success": False, "error": "ERPNext not connected"}, status_code=503)

    try:
        body = await request.json()
        member_id = body.get("member_id")
        coach_id = body.get("coach_id")
        new_rank_id = body.get("new_rank_id")
        notes = body.get("notes", "")

        if not all([member_id, coach_id, new_rank_id]):
            return JSONResponse({
                "success": False,
                "error": "Missing required fields: member_id, coach_id, new_rank_id"
            }, status_code=400)

        # Get current member info
        member_response = http_requests.get(
            f"{url}/api/resource/Gym Member/{member_id}",
            headers=headers,
            timeout=10
        )

        if member_response.status_code != 200:
            return JSONResponse({"success": False, "error": "Member not found"}, status_code=404)

        member_data = member_response.json().get("data", {})
        old_rank = member_data.get("current_rank")
        days_at_old_rank = member_data.get("days_at_current_rank", 0)

        # Create Rank History record
        today = date.today().isoformat()
        history_data = {
            "doctype": "Rank History",
            "member": member_id,
            "from_rank": old_rank,
            "to_rank": new_rank_id,
            "promotion_date": today,
            "days_in_previous_rank": days_at_old_rank,
            "promoted_by": coach_id,
            "promoter_rfid_verified": 1,
            "notes": notes
        }

        history_response = http_requests.post(
            f"{url}/api/resource/Rank History",
            headers=headers,
            json=history_data,
            timeout=10
        )

        if history_response.status_code not in [200, 201]:
            return JSONResponse({
                "success": False,
                "error": "Failed to create rank history"
            }, status_code=500)

        # Update member record
        member_update = {
            "current_rank": new_rank_id,
            "current_stripes": 0,  # Reset stripes on belt promotion
            "days_at_current_rank": 0,  # Reset days counter
            "last_promotion_date": today,
            "eligible_for_promotion": 0  # Reset eligibility flag
        }

        update_response = http_requests.put(
            f"{url}/api/resource/Gym Member/{member_id}",
            headers=headers,
            json=member_update,
            timeout=10
        )

        if update_response.status_code not in [200, 201]:
            return JSONResponse({
                "success": False,
                "error": "Failed to update member rank"
            }, status_code=500)

        # Get new rank info for response
        new_rank_response = http_requests.get(
            f"{url}/api/resource/Belt Rank/{new_rank_id}",
            headers=headers,
            timeout=10
        )

        new_rank_name = new_rank_id
        new_rank_color = "#000000"
        if new_rank_response.status_code == 200:
            new_rank_data = new_rank_response.json().get("data", {})
            new_rank_name = new_rank_data.get("rank_name", new_rank_id)
            new_rank_color = new_rank_data.get("color", "#000000")

        return JSONResponse({
            "success": True,
            "message": "Promotion successful",
            "member_name": member_data.get("full_name") or f"{member_data.get('first_name', '')} {member_data.get('last_name', '')}".strip(),
            "new_rank": {
                "name": new_rank_name,
                "color": new_rank_color
            },
            "days_at_previous_rank": days_at_old_rank
        })

    except Exception as e:
        import traceback
        print(f"Promotion error: {traceback.format_exc()}")
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@router.post("/add-stripe")
async def add_stripe(request: Request):
    """Add a stripe to a member's current belt."""
    url, headers, connected = get_erpnext_connection()

    if not connected:
        return JSONResponse({"success": False, "error": "ERPNext not connected"}, status_code=503)

    try:
        body = await request.json()
        member_id = body.get("member_id")
        coach_id = body.get("coach_id")

        if not all([member_id, coach_id]):
            return JSONResponse({
                "success": False,
                "error": "Missing required fields: member_id, coach_id"
            }, status_code=400)

        # Get current member info
        member_response = http_requests.get(
            f"{url}/api/resource/Gym Member/{member_id}",
            headers=headers,
            timeout=10
        )

        if member_response.status_code != 200:
            return JSONResponse({"success": False, "error": "Member not found"}, status_code=404)

        member_data = member_response.json().get("data", {})
        current_stripes = member_data.get("current_stripes", 0)
        current_rank = member_data.get("current_rank")

        # Check max stripes for this rank
        max_stripes = 4
        if current_rank:
            rank_response = http_requests.get(
                f"{url}/api/resource/Belt Rank/{current_rank}",
                headers=headers,
                timeout=10
            )
            if rank_response.status_code == 200:
                rank_data = rank_response.json().get("data", {})
                max_stripes = rank_data.get("stripes_available", 4)

        if current_stripes >= max_stripes:
            return JSONResponse({
                "success": False,
                "error": f"Maximum stripes ({max_stripes}) already reached"
            }, status_code=400)

        # Update member with new stripe count
        new_stripes = current_stripes + 1
        update_response = http_requests.put(
            f"{url}/api/resource/Gym Member/{member_id}",
            headers=headers,
            json={"current_stripes": new_stripes},
            timeout=10
        )

        if update_response.status_code not in [200, 201]:
            return JSONResponse({
                "success": False,
                "error": "Failed to update stripe count"
            }, status_code=500)

        return JSONResponse({
            "success": True,
            "message": "Stripe added",
            "current_stripes": new_stripes,
            "max_stripes": max_stripes
        })

    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)
