# app/services/payment_service.py
from datetime import datetime
import json
from typing import Dict, Any, Optional, List
import uuid
from ..utils.session_store import session_store

class PaymentService:
    def __init__(self, erp_client):
        self.erp_client = erp_client

    async def _get_payer_invoices(self, payer_name: str) -> List[Dict[str, Any]]:
        """Get all unpaid invoices for a payer"""
        try:
            print(f"\nGetting invoices for payer: {payer_name}")
            
            # Use the client's API method to get invoices
            api_endpoint = f"{self.erp_client.base_url}/api/method/frappe.client.get_list"
            params = {
                'doctype': 'Sales Invoice',
                'fields': '["*"]',
                'filters': json.dumps({
                    'customer': payer_name,
                    'docstatus': 1,  # Only submitted invoices
                    'status': ['in', ['Unpaid', 'Overdue']],  # Get both unpaid and overdue invoices
                    'outstanding_amount': ['>', 0]  # Only invoices with remaining balance
                })
            }
            
            response = self.erp_client.session.get(api_endpoint, params=params)
            print(f"Invoice response status: {response.status_code}")
            
            if response.status_code == 200:
                invoices = response.json().get('message', [])
                print(f"Found {len(invoices)} invoices")
                
                formatted_invoices = []
                for invoice in invoices:
                    try:
                        # Initialize the base invoice data
                        formatted_invoice = {
                            "type": "Sales Invoice",
                            "data": {
                                "name": invoice.get("name"),
                                "posting_date": invoice.get("posting_date"),
                                "due_date": invoice.get("due_date"),
                                "outstanding_amount": float(invoice.get("outstanding_amount", 0)),
                                "grand_total": float(invoice.get("grand_total", 0)),
                                "status": invoice.get("status", "Unknown"),
                                "customer_name": invoice.get("customer_name"),
                                "subscription": None,
                                "from_date": None,
                                "to_date": None,
                                "items": []  # Initialize empty items list
                            }
                        }

                        # Get detailed invoice information
                        detail_response = self.erp_client.session.get(
                            f"{self.erp_client.base_url}/api/resource/Sales Invoice/{invoice.get('name')}"
                        )
                        
                        if detail_response.status_code == 200:
                            invoice_detail = detail_response.json().get('data', {})
                            
                            # Update with subscription details if available
                            formatted_invoice["data"]["subscription"] = invoice_detail.get("subscription")
                            formatted_invoice["data"]["from_date"] = invoice_detail.get("from_date")
                            formatted_invoice["data"]["to_date"] = invoice_detail.get("to_date")
                            
                            # Create item description
                            item_description = "Monthly Subscription"
                            if invoice_detail.get('subscription'):
                                item_description += f" - {invoice_detail.get('subscription')}"
                            if invoice_detail.get('from_date') and invoice_detail.get('to_date'):
                                item_description += f"\n({invoice_detail.get('from_date')} to {invoice_detail.get('to_date')})"
                            
                            # Add item to items list
                            formatted_invoice["data"]["items"].append({
                                "description": item_description,
                                "amount": float(invoice_detail.get("grand_total", 0))
                            })
                        
                        formatted_invoices.append(formatted_invoice)
                        print(f"Processed invoice {formatted_invoice['data']['name']}")
                        
                    except Exception as e:
                        print(f"Error processing invoice {invoice.get('name')}: {str(e)}")
                        continue
                
                return formatted_invoices
                
            print(f"No invoices found or error in response: {response.text}")
            return []
            
        except Exception as e:
            print(f"Error getting payer invoices: {str(e)}")
            return []

    async def process_initial_scan(self, rfid: str) -> Dict[str, Any]:
        """Process initial RFID scan and return customer/family info"""
        try:
            print(f"Processing RFID scan: {rfid}")
            # First try to find the customer by RFID
            customer_result = self.erp_client.search_customer(rfid)
            
            if not customer_result or not customer_result.get("customer"):
                print(f"No customer found with RFID: {rfid}")
                raise ValueError(f"No customer found with RFID card: {rfid}")
            
            customer = customer_result["customer"]
            print(f"Found customer: {customer.get('customer_name')}")
            
            # Check if customer is part of a family group
            family_group = self.erp_client.get_family_group(customer["name"])
            
            if family_group:
                print(f"Customer is part of family group: {family_group.get('name')}")
                # If customer is part of family, get primary payer's info
                primary_payer = self.erp_client.search_customer_by_name(family_group["primary_payer"])
                
                if not primary_payer:
                    raise ValueError(f"Could not find primary payer: {family_group['primary_payer']}")
                
                print(f"Primary payer: {primary_payer.get('customer_name')}")
                invoices = await self._get_payer_invoices(primary_payer["name"])
                
                session_id = str(uuid.uuid4())
                session_data = {
                    "payer": primary_payer,
                    "family_group": family_group,
                    "scanned_member": customer,
                    "customer_type": "family_member",
                    "invoices": invoices,
                    "total_amount": 0,
                    "selected_invoices": []
                }
                session_store.create_session(session_id, session_data)
                
                return {
                    "session_id": session_id,
                    "customer_type": "family_member",
                    "primary_payer": primary_payer,
                    "family_group": family_group,
                    "scanned_member": customer,
                    "invoices": invoices
                }
            else:
                print("Customer is individual (not part of family group)")
                # Customer is not part of family, treat as individual
                invoices = await self._get_payer_invoices(customer["name"])
                
                session_id = str(uuid.uuid4())
                session_data = {
                    "payer": customer,
                    "family_group": None,
                    "customer_type": "individual",
                    "invoices": invoices,
                    "total_amount": 0,
                    "selected_invoices": []
                }
                session_store.create_session(session_id, session_data)
                
                return {
                    "session_id": session_id,
                    "customer_type": "individual",
                    "customer": customer,
                    "invoices": invoices
                }
            
        except Exception as e:
            print(f"Error in process_initial_scan: {str(e)}")
            raise

    def get_session(self, session_id: str) -> Optional[Dict]:
        """Get session data if still valid"""
        return session_store.get_session(session_id)

    def end_session(self, session_id: str) -> None:
        """End a payment session"""
        session_store.delete_session(session_id)

    async def process_payment(self, payment_request: Any) -> Dict[str, Any]:
        """Process payment for selected invoices"""
        try:
            print(f"\nProcessing payment request: {payment_request}")

            # First verify staff authorization
            if not hasattr(payment_request, 'staff_rfid'):
                raise ValueError("Staff authorization required")

            staff_result = self.erp_client.verify_staff_rfid(payment_request.staff_rfid)
            if not staff_result.get("verified"):
                raise ValueError(staff_result.get("error", "Staff authorization failed"))

            # Check if staff is treasurer/head coach
            staff_roles = staff_result.get("roles", [])
            staff_is_treasurer = any(role in ["Treasurer", "Head Coach", "Accounts User", "System Manager", "Administrator"] 
                                    for role in staff_roles)

            # Get staff email (user ID) instead of display name
            staff_user_id = staff_result.get("user_id")  # This should be their email/user ID
            staff_name = staff_result.get("name")  # This is their display name
            auth_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Validate total amount matches sum of invoice amounts
            total_calculated = sum(float(amount) for amount in payment_request.invoice_amounts.values())
            if abs(total_calculated - payment_request.total_amount) > 0.01:
                raise ValueError(f"Total amount mismatch: {total_calculated} != {payment_request.total_amount}")

            # Create payment entry
            payment_data = {
                "doctype": "Payment Entry",
                "naming_series": "ACC-PAY-.YYYY.-",
                "payment_type": "Receive",
                "posting_date": datetime.now().strftime('%Y-%m-%d'),
                "company": "INVICTUS BJJ",
                "mode_of_payment": "Cash",
                "party_type": "Customer",
                "party": payment_request.customer_name,
                "party_name": payment_request.customer_name,
                "paid_from": "Debtors - IB",
                "paid_from_account_type": "Receivable",
                "paid_from_account_currency": "SRD",
                "paid_to": "Cash - IB",
                "paid_to_account_type": "Cash",
                "paid_to_account_currency": "SRD",
                "paid_amount": payment_request.total_amount,
                "source_exchange_rate": 1,
                "base_paid_amount": payment_request.total_amount,
                "received_amount": payment_request.total_amount,
                "target_exchange_rate": 1,
                "base_received_amount": payment_request.total_amount,
                "reference_no": f"PMT-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}",
                "reference_date": datetime.now().strftime('%Y-%m-%d'),
                # Set the custom fields for staff authorization
                "authorized_by_staff": staff_user_id,  # This should be the email/user ID
                "authorization_time": auth_time,
                "staff_notes": f"Payment processed by {staff_name}",
                "custom_handover_status": "transferred" if staff_is_treasurer else "pending",
                "custom_received_by_role": "Treasurer" if staff_is_treasurer else "Coach",
                               
                # Set the ownership fields
                "owner": staff_user_id,
                "modified_by": staff_user_id,
                # Add to remarks for visibility
                "remarks": (
                    f"Payment processed by {staff_name} on {auth_time}\n"
                    f"Amount SRD {payment_request.total_amount} received from {payment_request.customer_name}"
                )
                }

            # Add references to invoices
            # Update references if needed
            if payment_request.invoices:
                references = []
                for invoice_id in payment_request.invoices:
                    amount = payment_request.invoice_amounts[invoice_id]
                    if amount > 0:
                        references.append({
                            "reference_doctype": "Sales Invoice",
                            "reference_name": invoice_id,
                            "allocated_amount": amount
                        })
                payment_data["references"] = references
            
            print(f"Creating payment entry: {json.dumps(payment_data, indent=2)}")

            # Create payment entry
            response = self.erp_client.session.post(
                f"{self.erp_client.base_url}/api/method/frappe.client.insert",
                json={"doc": payment_data}
            )

            if response.status_code not in (200, 201):
                print(f"Error creating payment: {response.text}")
                raise Exception(f"Failed to create payment: {response.text}")

            payment_entry = response.json()
            payment_name = payment_entry.get("message", {}).get("name")
            
            if not payment_name:
                raise ValueError("No payment entry name received")
            
            print(f"Created payment entry: {payment_name}")

            # Get the full document before submitting
            doc_response = self.erp_client.session.get(
                f"{self.erp_client.base_url}/api/resource/Payment Entry/{payment_name}"
            )
            
            if doc_response.status_code != 200:
                raise ValueError("Failed to get payment document")
                
            doc_data = doc_response.json().get("data", {})

            # Submit the payment
            submit_response = self.erp_client.session.post(
                f"{self.erp_client.base_url}/api/method/frappe.client.submit",
                json={"doc": doc_data}
            )

            if submit_response.status_code not in (200, 201):
                print(f"Error submitting payment: {submit_response.text}")
                
                # Try to clean up the draft payment
                try:
                    cancel_response = self.erp_client.session.delete(
                        f"{self.erp_client.base_url}/api/resource/Payment Entry/{payment_name}"
                    )
                    print(f"Cancelled draft payment: {cancel_response.status_code}")
                except Exception as e:
                    print(f"Failed to cancel draft payment: {str(e)}")
                    
                raise Exception(f"Failed to submit payment: {submit_response.text}")

            print(f"Successfully submitted payment: {payment_name}")
            return {
                "status": "success",
                "payment_id": payment_name,
                "amount": payment_request.total_amount,
                "currency": "SRD"
            }

        except Exception as e:
            print(f"Payment processing error: {str(e)}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            raise