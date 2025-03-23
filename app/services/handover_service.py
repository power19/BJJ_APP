# app/services/handover_service.py
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import json

from ..models.payment import PaymentStatus, PaymentHandoverRequest
from ..utils.erp_client import ERPNextClient

class HandoverService:
    def __init__(self, erp_client: ERPNextClient):
        self.erp_client = erp_client
        
    async def get_pending_handovers(self) -> List[Dict[str, Any]]:
        """Get all payments received by coaches that haven't been handed over to treasurer"""
        try:
            print("Fetching pending payment handovers")
            
            # Get all Payment Entries that don't have a corresponding Payment Handover
            # First, get all handovers
            handovers_endpoint = f"{self.erp_client.base_url}/api/method/frappe.client.get_list"
            handovers_params = {
                'doctype': 'Payment Handover',
                'fields': '["payment_entry"]',
                'filters': json.dumps({
                    'docstatus': 1  # Only submitted handovers
                })
            }
            
            handovers_response = self.erp_client.session.get(handovers_endpoint, params=handovers_params)
            processed_payments = []
            
            if handovers_response.status_code == 200:
                handovers = handovers_response.json().get('message', [])
                processed_payments = [h.get('payment_entry') for h in handovers if h.get('payment_entry')]
            
            # Now get payments that don't have a handover
            api_endpoint = f"{self.erp_client.base_url}/api/method/frappe.client.get_list"
            params = {
                'doctype': 'Payment Entry',
                'fields': '["*"]',
                'filters': json.dumps({
                    'payment_type': 'Receive',
                    'docstatus': 1,  # Only submitted payments
                    'name': ['not in', processed_payments] if processed_payments else None
                }),
                'order_by': 'creation desc'
            }
            
            response = self.erp_client.session.get(api_endpoint, params=params)
            
            if response.status_code != 200:
                print(f"Error fetching pending handovers: {response.text}")
                return []
                    
            payments = response.json().get('message', [])
            
            # Format payments for display
            formatted_payments = []
            for payment in payments:
                try:
                    # Get coach/staff details
                    staff_user_id = payment.get('authorized_by_staff', payment.get('owner'))
                    staff_name = "Unknown"
                    
                    if staff_user_id:
                        user_response = self.erp_client.session.get(
                            f"{self.erp_client.base_url}/api/resource/User/{staff_user_id}"
                        )
                        if user_response.status_code == 200:
                            user_data = user_response.json().get('data', {})
                            staff_name = user_data.get('full_name')
                    
                    # Get invoice references
                    invoice_refs = []
                    detailed_response = self.erp_client.session.get(
                        f"{self.erp_client.base_url}/api/resource/Payment Entry/{payment.get('name')}"
                    )
                    
                    if detailed_response.status_code == 200:
                        payment_detail = detailed_response.json().get('data', {})
                        for ref in payment_detail.get('references', []):
                            if ref.get('reference_doctype') == 'Sales Invoice':
                                invoice_refs.append(ref.get('reference_name'))
                    
                    formatted_payment = {
                        'payment_id': payment.get('name'),
                        'date': payment.get('posting_date'),
                        'customer_name': payment.get('party'),
                        'amount': float(payment.get('paid_amount', 0)),
                        'received_by': staff_name,
                        'received_by_id': staff_user_id,
                        'received_at': payment.get('creation'),
                        'reference_no': payment.get('reference_no'),
                        'invoices': invoice_refs,
                        'status': 'pending'
                    }
                    
                    formatted_payments.append(formatted_payment)
                    
                except Exception as e:
                    print(f"Error processing payment {payment.get('name')}: {str(e)}")
                    continue
            
            return formatted_payments
            
        except Exception as e:
            print(f"Error in get_pending_handovers: {str(e)}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            return []
    
    async def process_handover(self, handover_request: PaymentHandoverRequest) -> Dict[str, Any]:
        """Process handover from coach to treasurer/head coach"""
        try:
            print(f"Processing handover for payment: {handover_request.payment_id}")
            
            # Verify treasurer/head coach RFID first
            treasurer = self.erp_client.verify_staff_rfid(handover_request.treasurer_rfid)
            if not treasurer.get("verified"):
                return {
                    "success": False,
                    "payment_id": handover_request.payment_id,
                    "status": PaymentStatus.RECEIVED,
                    "message": treasurer.get("error", "Treasurer/head coach authorization failed")
                }
                
            # Verify the staff member has treasurer or head coach role
            treasurer_roles = treasurer.get("roles", [])
            if not any(role in ["Treasurer", "Head Coach", "Accounts User", "System Manager", "Administrator"] 
                    for role in treasurer_roles):
                return {
                    "success": False,
                    "payment_id": handover_request.payment_id,
                    "status": PaymentStatus.RECEIVED,
                    "message": "Only treasurers or head coaches are authorized to confirm payment handovers"
                }
                    
            # Get payment details
            payment_response = self.erp_client.session.get(
                f"{self.erp_client.base_url}/api/resource/Payment Entry/{handover_request.payment_id}"
            )
            
            print(f"Payment response status: {payment_response.status_code}")
            print(f"Payment response content: {payment_response.text[:200]}...")
            
            if payment_response.status_code != 200:
                return {
                    "success": False,
                    "payment_id": handover_request.payment_id,
                    "status": PaymentStatus.RECEIVED,
                    "message": "Payment not found"
                }
                
            payment_data = payment_response.json().get('data', {})
            
            # Get the original owner/staff
            staff_user_id = payment_data.get('authorized_by_staff', payment_data.get('owner'))
            
            # Set handover information
            handover_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            treasurer_id = treasurer.get("user_id")
            treasurer_name = treasurer.get("name")
            
            # Create a Payment Handover record instead of updating the Payment Entry
            handover_data = {
                "doctype": "Payment Handover",
                "payment_entry": handover_request.payment_id,
                "received_by": staff_user_id,
                "received_at": payment_data.get("creation"),
                "transferred_to": treasurer_id,
                "transferred_at": handover_time,
                "handover_notes": handover_request.handover_notes or "",
                "status": "Transferred"
            }
            
            # Create and submit the handover record
            create_response = self.erp_client.session.post(
                f"{self.erp_client.base_url}/api/method/frappe.client.insert",
                json={"doc": handover_data}
            )
            
            print(f"Create handover response status: {create_response.status_code}")
            print(f"Create handover response: {create_response.text}")
            
            if create_response.status_code not in (200, 201):
                return {
                    "success": False,
                    "payment_id": handover_request.payment_id,
                    "status": PaymentStatus.RECEIVED,
                    "message": f"Failed to create handover record: {create_response.text}"
                }
                
            # Get the handover document
            handover_doc = create_response.json().get("message", {})
            handover_name = handover_doc.get("name")
            
            # Submit the handover document
            if handover_name:
                submit_response = self.erp_client.session.post(
                    f"{self.erp_client.base_url}/api/method/frappe.client.submit",
                    json={"doc": handover_doc}
                )
                
                print(f"Submit handover response status: {submit_response.status_code}")
                print(f"Submit handover response: {submit_response.text}")
            
            return {
                "success": True,
                "payment_id": handover_request.payment_id,
                "handover_id": handover_name,
                "status": PaymentStatus.TRANSFERRED,
                "message": f"Payment successfully transferred to {treasurer_name}"
            }
            
        except Exception as e:
            print(f"Error in process_handover: {str(e)}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            return {
                "success": False,
                "payment_id": handover_request.payment_id,
                "status": PaymentStatus.RECEIVED,
                "message": f"Error processing handover: {str(e)}"
            }
        
    async def get_payment_history(self, days: int = 30) -> List[Dict[str, Any]]:
        """Get payment history including handover status"""
        try:
            print(f"Fetching payment history for past {days} days")
            
            # Calculate date range
            from datetime import datetime, timedelta
            past_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
            
            # Get all handovers first regardless of date
            handovers_endpoint = f"{self.erp_client.base_url}/api/method/frappe.client.get_list"
            handovers_params = {
                'doctype': 'Payment Handover',
                'fields': '["*"]',
                'filters': json.dumps({
                    'docstatus': 1  # Only submitted handovers
                })
            }
            
            handovers_response = self.erp_client.session.get(handovers_endpoint, params=handovers_params)
            handovers_by_payment = {}
            payment_ids_with_handovers = []
            
            if handovers_response.status_code == 200:
                handovers = handovers_response.json().get('message', [])
                print(f"Found {len(handovers)} handovers")
                for handover in handovers:
                    payment_id = handover.get('payment_entry')
                    if payment_id:
                        handovers_by_payment[payment_id] = handover
                        payment_ids_with_handovers.append(payment_id)
            else:
                print(f"Error getting handovers: {handovers_response.status_code} - {handovers_response.text}")
            
            # First, try getting recent payments with date filter
            api_endpoint = f"{self.erp_client.base_url}/api/method/frappe.client.get_list"
            params = {
                'doctype': 'Payment Entry',
                'fields': '["*"]',
                'filters': json.dumps({
                    'payment_type': 'Receive',
                    'docstatus': 1,  # Only submitted payments
                    'posting_date': ['>=', past_date]
                }),
                'order_by': 'creation desc'
            }
            
            response = self.erp_client.session.get(api_endpoint, params=params)
            
            if response.status_code != 200:
                print(f"Error fetching payment history: {response.status_code} - {response.text}")
                return []
                    
            payments = response.json().get('message', [])
            print(f"Found {len(payments)} payments with date filter")
            
            # If no payments but we have handovers, try getting payments by ID
            if len(payments) == 0 and payment_ids_with_handovers:
                print(f"No payments with date filter, trying to get payments by ID: {payment_ids_with_handovers}")
                
                # Get payments by ID without date filter
                params = {
                    'doctype': 'Payment Entry',
                    'fields': '["*"]',
                    'filters': json.dumps({
                        'name': ['in', payment_ids_with_handovers]
                    })
                }
                
                response = self.erp_client.session.get(api_endpoint, params=params)
                
                if response.status_code == 200:
                    payments = response.json().get('message', [])
                    print(f"Found {len(payments)} payments by ID")
            
            # Format payments for display
            formatted_payments = []
            for payment in payments:
                try:
                    payment_id = payment.get('name')
                    print(f"Processing payment: {payment_id}")
                    
                    # Get staff who received the payment
                    staff_user_id = payment.get('authorized_by_staff', payment.get('owner'))
                    staff_name = "Unknown"
                    
                    if staff_user_id:
                        user_response = self.erp_client.session.get(
                            f"{self.erp_client.base_url}/api/resource/User/{staff_user_id}"
                        )
                        if user_response.status_code == 200:
                            user_data = user_response.json().get('data', {})
                            staff_name = user_data.get('full_name')
                    
                    # Check if there's a handover record
                    handover = handovers_by_payment.get(payment_id)
                    status = 'transferred' if handover else 'pending'
                    
                    # Get treasurer details if handover exists
                    treasurer_name = "Not transferred"
                    transferred_at = None
                    
                    if handover:
                        transferred_to = handover.get('transferred_to')
                        transferred_at = handover.get('transferred_at')
                        
                        if transferred_to:
                            user_response = self.erp_client.session.get(
                                f"{self.erp_client.base_url}/api/resource/User/{transferred_to}"
                            )
                            if user_response.status_code == 200:
                                user_data = user_response.json().get('data', {})
                                treasurer_name = user_data.get('full_name')
                    
                    # Get invoice references
                    invoice_refs = []
                    detailed_response = self.erp_client.session.get(
                        f"{self.erp_client.base_url}/api/resource/Payment Entry/{payment_id}"
                    )
                    
                    if detailed_response.status_code == 200:
                        payment_detail = detailed_response.json().get('data', {})
                        references = payment_detail.get('references', [])
                        for ref in references:
                            if isinstance(ref, dict) and ref.get('reference_doctype') == 'Sales Invoice':
                                invoice_refs.append(ref.get('reference_name'))
                    
                    formatted_payment = {
                        'payment_id': payment_id,
                        'date': payment.get('posting_date'),
                        'customer_name': payment.get('party'),
                        'amount': float(payment.get('paid_amount', 0)),
                        'received_by': staff_name,
                        'received_by_id': staff_user_id,
                        'received_at': payment.get('creation'),
                        'transferred_to': treasurer_name if handover else "Not transferred",
                        'transferred_at': transferred_at,
                        'reference_no': payment.get('reference_no'),
                        'invoices': invoice_refs,
                        'status': status,
                        'handover_notes': handover.get('handover_notes', '') if handover else '',
                        'handover_id': handover.get('name') if handover else None
                    }
                    
                    formatted_payments.append(formatted_payment)
                    
                except Exception as e:
                    print(f"Error processing payment history for {payment.get('name')}: {str(e)}")
                    import traceback
                    print(f"Traceback: {traceback.format_exc()}")
                    continue
            
            # Also add payments from handovers that weren't found in the payments list
            for payment_id, handover in handovers_by_payment.items():
                if payment_id not in [p.get('payment_id') for p in formatted_payments]:
                    try:
                        print(f"Adding missing payment from handover: {payment_id}")
                        
                        # Get the payment details
                        payment_response = self.erp_client.session.get(
                            f"{self.erp_client.base_url}/api/resource/Payment Entry/{payment_id}"
                        )
                        
                        if payment_response.status_code == 200:
                            payment_data = payment_response.json().get('data', {})
                            
                            # Get staff details
                            staff_user_id = handover.get('received_by')
                            staff_name = "Unknown"
                            
                            if staff_user_id:
                                user_response = self.erp_client.session.get(
                                    f"{self.erp_client.base_url}/api/resource/User/{staff_user_id}"
                                )
                                if user_response.status_code == 200:
                                    user_data = user_response.json().get('data', {})
                                    staff_name = user_data.get('full_name')
                            
                            # Get treasurer details
                            treasurer_id = handover.get('transferred_to')
                            treasurer_name = "Unknown"
                            
                            if treasurer_id:
                                user_response = self.erp_client.session.get(
                                    f"{self.erp_client.base_url}/api/resource/User/{treasurer_id}"
                                )
                                if user_response.status_code == 200:
                                    user_data = user_response.json().get('data', {})
                                    treasurer_name = user_data.get('full_name')
                            
                            # Add payment from handover data
                            formatted_payments.append({
                                'payment_id': payment_id,
                                'date': payment_data.get('posting_date'),
                                'customer_name': payment_data.get('party'),
                                'amount': float(payment_data.get('paid_amount', 0)),
                                'received_by': staff_name,
                                'received_by_id': staff_user_id,
                                'received_at': handover.get('received_at'),
                                'transferred_to': treasurer_name,
                                'transferred_at': handover.get('transferred_at'),
                                'reference_no': payment_data.get('reference_no'),
                                'invoices': [],  # We don't have invoice refs here
                                'status': 'transferred',
                                'handover_notes': handover.get('handover_notes', ''),
                                'handover_id': handover.get('name')
                            })
                    except Exception as e:
                        print(f"Error adding handover-only payment {payment_id}: {str(e)}")
            
            print(f"Returning {len(formatted_payments)} formatted payments for history")
            return formatted_payments
            
        except Exception as e:
            print(f"Error in get_payment_history: {str(e)}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            return []