# app/routes/files.py
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
import httpx
from ..utils.erp_client import get_erp_client

router = APIRouter()

@router.get("/file/{file_name}")
async def get_file(file_name: str):
    try:
        erp_client = get_erp_client()
        url, headers = erp_client.get_file_url(file_name)
        
        print(f"Fetching file from URL: {url}")  # Debug print
        print(f"With headers: {headers}")  # Debug print
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
            if response.status_code == 200:
                return StreamingResponse(
                    content=response.iter_bytes(),
                    media_type=response.headers.get('content-type', 'application/octet-stream')
                )
            else:
                print(f"Error response: {response.text}")  # Debug print
                raise HTTPException(status_code=response.status_code, detail="Failed to fetch file")
    except Exception as e:
        print(f"Error in get_file: {str(e)}")  # Debug print
        raise HTTPException(status_code=404, detail=str(e))