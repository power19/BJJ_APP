from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class Customer(BaseModel):
    id: int
    name: str
    email: str
    phone: Optional[str] = None
    created_at: datetime = datetime.now()

class BillingInfo(BaseModel):
    customer_id: int
    amount: float
    due_date: datetime
    status: str
    description: Optional[str] = None