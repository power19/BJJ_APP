# app/services/billing_service.py
from typing import Dict, Any
from datetime import datetime
import json
from ..utils.erp_client import ERPNextClient

class BillingService:
    def __init__(self, erp_client: ERPNextClient):
        self.erp_client = erp_client

    def format_money(self, amount: float) -> str:
        """Format amount with currency"""
        try:
            return f"SRD {float(amount):,.2f}"
        except:
            return "SRD 0.00"

    def format_date(self, date_str: str) -> str:
        """Format date string"""
        try:
            if not date_str:
                return ""
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            return date_obj.strftime('%d %B %Y')
        except:
            return date_str

    def format_address(self, address: str) -> str:
        """Format address string by removing HTML tags and extra whitespace"""
        if not address:
            return "Not provided"
        return address.replace("<br>", ", ").replace("\n", "").strip(", ")

    async def get_customer_billing(self, customer_name: str) -> Dict[str, Any]:
        try:
            print(f"Getting billing info for: {customer_name}")
            
            # Search for customer
            customer = self.erp_client.search_customer_by_name(customer_name)
            if not customer:
                raise Exception(f"Customer '{customer_name}' not found")

            print(f"Found customer: {customer.get('customer_name')}")

            # Get transactions
            transactions_data = self.erp_client.get_customer_transactions(customer["customer_name"])
            print(f"Raw transactions data: {json.dumps(transactions_data, indent=2)}")
            
            # Format customer info
            customer_info = {
                "personal": {
                    "name": customer.get("customer_name", "Not provided"),
                    "email": customer.get("email_id") or "Not provided",
                    "phone": customer.get("mobile_no", "Not provided"),
                    "address": self.format_address(customer.get("primary_address")),
                    "gender": customer.get("gender", "Not provided"),
                    "date_of_birth": customer.get("custom_date_of_birth") or "Not provided"
                },
                "membership": {
                    "belt_rank": customer.get("custom_current_belt_rank") or "Not assigned",
                    "registration_fee": self.format_money(float(customer.get("custom_registration_fee", 0))),
                    "attendance": len(json.loads(customer.get("custom_attendance", "[]"))) if customer.get("custom_attendance") else 0
                }
            }

            # Format transactions
            formatted_transactions = []
            total_amount = 0
            outstanding_amount = 0
            
            # Process all transactions
            for transaction in transactions_data.get("data", []):
                if isinstance(transaction, dict) and "data" in transaction:
                    tx_data = transaction["data"]
                    if transaction["type"] == "Sales Invoice":
                        print(f"Processing invoice: {json.dumps(tx_data, indent=2)}")
                        
                        # Get amounts
                        grand_total = float(tx_data.get("grand_total", 0))
                        outstanding = float(tx_data.get("outstanding_amount", 0))
                        
                        formatted_tx = {
                            "type": "Invoice",
                            "date": self.format_date(tx_data.get("posting_date")),
                            "due_date": self.format_date(tx_data.get("due_date")),
                            "number": tx_data.get("name"),
                            "amount": self.format_money(grand_total),
                            "outstanding": self.format_money(outstanding),
                            "status": tx_data.get("status", "Unknown"),
                            "remarks": tx_data.get("remarks", "")
                        }
                        
                        formatted_transactions.append(formatted_tx)
                        total_amount += grand_total
                        outstanding_amount += outstanding
                        
                        print(f"Processed transaction: {json.dumps(formatted_tx, indent=2)}")

            print(f"Total amount: {total_amount}")
            print(f"Outstanding amount: {outstanding_amount}")

            return {
                "customer": customer_info,
                "billing_summary": {
                    "total_invoices": len(formatted_transactions),
                    "total_amount": self.format_money(total_amount),
                    "outstanding_amount": self.format_money(outstanding_amount)
                },
                "transactions": sorted(formatted_transactions, key=lambda x: x["date"] if x["date"] else "", reverse=True)
            }

        except Exception as e:
            print(f"Error in get_customer_billing: {str(e)}")
            raise Exception(f"Error fetching billing info: {str(e)}")