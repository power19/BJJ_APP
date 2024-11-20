# app/routes/main.py
from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/customers")
async def customers_page(request: Request):
    return templates.TemplateResponse(
        "customers.html",
        {"request": request}
    )

@router.get("/billing")
async def billing_page(request: Request):
    return templates.TemplateResponse(
        "billing.html",
        {"request": request}
    )

@router.get("/attendance")
async def attendance_page(request: Request):
    return templates.TemplateResponse(
        "attendance.html",
        {"request": request}
    )