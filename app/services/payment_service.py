from datetime import datetime
import json
from typing import Dict, Any, Optional
import uuid

class PaymentService:
    def __init__(self, erp_client):
        self.erp_client = erp_client
        self.active_sessions = {}

    async def process_initial_scan(self, rfid: str) -> Dict[str, Any]:
        """Process initial RFID scan and return customer/family info"""
        try:
            # First try to find the customer directly
            customer = self.erp_client.search_customer_by_name(rfid)
            
            if customer:
                # Check if customer is part of a family group
                family_group = self.erp_client.get_family_group(customer["name"])
                
                if family_group:
                    # If customer is part of family, get primary payer's info
                    primary_payer = self.erp_client.search_customer_by_name(family_group["primary_payer"])
                    
                    return {
                        "session_id": self._create_session(primary_payer, family_group),
                        "customer_type": "family_member",
                        "primary_payer": primary_payer,
                        "family_group": family_group,
                        "scanned_member": customer,
                        "invoices": await self._get_payer_invoices(primary_payer["name"])
                    }
                else:
                    # Customer is not part of family, treat as individual
                    return {
                        "session_id": self._create_session(customer, None),
                        "customer_type": "individual",
                        "customer": customer,
                        "invoices": await self._get_payer_invoices(customer["name"])
                    }
            
            raise ValueError("No customer found for this RFID")
            
        except Exception as e:
            print(f"Error in process_initial_scan: {str(e)}")
            raise

    def _create_session(self, payer: Dict, family_group: Optional[Dict] = None) -> str:
        """Create a new payment session"""
        session_id = str(uuid.uuid4())
        self.active_sessions[session_id] = {
            "payer": payer,
            "family_group": family_group,
            "created_at": datetime.now(),
            "status": "invoice_selection",
            "selected_invoices": [],
            "total_amount": 0
        }
        return session_id

    async def _get_payer_invoices(self, payer_name: str) -> list:
        """Get all unpaid invoices for a payer"""
        transactions = self.erp_client.get_customer_transactions(payer_name)
        
        # Filter for unpaid invoices
        unpaid_invoices = [
            tx for tx in transactions.get("data", [])
            if tx["type"] == "Sales Invoice" 
            and float(tx["data"].get("outstanding_amount", 0)) > 0
        ]
        
        return unpaid_invoices

    def get_session(self, session_id: str) -> Optional[Dict]:
        """Get session data if still valid"""
        session = self.active_sessions.get(session_id)
        if not session:
            return None
            
        # Check if session has expired (30 seconds)
        if (datetime.now() - session["created_at"]).total_seconds() > 30:
            del self.active_sessions[session_id]
            return None
            
        return session