# main.py
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from app.routes import billing, attendance, customers, files, main, payment, overview, enrollment, handover

app = FastAPI(title="Invictus BJJ")

# Initialize templates
templates = Jinja2Templates(directory="app/templates")

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.include_router(files.router, prefix="/api/v1/files", tags=["files"])

@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# Include routers
app.include_router(customers.router, prefix="/api")  # This means routes will start with /api
app.include_router(billing.router, prefix="/api/v1/billing", tags=["billing"])
app.include_router(attendance.router, prefix="/api/v1/attendance", tags=["attendance"])
app.include_router(main.router, prefix="/api/v1/main", tags=["main"])
app.include_router(payment.router, prefix="/api/v1/payment", tags=["payment"])
app.include_router(overview.router)  # No prefix for overview since it's a main page
app.include_router(enrollment.router, prefix="/api/v1/enrollment", tags=["enrollment"])  # Add enrollment router
app.include_router(handover.router, prefix="/api/v1/payment/handover", tags=["handover"])
# Root route using the templates
@app.get("/")
async def root(request: Request):
    # Actually using the templates instance here
    return templates.TemplateResponse(
        "index.html",
        {"request": request}
    )