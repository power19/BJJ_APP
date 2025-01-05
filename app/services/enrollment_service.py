from datetime import datetime, timedelta
from typing import Dict, Any
import json
from ..models.enrollment import EnrollmentRequest, ProgramType, BillingCycle
from ..utils.erp_client import ERPNextClient

class EnrollmentService:
    def __init__(self, erp_client: ERPNextClient):
        self.erp_client = erp_client
        self.program_prices = {
            ProgramType.BJJ: {
                BillingCycle.DAILY: 50.0,
                BillingCycle.MONTHLY: 400.0,
                BillingCycle.SIX_MONTHS: 2000.0,
                BillingCycle.YEARLY: 3600.0
            },
            ProgramType.NOGI: {
                BillingCycle.DAILY: 50.0,
                BillingCycle.MONTHLY: 400.0,
                BillingCycle.SIX_MONTHS: 2000.0,
                BillingCycle.YEARLY: 3600.0
            }
        }

    def calculate_due_date(self, start_date: str, billing_cycle: BillingCycle) -> str:
        """Calculate invoice due date based on billing cycle."""
        start = datetime.strptime(start_date, '%Y-%m-%d')
        
        if billing_cycle == BillingCycle.DAILY:
            return start_date
        elif billing_cycle == BillingCycle.MONTHLY:
            due_date = start + timedelta(days=30)
        elif billing_cycle == BillingCycle.SIX_MONTHS:
            due_date = start + timedelta(days=180)
        else:  # yearly
            due_date = start + timedelta(days=365)
            
        return due_date.strftime('%Y-%m-%d')

    def get_program_amount(self, program_type: ProgramType, billing_cycle: BillingCycle) -> float:
        """Get program amount based on type and billing cycle."""
        return self.program_prices[program_type][billing_cycle]

    async def create_enrollment(self, enrollment: EnrollmentRequest) -> Dict[str, Any]:
        """Create customer and invoice in ERPNext."""
        try:
            # Create customer
            customer_data = {
                "doctype": "Customer",
                "customer_name": enrollment.student_name,
                "customer_type": "Individual",
                "customer_group": "Individual",
                "territory": "Suriname",
                "email_id": enrollment.email,
                "mobile_no": enrollment.phone,
                "custom_date_of_birth": enrollment.date_of_birth,
                "custom_current_belt_rank": "White Belt"
            }

            response = self.erp_client.session.post(
                f"{self.erp_client.base_url}/api/method/frappe.client.insert",
                json={"doc": customer_data}
            )
            
            if response.status_code not in (200, 201):
                raise Exception(f"Failed to create customer: {response.text}")

            customer = response.json().get("message", {})
            
            # Calculate amount and due date
            amount = self.get_program_amount(enrollment.program_type, enrollment.billing_cycle)
            due_date = self.calculate_due_date(enrollment.start_date, enrollment.billing_cycle)

            # Create invoice
            invoice_data = {
                "doctype": "Sales Invoice",
                "customer": customer.get("name"),
                "posting_date": enrollment.start_date,
                "due_date": due_date,
                "items": [{
                    "item_code": f"{enrollment.program_type.value.upper()}_PROGRAM",
                    "qty": 1,
                    "rate": amount,
                    "description": f"{enrollment.program_type.value.upper()} Program - {enrollment.billing_cycle.value} subscription"
                }]
            }

            invoice_response = self.erp_client.session.post(
                f"{self.erp_client.base_url}/api/method/frappe.client.insert",
                json={"doc": invoice_data}
            )

            if invoice_response.status_code not in (200, 201):
                raise Exception(f"Failed to create invoice: {invoice_response.text}")

            invoice = invoice_response.json().get("message", {})

            # Submit the invoice
            submit_response = self.erp_client.session.post(
                f"{self.erp_client.base_url}/api/method/frappe.client.submit",
                json={"doc": invoice}
            )

            if submit_response.status_code not in (200, 201):
                raise Exception(f"Failed to submit invoice: {submit_response.text}")

            return {
                "customer_id": customer.get("name"),
                "invoice_id": invoice.get("name"),
                "amount": amount,
                "due_date": due_date,
                "message": "Enrollment completed successfully"
            }

        except Exception as e:
            print(f"Error in enrollment: {str(e)}")
            raise