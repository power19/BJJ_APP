# app/services/billing_service.py
from typing import Dict, Any
from datetime import datetime
import json
from ..utils.erp_client import ERPNextClient

# app/services/billing_service.py

class BillingService:
    def __init__(self, erp_client):
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

    async def get_customer_billing(self, customer_name: str) -> Dict[str, Any]:
        try:
            print(f"Getting billing info for: {customer_name}")
            
            # Search for customer
            customer = self.erp_client.search_customer_by_name(customer_name)
            if not customer:
                raise Exception(f"Customer '{customer_name}' not found")

            print(f"Found customer: {customer.get('customer_name')}")

            # Get transactions with doctype filter for Sales Invoices
            api_endpoint = f"{self.erp_client.base_url}/api/method/frappe.client.get_list"
            params = {
                'doctype': 'Sales Invoice',
                'fields': '["*"]',
                'filters': json.dumps({
                    'customer': customer["name"],
                    'docstatus': 1  # Only submitted invoices
                })
            }
            
            response = self.erp_client.session.get(api_endpoint, params=params)
            if response.status_code != 200:
                raise Exception("Failed to fetch invoices")
                
            invoices = response.json().get('message', [])
            print(f"Found {len(invoices)} invoices")
            
            # Format customer info
            customer_info = {
                "personal": {
                    "name": customer.get("customer_name", "Not provided"),
                    "email": customer.get("email_id") or "Not provided",
                    "phone": customer.get("mobile_no", "Not provided"),
                    "address": customer.get("primary_address") or "Not provided"
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
            
            for invoice in invoices:
                try:
                    grand_total = float(invoice.get("grand_total", 0))
                    outstanding = float(invoice.get("outstanding_amount", 0))
                    
                    formatted_tx = {
                        "type": "Invoice",
                        "date": self.format_date(invoice.get("posting_date")),
                        "due_date": self.format_date(invoice.get("due_date")),
                        "number": invoice.get("name"),
                        "amount": self.format_money(grand_total),
                        "outstanding": self.format_money(outstanding),
                        "status": invoice.get("status", "Unknown"),
                        "remarks": invoice.get("remarks", "")
                    }
                    
                    formatted_transactions.append(formatted_tx)
                    total_amount += grand_total
                    outstanding_amount += outstanding
                    
                    print(f"Processed transaction: {json.dumps(formatted_tx, indent=2)}")
                except Exception as e:
                    print(f"Error processing invoice: {str(e)}")
                    continue

            print(f"Total amount: {total_amount}")
            print(f"Outstanding amount: {outstanding_amount}")

            return {
                "customer": customer_info,
                "billing_summary": {
                    "total_invoices": len(formatted_transactions),
                    "total_amount": self.format_money(total_amount),
                    "outstanding_amount": self.format_money(outstanding_amount)
                },
                "transactions": sorted(formatted_transactions, 
                                    key=lambda x: datetime.strptime(x["due_date"], '%d %B %Y') if x["due_date"] else datetime.min,
                                    reverse=True)
            }

        except Exception as e:
            print(f"Error in get_customer_billing: {str(e)}")
            raise Exception(f"Error fetching billing info: {str(e)}")