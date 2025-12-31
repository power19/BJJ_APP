# app/routes/settings.py
from fastapi import APIRouter, Request, UploadFile, File
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse, FileResponse
from pathlib import Path
import json
import shutil
import time
import os

from ..utils.config import get_config

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
