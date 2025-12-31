# app/routes/setup.py
from fastapi import APIRouter, Request, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from typing import Optional
import requests

from ..utils.config import get_config

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


class SetupRequest(BaseModel):
    erpnext_url: str
    erpnext_api_key: str
    erpnext_api_secret: str


@router.get("")
async def setup_page(request: Request, edit: bool = False):
    """Display the setup page."""
    config = get_config()

    # If already configured and not in edit mode, redirect to home (unless connection is failing)
    if config.is_configured() and not edit:
        # Test if current config still works
        erp_config = config.get_erpnext_config()
        if _test_erp_connection(erp_config['url'], erp_config['api_key'], erp_config['api_secret']):
            return RedirectResponse(url="/", status_code=302)

    return templates.TemplateResponse(
        "setup.html",
        {
            "request": request,
            "config": config.get_erpnext_config() if config.is_configured() else None
        }
    )


@router.post("/test-connection")
async def test_connection(setup_request: SetupRequest):
    """Test connection to ERPNext with provided credentials."""
    url = setup_request.erpnext_url.rstrip('/')
    api_key = setup_request.erpnext_api_key
    api_secret = setup_request.erpnext_api_secret

    result = _test_erp_connection(url, api_key, api_secret)

    if result:
        return {"success": True, "user": result}
    else:
        return {"success": False, "error": "Could not connect to ERPNext. Please check your credentials."}


@router.post("/save")
async def save_config(setup_request: SetupRequest):
    """Save the configuration after successful connection test."""
    url = setup_request.erpnext_url.rstrip('/')
    api_key = setup_request.erpnext_api_key
    api_secret = setup_request.erpnext_api_secret

    # Verify connection one more time before saving
    if not _test_erp_connection(url, api_key, api_secret):
        return {"success": False, "error": "Connection test failed. Please verify your credentials."}

    config = get_config()
    success = config.save_config({
        'erpnext_url': url,
        'erpnext_api_key': api_key,
        'erpnext_api_secret': api_secret
    })

    if success:
        # Reload the config to ensure it's available
        config.reload()
        return {"success": True, "message": "Configuration saved successfully"}
    else:
        return {"success": False, "error": "Failed to save configuration file"}


def _test_erp_connection(url: str, api_key: str, api_secret: str) -> Optional[str]:
    """
    Test ERPNext connection and return the logged-in user if successful.

    Returns:
        str: The logged-in user's email if successful
        None: If connection failed
    """
    try:
        headers = {
            'Authorization': f'token {api_key}:{api_secret}',
            'Content-Type': 'application/json'
        }

        # Test the connection by getting the logged-in user
        response = requests.get(
            f"{url}/api/method/frappe.auth.get_logged_user",
            headers=headers,
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            return data.get('message', 'Unknown User')

        return None

    except requests.exceptions.Timeout:
        print("Connection timeout")
        return None
    except requests.exceptions.ConnectionError:
        print("Connection error")
        return None
    except Exception as e:
        print(f"Connection test error: {str(e)}")
        return None
