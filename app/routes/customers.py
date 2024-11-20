from fastapi import APIRouter, HTTPException, Depends
from typing import List
from pydantic import BaseModel
from ..utils.erp_client import ERPNextClient, get_erp_client
import json

router = APIRouter()

class CustomerResponse(BaseModel):
    name: str
    email: str | None = None

@router.get("/customers/search")
async def search_customers(q: str, erp_client: ERPNextClient = Depends(get_erp_client)):
    print(f"Search query received: {q}")
    try:
        # Use the client's API method format
        endpoint = f"{erp_client.base_url}/api/resource/Customer"
        
        params = {
            'fields': '["name", "customer_name", "email_id"]',
            'filters': json.dumps([["customer_name", "like", f"%{q}%"]])
        }
        
        response = erp_client.session.get(endpoint, params=params)
        response.raise_for_status()
        
        data = response.json()
        customers = data.get("data", [])
        
        return [
            CustomerResponse(
                name=customer.get("customer_name", ""),
                email=customer.get("email_id")
            )
            for customer in customers
        ]
    except Exception as e:
        print(f"Error in search: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))