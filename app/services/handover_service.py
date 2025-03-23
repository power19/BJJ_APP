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
            
            # Get all Payment Entries that have been received but not transferred
            api_endpoint = f"{self.erp_client.base_url}/api/method/frappe.client.get_list"
            params = {
                'doctype': 'Payment Entry',
                'fields': '["*"]',
                'filters': json.dumps({
                    'payment_type': 'Receive',
                    'docstatus': 1,  # Submitted payments
                    'custom_handover_status': ['in', ['pending', None, '']],  # Payments not yet transferred
                    'custom_received_by_role': 'Coach'  # Only show payments received by coaches
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
                        'status': payment.get('custom_handover_status', 'pending'),
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
            
            if payment_response.status_code != 200:
                return {
                    "success": False,
                    "payment_id": handover_request.payment_id,
                    "status": PaymentStatus.RECEIVED,
                    "message": "Payment not found"
                }
                
            payment_data = payment_response.json().get('data', {})
            
            # Set handover information
            handover_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            treasurer_id = treasurer.get("user_id")
            treasurer_name = treasurer.get("name")
            
            # Update payment entry with handover details
            update_data = {
                "custom_handover_status": "transferred",
                "custom_transferred_to": treasurer_id,
                "custom_transferred_at": handover_time,
                "custom_handover_notes": handover_request.handover_notes or ""
            }
            
            # Append to remarks for visibility
            current_remarks = payment_data.get("remarks") or ""
            new_remarks = f"{current_remarks}\n[{handover_time}] Payment transferred to {treasurer_name}"
            update_data["remarks"] = new_remarks
            
            # Update the payment entry
            update_response = self.erp_client.session.put(
                f"{self.erp_client.base_url}/api/resource/Payment Entry/{handover_request.payment_id}",
                json=update_data
            )
            
            if update_response.status_code not in (200, 202):
                return {
                    "success": False,
                    "payment_id": handover_request.payment_id,
                    "status": PaymentStatus.RECEIVED,
                    "message": f"Failed to update payment status: {update_response.text}"
                }
                
            return {
                "success": True,
                "payment_id": handover_request.payment_id,
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
            past_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
            
            api_endpoint = f"{self.erp_client.base_url}/api/method/frappe.client.get_list"
            params = {
                'doctype': 'Payment Entry',
                'fields': '["*"]',
                'filters': json.dumps({
                    'payment_type': 'Receive',
                    'docstatus': 1,  # Submitted payments
                    'posting_date': ['>=', past_date]
                }),
                'order_by': 'creation desc'
            }
            
            response = self.erp_client.session.get(api_endpoint, params=params)
            
            if response.status_code != 200:
                print(f"Error fetching payment history: {response.text}")
                return []
                
            payments = response.json().get('message', [])
            
            # Format payments for display
            formatted_payments = []
            for payment in payments:
                try:
                    # Get detailed payment information
                    detail_response = self.erp_client.session.get(
                        f"{self.erp_client.base_url}/api/resource/Payment Entry/{payment.get('name')}"
                    )
                    
                    if detail_response.status_code != 200:
                        continue
                        
                    payment_detail = detail_response.json().get('data', {})
                    
                    # Get staff/coach details
                    staff_user_id = payment_detail.get('authorized_by_staff', payment_detail.get('owner'))
                    staff_name = "Unknown"
                    
                    if staff_user_id:
                        user_response = self.erp_client.session.get(
                            f"{self.erp_client.base_url}/api/resource/User/{staff_user_id}"
                        )
                        if user_response.status_code == 200:
                            user_data = user_response.json().get('data', {})
                            staff_name = user_data.get('full_name')
                    
                    # Get treasurer details if handover has occurred
                    treasurer_id = payment_detail.get('custom_transferred_to')
                    treasurer_name = "Not transferred"
                    
                    if treasurer_id:
                        user_response = self.erp_client.session.get(
                            f"{self.erp_client.base_url}/api/resource/User/{treasurer_id}"
                        )
                        if user_response.status_code == 200:
                            user_data = user_response.json().get('data', {})
                            treasurer_name = user_data.get('full_name')
                    
                    # Get invoice references
                    invoice_refs = []
                    for ref in payment_detail.get('references', []):
                        if ref.get('reference_doctype') == 'Sales Invoice':
                            invoice_refs.append(ref.get('reference_name'))
                    
                    # Determine status
                    status = payment_detail.get('custom_handover_status', 'pending')
                    if not status:
                        status = 'pending'
                    
                    formatted_payment = {
                        'payment_id': payment.get('name'),
                        'date': payment.get('posting_date'),
                        'customer_name': payment.get('party'),
                        'amount': float(payment.get('paid_amount', 0)),
                        'received_by': staff_name,
                        'received_at': payment.get('creation'),
                        'transferred_to': treasurer_name if treasurer_id else "N/A",
                        'transferred_at': payment_detail.get('custom_transferred_at'),
                        'reference_no': payment.get('reference_no'),
                        'invoices': invoice_refs,
                        'status': status,
                        'handover_notes': payment_detail.get('custom_handover_notes', '')
                    }
                    
                    formatted_payments.append(formatted_payment)
                    
                except Exception as e:
                    print(f"Error processing payment history for {payment.get('name')}: {str(e)}")
                    continue
            
            return formatted_payments
            
        except Exception as e:
            print(f"Error in get_payment_history: {str(e)}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            return []