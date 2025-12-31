# app/routes/attendance.py
"""
RFID Attendance scanning routes.
Handles member check-in via RFID tag scanning.
"""
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from datetime import datetime, date, timedelta
import requests
from typing import Optional

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
        'Authorization': f"token {erp_config.get('api_key', '')}:{erp_config.get('api_secret', '')}",
        'Content-Type': 'application/json'
    }
    return url, headers, True


@router.get("/scan", response_class=HTMLResponse)
async def attendance_scan_page(request: Request):
    """Display the RFID attendance scanning interface."""
    config = get_config()
    return templates.TemplateResponse("attendance/scan.html", {
        "request": request,
        "is_connected": config.is_configured()
    })


@router.get("/lookup/{rfid_tag}")
async def lookup_member_by_rfid(rfid_tag: str):
    """Look up a member by their RFID tag."""
    url, headers, connected = get_erpnext_client()

    if not connected:
        return JSONResponse({
            "success": False,
            "error": "ERPNext not connected"
        }, status_code=503)

    try:
        # Search for member with this RFID tag
        response = requests.get(
            f"{url}/api/resource/Gym Member",
            headers=headers,
            params={
                "filters": f'[["rfid_tag", "=", "{rfid_tag}"]]',
                "fields": '["name", "first_name", "last_name", "full_name", "photo", "member_type", "status", "current_rank", "current_stripes", "days_at_current_rank", "total_training_days", "payment_status", "current_membership_type", "membership_end_date", "remaining_sessions"]'
            },
            timeout=10
        )

        if response.status_code != 200:
            return JSONResponse({
                "success": False,
                "error": "Failed to query ERPNext"
            }, status_code=500)

        data = response.json()
        members = data.get("data", [])

        if not members:
            return JSONResponse({
                "success": False,
                "error": "Member not found",
                "rfid_tag": rfid_tag
            }, status_code=404)

        member = members[0]

        # Get belt rank details if available
        rank_info = None
        if member.get("current_rank"):
            rank_response = requests.get(
                f"{url}/api/resource/Belt Rank/{member['current_rank']}",
                headers=headers,
                timeout=10
            )
            if rank_response.status_code == 200:
                rank_data = rank_response.json().get("data", {})
                rank_info = {
                    "name": rank_data.get("rank_name"),
                    "color": rank_data.get("color"),
                    "days_required": rank_data.get("days_required", 0)
                }

        # Check if already checked in today
        today = date.today().isoformat()
        attendance_response = requests.get(
            f"{url}/api/resource/Gym Attendance",
            headers=headers,
            params={
                "filters": f'[["member", "=", "{member["name"]}"], ["attendance_date", "=", "{today}"]]',
                "fields": '["name", "check_in_time"]'
            },
            timeout=10
        )

        already_checked_in = False
        check_in_time = None
        if attendance_response.status_code == 200:
            attendance_data = attendance_response.json().get("data", [])
            if attendance_data:
                already_checked_in = True
                check_in_time = attendance_data[0].get("check_in_time")

        return JSONResponse({
            "success": True,
            "member": {
                "id": member.get("name"),
                "first_name": member.get("first_name"),
                "last_name": member.get("last_name"),
                "full_name": member.get("full_name") or f"{member.get('first_name', '')} {member.get('last_name', '')}".strip(),
                "photo": member.get("photo"),
                "member_type": member.get("member_type"),
                "status": member.get("status"),
                "payment_status": member.get("payment_status", "Current"),
                "membership_type": member.get("current_membership_type"),
                "membership_end_date": member.get("membership_end_date"),
                "remaining_sessions": member.get("remaining_sessions", 0),
                "current_stripes": member.get("current_stripes", 0),
                "days_at_current_rank": member.get("days_at_current_rank", 0),
                "total_training_days": member.get("total_training_days", 0),
                "rank": rank_info
            },
            "already_checked_in": already_checked_in,
            "check_in_time": check_in_time
        })

    except requests.exceptions.Timeout:
        return JSONResponse({
            "success": False,
            "error": "Connection timeout"
        }, status_code=504)
    except Exception as e:
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)


@router.post("/check-in")
async def check_in_member(request: Request):
    """Check in a member via RFID."""
    url, headers, connected = get_erpnext_client()

    if not connected:
        return JSONResponse({
            "success": False,
            "error": "ERPNext not connected"
        }, status_code=503)

    try:
        body = await request.json()
        rfid_tag = body.get("rfid_tag")
        class_type = body.get("class_type")  # Optional

        if not rfid_tag:
            return JSONResponse({
                "success": False,
                "error": "RFID tag required"
            }, status_code=400)

        # First lookup the member
        lookup_response = requests.get(
            f"{url}/api/resource/Gym Member",
            headers=headers,
            params={
                "filters": f'[["rfid_tag", "=", "{rfid_tag}"]]',
                "fields": '["name", "first_name", "last_name", "full_name", "photo", "status", "payment_status", "days_at_current_rank", "total_training_days", "current_rank"]'
            },
            timeout=10
        )

        if lookup_response.status_code != 200:
            return JSONResponse({
                "success": False,
                "error": "Failed to query member"
            }, status_code=500)

        members = lookup_response.json().get("data", [])
        if not members:
            return JSONResponse({
                "success": False,
                "error": "Member not found"
            }, status_code=404)

        member = members[0]
        member_id = member["name"]

        # Check member status
        if member.get("status") != "Active":
            return JSONResponse({
                "success": False,
                "error": f"Member status is {member.get('status')}",
                "member_name": member.get("full_name") or f"{member.get('first_name', '')} {member.get('last_name', '')}".strip()
            }, status_code=400)

        # Check if already checked in today
        today = date.today().isoformat()
        existing = requests.get(
            f"{url}/api/resource/Gym Attendance",
            headers=headers,
            params={
                "filters": f'[["member", "=", "{member_id}"], ["attendance_date", "=", "{today}"]]'
            },
            timeout=10
        )

        if existing.status_code == 200 and existing.json().get("data"):
            return JSONResponse({
                "success": True,
                "already_checked_in": True,
                "message": "Already checked in today",
                "member": {
                    "full_name": member.get("full_name") or f"{member.get('first_name', '')} {member.get('last_name', '')}".strip(),
                    "photo": member.get("photo"),
                    "total_training_days": member.get("total_training_days", 0)
                }
            })

        # Determine if this counts towards rank (payment must be current)
        payment_current = member.get("payment_status") == "Current"
        counts_towards_rank = payment_current

        # Create attendance record
        now = datetime.now()
        attendance_data = {
            "doctype": "Gym Attendance",
            "member": member_id,
            "attendance_date": today,
            "check_in_time": now.strftime("%H:%M:%S"),
            "rfid_tag": rfid_tag,
            "counts_towards_rank": 1 if counts_towards_rank else 0,
            "payment_was_current": 1 if payment_current else 0
        }

        if class_type:
            attendance_data["class_type"] = class_type

        create_response = requests.post(
            f"{url}/api/resource/Gym Attendance",
            headers=headers,
            json=attendance_data,
            timeout=10
        )

        if create_response.status_code not in [200, 201]:
            return JSONResponse({
                "success": False,
                "error": "Failed to create attendance record"
            }, status_code=500)

        # Update member's training days if payment is current
        new_days_at_rank = member.get("days_at_current_rank", 0)
        new_total_days = member.get("total_training_days", 0)

        if counts_towards_rank:
            new_days_at_rank += 1
            new_total_days += 1

            # Update member record
            update_data = {
                "days_at_current_rank": new_days_at_rank,
                "total_training_days": new_total_days
            }

            # Check if eligible for promotion
            if member.get("current_rank"):
                rank_response = requests.get(
                    f"{url}/api/resource/Belt Rank/{member['current_rank']}",
                    headers=headers,
                    timeout=10
                )
                if rank_response.status_code == 200:
                    rank_data = rank_response.json().get("data", {})
                    days_required = rank_data.get("days_required", 0)
                    if days_required > 0 and new_days_at_rank >= days_required:
                        update_data["eligible_for_promotion"] = 1

            requests.put(
                f"{url}/api/resource/Gym Member/{member_id}",
                headers=headers,
                json=update_data,
                timeout=10
            )

        return JSONResponse({
            "success": True,
            "message": "Check-in successful",
            "member": {
                "full_name": member.get("full_name") or f"{member.get('first_name', '')} {member.get('last_name', '')}".strip(),
                "photo": member.get("photo"),
                "days_at_current_rank": new_days_at_rank,
                "total_training_days": new_total_days,
                "payment_current": payment_current,
                "counts_towards_rank": counts_towards_rank
            }
        })

    except Exception as e:
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)


@router.get("/stats/{rfid_tag}")
async def get_member_stats(rfid_tag: str):
    """Get training statistics for a member by RFID (for self-service kiosk)."""
    url, headers, connected = get_erpnext_client()

    if not connected:
        return JSONResponse({
            "success": False,
            "error": "ERPNext not connected"
        }, status_code=503)

    try:
        # Look up member
        response = requests.get(
            f"{url}/api/resource/Gym Member",
            headers=headers,
            params={
                "filters": f'[["rfid_tag", "=", "{rfid_tag}"]]',
                "fields": '["name", "first_name", "last_name", "full_name", "photo", "current_rank", "current_stripes", "days_at_current_rank", "total_training_days", "last_promotion_date", "eligible_for_promotion", "join_date"]'
            },
            timeout=10
        )

        if response.status_code != 200:
            return JSONResponse({
                "success": False,
                "error": "Failed to query ERPNext"
            }, status_code=500)

        members = response.json().get("data", [])
        if not members:
            return JSONResponse({
                "success": False,
                "error": "Member not found"
            }, status_code=404)

        member = members[0]

        # Get rank info
        rank_info = None
        days_to_next_rank = None
        if member.get("current_rank"):
            rank_response = requests.get(
                f"{url}/api/resource/Belt Rank/{member['current_rank']}",
                headers=headers,
                timeout=10
            )
            if rank_response.status_code == 200:
                rank_data = rank_response.json().get("data", {})
                days_required = rank_data.get("days_required", 0)
                days_at_rank = member.get("days_at_current_rank", 0)

                rank_info = {
                    "name": rank_data.get("rank_name"),
                    "color": rank_data.get("color"),
                    "days_required": days_required,
                    "stripes_available": rank_data.get("stripes_available", 4)
                }

                if days_required > 0:
                    days_to_next_rank = max(0, days_required - days_at_rank)

        # Get recent attendance (last 30 days)
        thirty_days_ago = (date.today() - timedelta(days=30)).isoformat()

        attendance_response = requests.get(
            f"{url}/api/resource/Gym Attendance",
            headers=headers,
            params={
                "filters": f'[["member", "=", "{member["name"]}"], ["attendance_date", ">=", "{thirty_days_ago}"]]',
                "fields": '["attendance_date"]',
                "limit_page_length": 100
            },
            timeout=10
        )

        recent_days = 0
        if attendance_response.status_code == 200:
            recent_days = len(attendance_response.json().get("data", []))

        return JSONResponse({
            "success": True,
            "member": {
                "full_name": member.get("full_name") or f"{member.get('first_name', '')} {member.get('last_name', '')}".strip(),
                "photo": member.get("photo"),
                "join_date": member.get("join_date"),
                "rank": rank_info,
                "current_stripes": member.get("current_stripes", 0),
                "days_at_current_rank": member.get("days_at_current_rank", 0),
                "total_training_days": member.get("total_training_days", 0),
                "days_to_next_rank": days_to_next_rank,
                "eligible_for_promotion": member.get("eligible_for_promotion", False),
                "last_promotion_date": member.get("last_promotion_date"),
                "training_days_last_30": recent_days
            }
        })

    except Exception as e:
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)


# Legacy endpoints for backward compatibility
@router.get("")
async def attendance_scanner(request: Request):
    """Redirect to new scan page."""
    return templates.TemplateResponse("attendance/scan.html", {
        "request": request,
        "is_connected": get_config().is_configured()
    })
