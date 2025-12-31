# app/routes/settings.py
from fastapi import APIRouter, Request, UploadFile, File
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from pathlib import Path
import json
import shutil
import time
import os
import requests

from ..utils.config import get_config
from ..utils.erpnext_init import get_initializer

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

# Paths
STATIC_DIR = Path("app/static")
IMAGES_DIR = STATIC_DIR / "images"
LOGO_PATH = IMAGES_DIR / "logo.png"
CONFIG_PATH = Path("config.json")


def ensure_dirs():
    """Ensure required directories exist."""
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)


@router.get("")
async def settings_page(request: Request):
    """Display the settings page."""
    ensure_dirs()
    config = get_config()
    erp_config = config.get_erpnext_config() if config.is_configured() else {}

    # Test connection
    is_connected = False
    if config.is_configured():
        from .setup import _test_erp_connection
        is_connected = bool(_test_erp_connection(
            erp_config.get('url', ''),
            erp_config.get('api_key', ''),
            erp_config.get('api_secret', '')
        ))

    return templates.TemplateResponse(
        "settings.html",
        {
            "request": request,
            "logo_exists": LOGO_PATH.exists(),
            "cache_bust": int(time.time()),
            "is_connected": is_connected,
            "erpnext_url": erp_config.get('url', ''),
        }
    )


@router.post("/upload-logo")
async def upload_logo(logo: UploadFile = File(...)):
    """Upload a new logo."""
    ensure_dirs()

    # Validate file type
    if not logo.content_type or not logo.content_type.startswith('image/'):
        return JSONResponse({"success": False, "error": "Invalid file type. Please upload an image."})

    # Check file size (max 5MB)
    contents = await logo.read()
    if len(contents) > 5 * 1024 * 1024:
        return JSONResponse({"success": False, "error": "File too large. Maximum size is 5MB."})

    try:
        # Save the logo
        with open(LOGO_PATH, 'wb') as f:
            f.write(contents)

        return JSONResponse({"success": True, "message": "Logo uploaded successfully"})
    except Exception as e:
        return JSONResponse({"success": False, "error": f"Failed to save logo: {str(e)}"})


@router.post("/remove-logo")
async def remove_logo():
    """Remove the current logo."""
    try:
        if LOGO_PATH.exists():
            LOGO_PATH.unlink()
        return JSONResponse({"success": True, "message": "Logo removed"})
    except Exception as e:
        return JSONResponse({"success": False, "error": f"Failed to remove logo: {str(e)}"})


@router.get("/backup/config")
async def backup_config():
    """Download the configuration backup."""
    config = get_config()

    # Create backup data
    backup_data = {
        "app": "invictus-bjj",
        "version": "1.0.0",
        "backup_time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "config": {}
    }

    # Add ERPNext config (without secrets for security)
    if config.is_configured():
        erp_config = config.get_erpnext_config()
        backup_data["config"]["erpnext"] = {
            "url": erp_config.get('url', ''),
            "api_key": erp_config.get('api_key', ''),
            # Note: Including secret in backup - user should keep file secure
            "api_secret": erp_config.get('api_secret', '')
        }

    # Write to temp file
    backup_filename = f"invictus_backup_{time.strftime('%Y%m%d_%H%M%S')}.json"
    backup_path = Path("/tmp") / backup_filename

    with open(backup_path, 'w') as f:
        json.dump(backup_data, f, indent=2)

    return FileResponse(
        path=backup_path,
        filename=backup_filename,
        media_type='application/json'
    )


@router.post("/restore-config")
async def restore_config(config: UploadFile = File(...)):
    """Restore configuration from backup file."""
    try:
        contents = await config.read()
        backup_data = json.loads(contents.decode('utf-8'))

        # Validate backup file
        if backup_data.get('app') != 'invictus-bjj':
            return JSONResponse({"success": False, "error": "Invalid backup file"})

        # Restore ERPNext config
        if 'config' in backup_data and 'erpnext' in backup_data['config']:
            erp_config = backup_data['config']['erpnext']

            app_config = get_config()
            success = app_config.save_config({
                'erpnext_url': erp_config.get('url', ''),
                'erpnext_api_key': erp_config.get('api_key', ''),
                'erpnext_api_secret': erp_config.get('api_secret', '')
            })

            if not success:
                return JSONResponse({"success": False, "error": "Failed to save configuration"})

            app_config.reload()

        return JSONResponse({"success": True, "message": "Configuration restored successfully"})

    except json.JSONDecodeError:
        return JSONResponse({"success": False, "error": "Invalid JSON file"})
    except Exception as e:
        return JSONResponse({"success": False, "error": f"Restore failed: {str(e)}"})


def _fetch_erpnext_data(url: str, api_key: str, api_secret: str, doctype: str, fields: list = None, limit: int = 0):
    """Fetch data from ERPNext for a specific doctype."""
    try:
        headers = {
            'Authorization': f'token {api_key}:{api_secret}',
            'Content-Type': 'application/json'
        }

        params = {
            'limit_page_length': limit if limit > 0 else 0  # 0 means no limit
        }

        if fields:
            params['fields'] = json.dumps(fields)

        response = requests.get(
            f"{url}/api/resource/{doctype}",
            headers=headers,
            params=params,
            timeout=60
        )

        if response.status_code == 200:
            return response.json().get('data', [])
        return []
    except Exception as e:
        print(f"Error fetching {doctype}: {str(e)}")
        return []


@router.get("/backup/erpnext")
async def backup_erpnext():
    """Download ERPNext data backup."""
    config = get_config()

    if not config.is_configured():
        return JSONResponse({"success": False, "error": "ERPNext not configured"})

    erp_config = config.get_erpnext_config()
    url = erp_config.get('url', '')
    api_key = erp_config.get('api_key', '')
    api_secret = erp_config.get('api_secret', '')

    # Create backup data structure
    backup_data = {
        "app": "invictus-bjj-erpnext-backup",
        "version": "1.0.0",
        "backup_time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "erpnext_url": url,
        "data": {}
    }

    # Fetch various doctypes - adjust these based on your ERPNext setup
    doctypes_to_backup = [
        "Customer",
        "Gym Member",
        "Sales Invoice",
        "Payment Entry",
        "Journal Entry",
        "Membership",
        "Membership Type",
    ]

    for doctype in doctypes_to_backup:
        try:
            data = _fetch_erpnext_data(url, api_key, api_secret, doctype)
            if data:
                backup_data["data"][doctype] = data
                print(f"Backed up {len(data)} {doctype} records")
        except Exception as e:
            print(f"Could not backup {doctype}: {str(e)}")

    # Write to temp file
    backup_filename = f"erpnext_backup_{time.strftime('%Y%m%d_%H%M%S')}.json"
    backup_path = Path("/tmp") / backup_filename

    with open(backup_path, 'w') as f:
        json.dump(backup_data, f, indent=2)

    return FileResponse(
        path=backup_path,
        filename=backup_filename,
        media_type='application/json'
    )


@router.get("/backup/erpnext/status")
async def backup_erpnext_status():
    """Check what data is available for backup."""
    config = get_config()

    if not config.is_configured():
        return JSONResponse({"success": False, "error": "ERPNext not configured"})

    erp_config = config.get_erpnext_config()
    url = erp_config.get('url', '')
    api_key = erp_config.get('api_key', '')
    api_secret = erp_config.get('api_secret', '')

    doctypes = ["Customer", "Gym Member", "Sales Invoice", "Payment Entry", "Membership"]
    counts = {}

    for doctype in doctypes:
        try:
            headers = {
                'Authorization': f'token {api_key}:{api_secret}',
                'Content-Type': 'application/json'
            }
            response = requests.get(
                f"{url}/api/resource/{doctype}",
                headers=headers,
                params={'limit_page_length': 1},
                timeout=10
            )
            if response.status_code == 200:
                # Get total count
                count_response = requests.get(
                    f"{url}/api/resource/{doctype}",
                    headers=headers,
                    params={'limit_page_length': 0, 'fields': '["name"]'},
                    timeout=30
                )
                if count_response.status_code == 200:
                    counts[doctype] = len(count_response.json().get('data', []))
                else:
                    counts[doctype] = 0
            else:
                counts[doctype] = -1  # Not accessible
        except Exception:
            counts[doctype] = -1

    return JSONResponse({"success": True, "counts": counts})


# =====================
# ERPNext Initialization
# =====================

@router.get("/init/status")
async def initialization_status():
    """Get the initialization status of all required doctypes."""
    initializer = get_initializer()
    config = get_config()

    if not config.is_configured():
        return JSONResponse({"success": False, "error": "ERPNext not configured"})

    try:
        status = initializer.get_initialization_status()
        is_complete = all(status.values())

        return JSONResponse({
            "success": True,
            "is_complete": is_complete,
            "doctypes": status
        })
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)})


@router.post("/init/run")
async def run_initialization():
    """Run the initialization process to create all required doctypes."""
    initializer = get_initializer()
    config = get_config()

    if not config.is_configured():
        return JSONResponse({"success": False, "error": "ERPNext not configured"})

    try:
        # Create doctypes
        results = initializer.initialize_all()

        # Check if all were successful
        all_success = all(success for success, _ in results.values())

        # Format results for response
        formatted_results = {
            name: {"success": success, "message": message}
            for name, (success, message) in results.items()
        }

        return JSONResponse({
            "success": all_success,
            "message": "Initialization complete" if all_success else "Some doctypes failed to create",
            "results": formatted_results
        })
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)})


@router.post("/init/create-defaults")
async def create_default_data():
    """Create default membership types, class types, and belt ranks."""
    initializer = get_initializer()
    config = get_config()

    if not config.is_configured():
        return JSONResponse({"success": False, "error": "ERPNext not configured"})

    try:
        results = initializer.create_default_data()

        # Results are already formatted as dict with success/message
        all_success = all(r.get("success", False) for r in results.values() if isinstance(r, dict))

        return JSONResponse({
            "success": all_success,
            "message": "Default data created" if all_success else "Some items failed",
            "results": results
        })
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)})


@router.post("/init/create-belt-ranks")
async def create_belt_ranks():
    """Create all BJJ belt ranks (adult + kids)."""
    initializer = get_initializer()
    config = get_config()

    if not config.is_configured():
        return JSONResponse({"success": False, "error": "ERPNext not configured"})

    try:
        results = initializer.create_belt_ranks_only()

        all_success = all(r.get("success", False) for r in results.values() if isinstance(r, dict))

        return JSONResponse({
            "success": all_success,
            "message": f"Created {len(results)} belt ranks" if all_success else "Some ranks failed",
            "results": results
        })
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)})
