# main.py
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.routes import billing, attendance, customers, files, main, payment, overview, enrollment, handover, setup, settings, promotion, members
from app.utils.config import get_config

app = FastAPI(title="Invictus BJJ")

# Initialize templates
templates = Jinja2Templates(directory="app/templates")

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")


class SetupMiddleware(BaseHTTPMiddleware):
    """Middleware to redirect to setup page if app is not configured."""

    # Paths that should be accessible without configuration
    ALLOWED_PATHS = [
        '/setup',
        '/settings',
        '/static',
    ]

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Allow setup and static paths without config check
        if any(path.startswith(allowed) for allowed in self.ALLOWED_PATHS):
            return await call_next(request)

        # Check if app is configured
        config = get_config()
        if not config.is_configured():
            return RedirectResponse(url="/setup", status_code=302)

        return await call_next(request)


# Add middleware
app.add_middleware(SetupMiddleware)

# Include setup router first (before other routers)
app.include_router(setup.router, prefix="/setup", tags=["setup"])
app.include_router(settings.router, prefix="/settings", tags=["settings"])

# Include other routers
app.include_router(files.router, prefix="/api/v1/files", tags=["files"])
app.include_router(customers.router, prefix="/api")
app.include_router(billing.router, prefix="/api/v1/billing", tags=["billing"])
app.include_router(attendance.router, prefix="/api/v1/attendance", tags=["attendance"])
app.include_router(main.router, prefix="/api/v1/main", tags=["main"])
app.include_router(payment.router, prefix="/api/v1/payment", tags=["payment"])
app.include_router(overview.router)
app.include_router(enrollment.router, prefix="/api/v1/enrollment", tags=["enrollment"])
app.include_router(handover.router, prefix="/api/v1/payment/handover", tags=["handover"])
app.include_router(promotion.router, prefix="/api/v1/promotion", tags=["promotion"])
app.include_router(members.router, prefix="/members", tags=["members"])


@app.get("/")
async def index(request: Request):
    """Home page."""
    return templates.TemplateResponse("home.html", {"request": request})
