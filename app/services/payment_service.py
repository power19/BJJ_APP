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
            transactions = self.erp_client.get_customer_transactions(payer_name)
            
            # Extract transactions from the response
            invoices = transactions.get("message", [])
            if not isinstance(invoices, list):
                print("No valid invoices found")
                return []
                
            print(f"Found {len(invoices)} total invoices in response")
            
            # Filter for unpaid invoices
            unpaid_invoices = []
            for invoice in invoices:
                if not isinstance(invoice, dict):
                    continue
                
                try:
                    outstanding = float(invoice.get("outstanding_amount", 0))
                    print(f"\nChecking invoice {invoice.get('name')}:")
                    print(f"Outstanding amount: {outstanding}")
                    print(f"Status: {invoice.get('status')}")
                    
                    # Only include invoices with outstanding amount
                    if outstanding > 0:
                        print(f"Found unpaid invoice: {invoice.get('name')} - Amount: {outstanding}")
                        invoice_data = {
                            "type": "Sales Invoice",
                            "data": {
                                "name": invoice.get("name"),
                                "posting_date": invoice.get("posting_date"),
                                "due_date": invoice.get("due_date"),
                                "outstanding_amount": outstanding,
                                "grand_total": float(invoice.get("grand_total", 0)),
                                "status": invoice.get("status", "Unknown"),
                                "customer_name": invoice.get("customer_name"),
                                "subscription": invoice.get("subscription"),
                                "from_date": invoice.get("from_date"),
                                "to_date": invoice.get("to_date"),
                                "items": []
                            }
                        }
                        
                        # Add subscription item
                        item_description = "Monthly Subscription"
                        if invoice.get('subscription'):
                            item_description += f" - {invoice.get('subscription')}"
                        if invoice.get('from_date') and invoice.get('to_date'):
                            item_description += f"\n({invoice.get('from_date')} to {invoice.get('to_date')})"
                            
                        invoice_data["data"]["items"].append({
                            "description": item_description,
                            "amount": float(invoice.get("grand_total", 0))
                        })
                        
                        unpaid_invoices.append(invoice_data)
                        
                except (ValueError, TypeError) as e:
                    print(f"Error processing invoice {invoice.get('name')}: {str(e)}")
                    continue
                    
            print(f"\nFound {len(unpaid_invoices)} unpaid invoices after filtering")
            for inv in unpaid_invoices:
                print(f"- Invoice {inv['data']['name']}: SRD {inv['data']['outstanding_amount']}")
                
            return unpaid_invoices
            
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
            
            # Validate total amount matches sum of invoice amounts
            total_calculated = sum(float(amount) for amount in payment_request.invoice_amounts.values())
            if abs(total_calculated - payment_request.total_amount) > 0.01:  # Allow for small float rounding differences
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
                "reference_date": datetime.now().strftime('%Y-%m-%d')
            }

            # Add references to invoices
            references = []
            for invoice_id in payment_request.invoices:
                amount = payment_request.invoice_amounts[invoice_id]
                if amount > 0:
                    references.append({
                        "reference_doctype": "Sales Invoice",
                        "reference_name": invoice_id,
                        "allocated_amount": amount
                    })
                    
            if not references:
                raise ValueError("No valid invoice references found")
                
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

            # Submit the payment
            submit_response = self.erp_client.session.post(
                f"{self.erp_client.base_url}/api/method/frappe.client.submit",
                json={"doc": payment_entry.get("message")}
            )

            if submit_response.status_code not in (200, 201):
                print(f"Error submitting payment: {submit_response.text}")
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