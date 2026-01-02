# app/services/auto_billing.py
"""
Auto-billing service for recurring membership invoices.
Generates invoices for members with recurring memberships on their billing date.
"""
import requests
from datetime import date, timedelta
from typing import Dict, List, Tuple, Optional
from dateutil.relativedelta import relativedelta

from ..utils.config import get_config


class AutoBillingService:
    """Service for automatic invoice generation."""

    def __init__(self):
        self._url = None
        self._headers = None
        self._company = None

    def _setup_connection(self) -> bool:
        """Setup ERPNext connection."""
        config = get_config()
        if not config.is_configured():
            return False

        erp_config = config.get_erpnext_config()
        self._url = erp_config.get('url', '')
        api_key = erp_config.get('api_key', '')
        api_secret = erp_config.get('api_secret', '')

        self._headers = {
            'Authorization': f'token {api_key}:{api_secret}',
            'Content-Type': 'application/json'
        }

        self._company = config.get_company()

        # If company not configured, try to fetch from ERPNext
        if not self._company:
            try:
                resp = requests.get(
                    f"{self._url}/api/resource/Company",
                    headers=self._headers,
                    params={"fields": '["name"]', "limit_page_length": 1},
                    timeout=10
                )
                if resp.status_code == 200:
                    companies = resp.json().get("data", [])
                    if companies:
                        self._company = companies[0].get("name")
                        print(f"[Auto-Billing] Using company: {self._company}")
            except Exception as e:
                print(f"[Auto-Billing] Could not fetch company: {e}")

        return True

    def get_members_due_for_billing(self) -> List[Dict]:
        """
        Get all members with recurring memberships due for billing.
        Returns members where next_billing_date <= today and auto_invoice is enabled.
        """
        if not self._setup_connection():
            return []

        today = date.today().isoformat()

        try:
            response = requests.get(
                f"{self._url}/api/resource/Gym Member",
                headers=self._headers,
                params={
                    "filters": f'[["next_billing_date", "<=", "{today}"], ["auto_invoice", "=", 1], ["status", "=", "Active"]]',
                    "fields": '["name", "full_name", "email", "phone", "current_membership_type", "next_billing_date", "customer"]',
                    "limit_page_length": 500
                },
                timeout=15
            )

            if response.status_code == 200:
                return response.json().get("data", [])
            return []
        except Exception as e:
            print(f"Error fetching members due for billing: {e}")
            return []

    def get_membership_type_details(self, membership_type: str) -> Optional[Dict]:
        """Get membership type details including price and duration."""
        if not self._url:
            return None

        try:
            response = requests.get(
                f"{self._url}/api/resource/Membership Type/{membership_type}",
                headers=self._headers,
                timeout=10
            )

            if response.status_code == 200:
                return response.json().get("data", {})
            return None
        except Exception as e:
            print(f"Error fetching membership type: {e}")
            return None

    def create_sales_invoice(self, member: Dict, membership_type: Dict) -> Tuple[bool, str, Optional[str]]:
        """
        Create a Sales Invoice in ERPNext for a member.
        Returns (success, message, invoice_name).
        """
        if not self._url:
            return False, "Not connected to ERPNext", None

        try:
            # Get or create customer link
            customer_name = member.get("customer")
            if not customer_name:
                # Create a customer for this member
                customer_name = self._ensure_customer_exists(member)
                if not customer_name:
                    return False, "Could not create customer record", None

            # Ensure item exists for this membership type
            item_code = self._ensure_item_exists(membership_type)
            if not item_code:
                return False, "Could not create item for membership", None

            # Calculate due date (usually immediate or within a few days)
            posting_date = date.today().isoformat()
            due_date = (date.today() + timedelta(days=7)).isoformat()

            # Build invoice data - minimal required fields
            invoice_data = {
                "doctype": "Sales Invoice",
                "customer": customer_name,
                "posting_date": posting_date,
                "due_date": due_date,
                "company": self._company,
                "items": [
                    {
                        "item_code": item_code,
                        "qty": 1,
                        "rate": float(membership_type.get("price", 0)),
                        "description": f"Membership: {membership_type.get('membership_name')} for {member.get('full_name')}"
                    }
                ]
            }

            # Create the invoice
            response = requests.post(
                f"{self._url}/api/resource/Sales Invoice",
                headers=self._headers,
                json=invoice_data,
                timeout=15
            )

            if response.status_code in [200, 201]:
                result = response.json()
                invoice_name = result.get("data", {}).get("name")

                # Submit the invoice using run_doc_method
                submit_response = requests.post(
                    f"{self._url}/api/method/run_doc_method",
                    headers=self._headers,
                    json={
                        "dt": "Sales Invoice",
                        "dn": invoice_name,
                        "method": "submit"
                    },
                    timeout=10
                )

                if submit_response.status_code == 200:
                    return True, f"Invoice {invoice_name} created and submitted", invoice_name
                else:
                    # Try frappe.client.submit with full doc fetch
                    get_doc = requests.get(
                        f"{self._url}/api/resource/Sales Invoice/{invoice_name}",
                        headers=self._headers,
                        timeout=10
                    )
                    if get_doc.status_code == 200:
                        doc = get_doc.json().get("data", {})
                        doc["docstatus"] = 1
                        submit_response2 = requests.post(
                            f"{self._url}/api/method/frappe.client.submit",
                            headers=self._headers,
                            json={"doc": doc},
                            timeout=10
                        )
                        if submit_response2.status_code == 200:
                            return True, f"Invoice {invoice_name} created and submitted", invoice_name

                    print(f"[Auto-Billing] Submit failed: {submit_response.text[:200]}")
                    return True, f"Invoice {invoice_name} created (draft - submit failed)", invoice_name
            else:
                # Get full error message
                try:
                    error_data = response.json()
                    if "exception" in error_data:
                        error = error_data["exception"]
                    elif "exc" in error_data:
                        error = error_data["exc"]
                    elif "_server_messages" in error_data:
                        import json as json_lib
                        msgs = json_lib.loads(error_data["_server_messages"])
                        error = " | ".join([json_lib.loads(m).get("message", m) if m.startswith("{") else m for m in msgs])
                    else:
                        error = str(error_data)
                except:
                    error = response.text

                print(f"[Auto-Billing] Invoice creation failed for {member.get('full_name')}: {error[:1000]}")
                return False, f"Failed to create invoice: {error[:200]}", None

        except Exception as e:
            print(f"[Auto-Billing] Exception: {e}")
            return False, f"Error creating invoice: {str(e)}", None

    def _ensure_item_exists(self, membership_type: Dict) -> Optional[str]:
        """Ensure an Item exists for this membership type, create if needed."""
        item_name = membership_type.get("membership_name", "Membership")

        try:
            # Check if item exists
            response = requests.get(
                f"{self._url}/api/resource/Item",
                headers=self._headers,
                params={
                    "filters": f'[["item_name", "=", "{item_name}"]]',
                    "fields": '["name", "item_code"]'
                },
                timeout=10
            )

            if response.status_code == 200:
                items = response.json().get("data", [])
                if items:
                    return items[0].get("name") or items[0].get("item_code")

            # Create the item
            item_data = {
                "doctype": "Item",
                "item_code": item_name,
                "item_name": item_name,
                "item_group": "Services",
                "stock_uom": "Nos",
                "is_stock_item": 0,
                "is_sales_item": 1,
                "is_service_item": 1,
                "description": f"Gym Membership: {item_name}"
            }

            create_response = requests.post(
                f"{self._url}/api/resource/Item",
                headers=self._headers,
                json=item_data,
                timeout=10
            )

            if create_response.status_code in [200, 201]:
                return item_name
            else:
                # Try with different item_group if Services doesn't exist
                item_data["item_group"] = "All Item Groups"
                create_response = requests.post(
                    f"{self._url}/api/resource/Item",
                    headers=self._headers,
                    json=item_data,
                    timeout=10
                )
                if create_response.status_code in [200, 201]:
                    return item_name

            print(f"[Auto-Billing] Failed to create item: {create_response.text[:200]}")
            return None

        except Exception as e:
            print(f"[Auto-Billing] Error ensuring item exists: {e}")
            return None

    def _ensure_customer_exists(self, member: Dict) -> Optional[str]:
        """Ensure a customer record exists for the member and return customer name."""
        try:
            # Check if customer already exists by member name
            member_name = member.get("full_name", "")
            response = requests.get(
                f"{self._url}/api/resource/Customer",
                headers=self._headers,
                params={
                    "filters": f'[["customer_name", "=", "{member_name}"]]',
                    "fields": '["name"]'
                },
                timeout=10
            )

            if response.status_code == 200:
                customers = response.json().get("data", [])
                if customers:
                    customer_name = customers[0].get("name")
                    # Update member with customer link
                    self._update_member_customer_link(member.get("name"), customer_name)
                    return customer_name

            # Create new customer
            customer_data = {
                "doctype": "Customer",
                "customer_name": member_name,
                "customer_type": "Individual",
                "customer_group": "Individual",
                "territory": "All Territories"
            }

            if member.get("email"):
                customer_data["email_id"] = member.get("email")
            if member.get("phone"):
                customer_data["mobile_no"] = member.get("phone")

            create_response = requests.post(
                f"{self._url}/api/resource/Customer",
                headers=self._headers,
                json=customer_data,
                timeout=10
            )

            if create_response.status_code in [200, 201]:
                customer_name = create_response.json().get("data", {}).get("name")
                # Update member with customer link
                self._update_member_customer_link(member.get("name"), customer_name)
                return customer_name

            return None

        except Exception as e:
            print(f"Error ensuring customer exists: {e}")
            return None

    def _update_member_customer_link(self, member_id: str, customer_name: str):
        """Update the member record with the customer link."""
        try:
            requests.put(
                f"{self._url}/api/resource/Gym Member/{member_id}",
                headers=self._headers,
                json={"customer": customer_name},
                timeout=5
            )
        except:
            pass

    def update_next_billing_date(self, member_id: str, membership_type: Dict) -> bool:
        """Update the member's next billing date based on membership duration."""
        if not self._url:
            return False

        try:
            # Calculate next billing date
            duration_months = membership_type.get("duration_months", 1)
            duration_days = membership_type.get("duration_days", 0)

            if duration_months > 0:
                next_date = date.today() + relativedelta(months=duration_months)
            elif duration_days > 0:
                next_date = date.today() + timedelta(days=duration_days)
            else:
                next_date = date.today() + relativedelta(months=1)  # Default to 1 month

            response = requests.put(
                f"{self._url}/api/resource/Gym Member/{member_id}",
                headers=self._headers,
                json={"next_billing_date": next_date.isoformat()},
                timeout=10
            )

            return response.status_code == 200

        except Exception as e:
            print(f"Error updating next billing date: {e}")
            return False

    def run_billing_cycle(self) -> Dict:
        """
        Run a complete billing cycle.
        - Find all members due for billing
        - Generate invoices for each
        - Update next billing dates
        Returns summary of results.
        """
        if not self._setup_connection():
            return {"success": False, "error": "ERPNext not connected"}

        results = {
            "success": True,
            "processed": 0,
            "invoices_created": 0,
            "errors": [],
            "details": []
        }

        # Get members due for billing
        members = self.get_members_due_for_billing()
        results["processed"] = len(members)

        if not members:
            results["message"] = "No members due for billing"
            return results

        for member in members:
            member_name = member.get("full_name", member.get("name"))
            membership_type_name = member.get("current_membership_type")

            if not membership_type_name:
                results["errors"].append(f"{member_name}: No membership type assigned")
                continue

            # Get membership type details
            membership_type = self.get_membership_type_details(membership_type_name)
            if not membership_type:
                results["errors"].append(f"{member_name}: Could not fetch membership type")
                continue

            # Skip non-recurring memberships
            if not membership_type.get("is_recurring"):
                # Just update the next billing date to null or far future
                self.update_next_billing_date(member.get("name"), {"duration_months": 0, "duration_days": 0})
                results["details"].append({
                    "member": member_name,
                    "status": "skipped",
                    "reason": "Non-recurring membership"
                })
                continue

            # Create invoice
            success, message, invoice_name = self.create_sales_invoice(member, membership_type)

            if success:
                results["invoices_created"] += 1
                # Update next billing date
                self.update_next_billing_date(member.get("name"), membership_type)
                results["details"].append({
                    "member": member_name,
                    "status": "success",
                    "invoice": invoice_name
                })
            else:
                results["errors"].append(f"{member_name}: {message}")
                results["details"].append({
                    "member": member_name,
                    "status": "error",
                    "error": message
                })

        results["message"] = f"Created {results['invoices_created']} invoices for {results['processed']} members"
        return results

    def preview_billing_cycle(self) -> Dict:
        """
        Preview what would be billed without actually creating invoices.
        Useful for checking before running the billing cycle.
        """
        if not self._setup_connection():
            return {"success": False, "error": "ERPNext not connected"}

        members = self.get_members_due_for_billing()

        preview = {
            "success": True,
            "members_due": len(members),
            "total_amount": 0,
            "members": []
        }

        for member in members:
            membership_type_name = member.get("current_membership_type")
            membership_type = self.get_membership_type_details(membership_type_name) if membership_type_name else None

            member_info = {
                "name": member.get("full_name", member.get("name")),
                "membership": membership_type_name or "None",
                "next_billing_date": member.get("next_billing_date"),
                "amount": 0,
                "is_recurring": False
            }

            if membership_type:
                member_info["amount"] = float(membership_type.get("price", 0))
                member_info["is_recurring"] = membership_type.get("is_recurring", False)
                if member_info["is_recurring"]:
                    preview["total_amount"] += member_info["amount"]

            preview["members"].append(member_info)

        return preview


# Singleton instance
_billing_service = None


def get_billing_service() -> AutoBillingService:
    """Get the auto billing service singleton."""
    global _billing_service
    if _billing_service is None:
        _billing_service = AutoBillingService()
    return _billing_service
