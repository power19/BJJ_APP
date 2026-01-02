# main.py
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware
from contextlib import asynccontextmanager

from app.routes import billing, attendance, customers, files, main, payment, overview, enrollment, handover, setup, settings, promotion, members
from app.utils.config import get_config

# Scheduler for automatic billing
scheduler = None

def run_daily_billing():
    """Run the daily billing cycle."""
    try:
        from app.services.auto_billing import get_billing_service
        billing_service = get_billing_service()
        result = billing_service.run_billing_cycle()
        print(f"[Auto-Billing] {result.get('message', 'Completed')}")
        if result.get('errors'):
            print(f"[Auto-Billing] Errors: {result['errors']}")
    except Exception as e:
        print(f"[Auto-Billing] Error: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    global scheduler

    # Start scheduler on startup
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.cron import CronTrigger

        scheduler = BackgroundScheduler()
        # Run billing daily at 6:00 AM
        scheduler.add_job(
            run_daily_billing,
            CronTrigger(hour=6, minute=0),
            id='daily_billing',
            name='Daily Membership Billing',
            replace_existing=True
        )
        scheduler.start()
        print("[Scheduler] Auto-billing scheduler started (runs daily at 6:00 AM)")
    except ImportError:
        print("[Scheduler] APScheduler not installed, auto-billing disabled")
    except Exception as e:
        print(f"[Scheduler] Failed to start: {e}")

    yield

    # Shutdown scheduler
    if scheduler:
        scheduler.shutdown()
        print("[Scheduler] Shutdown complete")


app = FastAPI(title="Invictus BJJ", lifespan=lifespan)

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

# Clean URL routes for pages
app.include_router(members.router, prefix="/members", tags=["members"])
app.include_router(attendance.router, prefix="/checkin", tags=["checkin"])
app.include_router(payment.router, prefix="/payment", tags=["payment-pages"])
app.include_router(handover.router, prefix="/handover", tags=["handover-pages"])
app.include_router(promotion.router, prefix="/promotion", tags=["promotion-pages"])

# API routes (keep for backwards compatibility and API calls)
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


@app.get("/")
async def index(request: Request):
    """Home page."""
    return templates.TemplateResponse("home.html", {"request": request})
