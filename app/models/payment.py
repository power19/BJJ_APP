# app/models/payment.py
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class PaymentStatus(str, Enum):
    PENDING = "pending"           # Initial state after customer payment
    RECEIVED = "received"         # Coach has received payment  
    TRANSFERRED = "transferred"   # Treasurer/head coach has received payment from coach
    COMPLETED = "completed"       # Payment fully processed

class PaymentHandoverRequest(BaseModel):
    payment_id: str
    treasurer_rfid: str           # RFID of treasurer confirming receipt
    handover_notes: Optional[str] = None