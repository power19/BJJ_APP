from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from enum import Enum

class ProgramType(str, Enum):
    BJJ = "bjj"
    NOGI = "nogi"

class BillingCycle(str, Enum):
    DAILY = "daily"
    MONTHLY = "monthly"
    SIX_MONTHS = "six_months"
    YEARLY = "yearly"

class ProgramPricing(BaseModel):
    daily: float
    monthly: float
    six_months: float
    yearly: float

class Program(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    pricing: ProgramPricing

class EnrollmentRequest(BaseModel):
    student_name: str
    email: str
    phone: str
    date_of_birth: str
    program_type: ProgramType
    billing_cycle: BillingCycle
    start_date: str

class EnrollmentResponse(BaseModel):
    customer_id: str
    invoice_id: str
    amount: float
    due_date: str
    message: str