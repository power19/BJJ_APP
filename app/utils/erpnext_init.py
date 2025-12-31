# app/utils/erpnext_init.py
"""
ERPNext initialization module for Gym Management System.
Checks and creates required doctypes on first run.
"""
import requests
import json
from typing import Optional, Dict, List, Tuple
from .config import get_config


# Define the custom doctypes required for the gym app
GYM_DOCTYPES = {
    "Membership Type": {
        "doctype": "DocType",
        "name": "Membership Type",
        "module": "Custom",
        "custom": 1,
        "autoname": "field:membership_name",
        "is_submittable": 0,
        "fields": [
            {"fieldname": "membership_name", "fieldtype": "Data", "label": "Membership Name", "reqd": 1, "unique": 1},
            {"fieldname": "duration_months", "fieldtype": "Int", "label": "Duration (Months)", "reqd": 1, "default": "1"},
            {"fieldname": "price", "fieldtype": "Currency", "label": "Price", "reqd": 1},
            {"fieldname": "description", "fieldtype": "Small Text", "label": "Description"},
            {"fieldname": "is_active", "fieldtype": "Check", "label": "Is Active", "default": "1"},
            {"fieldname": "max_freeze_days", "fieldtype": "Int", "label": "Max Freeze Days", "default": "0"},
            {"fieldname": "classes_per_week", "fieldtype": "Int", "label": "Classes Per Week", "description": "0 = Unlimited"},
        ],
        "permissions": [
            {"role": "System Manager", "read": 1, "write": 1, "create": 1, "delete": 1},
            {"role": "Sales User", "read": 1},
        ]
    },
    "Gym Member": {
        "doctype": "DocType",
        "name": "Gym Member",
        "module": "Custom",
        "custom": 1,
        "autoname": "naming_series:",
        "is_submittable": 0,
        "fields": [
            {"fieldname": "naming_series", "fieldtype": "Select", "label": "Series", "options": "GYM-.YYYY.-", "reqd": 1},
            {"fieldname": "member_name", "fieldtype": "Data", "label": "Member Name", "reqd": 1},
            {"fieldname": "email", "fieldtype": "Data", "label": "Email", "options": "Email"},
            {"fieldname": "phone", "fieldtype": "Data", "label": "Phone"},
            {"fieldname": "date_of_birth", "fieldtype": "Date", "label": "Date of Birth"},
            {"fieldname": "gender", "fieldtype": "Select", "label": "Gender", "options": "\nMale\nFemale\nOther"},
            {"fieldname": "address", "fieldtype": "Small Text", "label": "Address"},
            {"fieldname": "emergency_contact", "fieldtype": "Data", "label": "Emergency Contact"},
            {"fieldname": "emergency_phone", "fieldtype": "Data", "label": "Emergency Phone"},
            {"fieldname": "column_break_1", "fieldtype": "Column Break"},
            {"fieldname": "photo", "fieldtype": "Attach Image", "label": "Photo"},
            {"fieldname": "rfid_tag", "fieldtype": "Data", "label": "RFID Tag", "unique": 1},
            {"fieldname": "customer", "fieldtype": "Link", "label": "Linked Customer", "options": "Customer"},
            {"fieldname": "status", "fieldtype": "Select", "label": "Status", "options": "Active\nInactive\nSuspended\nExpired", "default": "Active"},
            {"fieldname": "join_date", "fieldtype": "Date", "label": "Join Date"},
            {"fieldname": "section_membership", "fieldtype": "Section Break", "label": "Current Membership"},
            {"fieldname": "current_membership_type", "fieldtype": "Link", "label": "Membership Type", "options": "Membership Type"},
            {"fieldname": "membership_start_date", "fieldtype": "Date", "label": "Start Date"},
            {"fieldname": "membership_end_date", "fieldtype": "Date", "label": "End Date"},
            {"fieldname": "section_notes", "fieldtype": "Section Break", "label": "Notes"},
            {"fieldname": "notes", "fieldtype": "Text", "label": "Notes"},
        ],
        "permissions": [
            {"role": "System Manager", "read": 1, "write": 1, "create": 1, "delete": 1},
            {"role": "Sales User", "read": 1, "write": 1, "create": 1},
        ]
    },
    "Gym Attendance": {
        "doctype": "DocType",
        "name": "Gym Attendance",
        "module": "Custom",
        "custom": 1,
        "autoname": "naming_series:",
        "is_submittable": 0,
        "fields": [
            {"fieldname": "naming_series", "fieldtype": "Select", "label": "Series", "options": "ATT-.YYYY.-.#####", "reqd": 1},
            {"fieldname": "member", "fieldtype": "Link", "label": "Member", "options": "Gym Member", "reqd": 1},
            {"fieldname": "member_name", "fieldtype": "Data", "label": "Member Name", "fetch_from": "member.member_name", "read_only": 1},
            {"fieldname": "check_in_time", "fieldtype": "Datetime", "label": "Check In Time", "reqd": 1},
            {"fieldname": "check_out_time", "fieldtype": "Datetime", "label": "Check Out Time"},
            {"fieldname": "rfid_tag", "fieldtype": "Data", "label": "RFID Tag"},
            {"fieldname": "column_break_1", "fieldtype": "Column Break"},
            {"fieldname": "class_type", "fieldtype": "Link", "label": "Class Type", "options": "Gym Class Type"},
            {"fieldname": "checked_in_by", "fieldtype": "Link", "label": "Checked In By", "options": "User"},
            {"fieldname": "notes", "fieldtype": "Small Text", "label": "Notes"},
        ],
        "permissions": [
            {"role": "System Manager", "read": 1, "write": 1, "create": 1, "delete": 1},
            {"role": "Sales User", "read": 1, "write": 1, "create": 1},
        ]
    },
    "Gym Class Type": {
        "doctype": "DocType",
        "name": "Gym Class Type",
        "module": "Custom",
        "custom": 1,
        "autoname": "field:class_name",
        "is_submittable": 0,
        "fields": [
            {"fieldname": "class_name", "fieldtype": "Data", "label": "Class Name", "reqd": 1, "unique": 1},
            {"fieldname": "description", "fieldtype": "Small Text", "label": "Description"},
            {"fieldname": "duration_minutes", "fieldtype": "Int", "label": "Duration (Minutes)", "default": "60"},
            {"fieldname": "max_capacity", "fieldtype": "Int", "label": "Max Capacity"},
            {"fieldname": "color", "fieldtype": "Color", "label": "Color"},
            {"fieldname": "is_active", "fieldtype": "Check", "label": "Is Active", "default": "1"},
        ],
        "permissions": [
            {"role": "System Manager", "read": 1, "write": 1, "create": 1, "delete": 1},
            {"role": "Sales User", "read": 1},
        ]
    },
    "Membership": {
        "doctype": "DocType",
        "name": "Membership",
        "module": "Custom",
        "custom": 1,
        "autoname": "naming_series:",
        "is_submittable": 1,
        "fields": [
            {"fieldname": "naming_series", "fieldtype": "Select", "label": "Series", "options": "MEM-.YYYY.-", "reqd": 1},
            {"fieldname": "member", "fieldtype": "Link", "label": "Member", "options": "Gym Member", "reqd": 1},
            {"fieldname": "member_name", "fieldtype": "Data", "label": "Member Name", "fetch_from": "member.member_name", "read_only": 1},
            {"fieldname": "membership_type", "fieldtype": "Link", "label": "Membership Type", "options": "Membership Type", "reqd": 1},
            {"fieldname": "column_break_1", "fieldtype": "Column Break"},
            {"fieldname": "start_date", "fieldtype": "Date", "label": "Start Date", "reqd": 1},
            {"fieldname": "end_date", "fieldtype": "Date", "label": "End Date", "reqd": 1},
            {"fieldname": "status", "fieldtype": "Select", "label": "Status", "options": "Active\nExpired\nCancelled\nFrozen", "default": "Active"},
            {"fieldname": "section_payment", "fieldtype": "Section Break", "label": "Payment Details"},
            {"fieldname": "amount", "fieldtype": "Currency", "label": "Amount"},
            {"fieldname": "paid_amount", "fieldtype": "Currency", "label": "Paid Amount"},
            {"fieldname": "payment_status", "fieldtype": "Select", "label": "Payment Status", "options": "Unpaid\nPartially Paid\nPaid", "default": "Unpaid"},
            {"fieldname": "invoice", "fieldtype": "Link", "label": "Invoice", "options": "Sales Invoice"},
        ],
        "permissions": [
            {"role": "System Manager", "read": 1, "write": 1, "create": 1, "delete": 1, "submit": 1, "cancel": 1},
            {"role": "Sales User", "read": 1, "write": 1, "create": 1, "submit": 1},
        ]
    },
    "Payment Handover": {
        "doctype": "DocType",
        "name": "Payment Handover",
        "module": "Custom",
        "custom": 1,
        "autoname": "naming_series:",
        "is_submittable": 1,
        "fields": [
            {"fieldname": "naming_series", "fieldtype": "Select", "label": "Series", "options": "HND-.YYYY.-", "reqd": 1},
            {"fieldname": "handover_date", "fieldtype": "Date", "label": "Handover Date", "reqd": 1},
            {"fieldname": "from_user", "fieldtype": "Link", "label": "From User", "options": "User", "reqd": 1},
            {"fieldname": "to_user", "fieldtype": "Link", "label": "To User", "options": "User", "reqd": 1},
            {"fieldname": "column_break_1", "fieldtype": "Column Break"},
            {"fieldname": "total_amount", "fieldtype": "Currency", "label": "Total Amount", "reqd": 1},
            {"fieldname": "status", "fieldtype": "Select", "label": "Status", "options": "Pending\nCompleted\nCancelled", "default": "Pending"},
            {"fieldname": "section_payments", "fieldtype": "Section Break", "label": "Payments"},
            {"fieldname": "payments", "fieldtype": "Table", "label": "Payments", "options": "Payment Handover Item"},
            {"fieldname": "section_notes", "fieldtype": "Section Break", "label": "Notes"},
            {"fieldname": "notes", "fieldtype": "Text", "label": "Notes"},
        ],
        "permissions": [
            {"role": "System Manager", "read": 1, "write": 1, "create": 1, "delete": 1, "submit": 1, "cancel": 1},
            {"role": "Sales User", "read": 1, "write": 1, "create": 1, "submit": 1},
        ]
    },
    "Payment Handover Item": {
        "doctype": "DocType",
        "name": "Payment Handover Item",
        "module": "Custom",
        "custom": 1,
        "istable": 1,
        "fields": [
            {"fieldname": "payment_entry", "fieldtype": "Link", "label": "Payment Entry", "options": "Payment Entry"},
            {"fieldname": "payment_date", "fieldtype": "Date", "label": "Payment Date"},
            {"fieldname": "customer", "fieldtype": "Link", "label": "Customer", "options": "Customer"},
            {"fieldname": "amount", "fieldtype": "Currency", "label": "Amount"},
            {"fieldname": "payment_type", "fieldtype": "Data", "label": "Payment Type"},
        ],
    },
}


class ERPNextInitializer:
    """Handles ERPNext initialization and doctype creation."""

    def __init__(self):
        self.config = get_config()
        self._headers = None
        self._url = None

    def _setup_connection(self) -> bool:
        """Setup connection parameters."""
        if not self.config.is_configured():
            return False

        erp_config = self.config.get_erpnext_config()
        self._url = erp_config.get('url', '')
        api_key = erp_config.get('api_key', '')
        api_secret = erp_config.get('api_secret', '')

        self._headers = {
            'Authorization': f'token {api_key}:{api_secret}',
            'Content-Type': 'application/json'
        }
        return True

    def check_doctype_exists(self, doctype_name: str) -> bool:
        """Check if a doctype exists in ERPNext."""
        if not self._setup_connection():
            return False

        try:
            response = requests.get(
                f"{self._url}/api/resource/DocType/{doctype_name}",
                headers=self._headers,
                timeout=10
            )
            return response.status_code == 200
        except Exception as e:
            print(f"Error checking doctype {doctype_name}: {e}")
            return False

    def get_initialization_status(self) -> Dict[str, bool]:
        """Get the initialization status of all required doctypes."""
        status = {}
        for doctype_name in GYM_DOCTYPES.keys():
            status[doctype_name] = self.check_doctype_exists(doctype_name)
        return status

    def is_fully_initialized(self) -> bool:
        """Check if all required doctypes are initialized."""
        status = self.get_initialization_status()
        return all(status.values())

    def create_doctype(self, doctype_name: str) -> Tuple[bool, str]:
        """Create a single doctype in ERPNext."""
        if not self._setup_connection():
            return False, "ERPNext not configured"

        if doctype_name not in GYM_DOCTYPES:
            return False, f"Unknown doctype: {doctype_name}"

        # Check if already exists
        if self.check_doctype_exists(doctype_name):
            return True, f"{doctype_name} already exists"

        doctype_def = GYM_DOCTYPES[doctype_name].copy()

        try:
            response = requests.post(
                f"{self._url}/api/resource/DocType",
                headers=self._headers,
                json=doctype_def,
                timeout=30
            )

            if response.status_code in [200, 201]:
                return True, f"{doctype_name} created successfully"
            else:
                error_msg = response.json().get('exc', response.text)
                return False, f"Failed to create {doctype_name}: {error_msg}"

        except Exception as e:
            return False, f"Error creating {doctype_name}: {str(e)}"

    def initialize_all(self) -> Dict[str, Tuple[bool, str]]:
        """Initialize all required doctypes."""
        results = {}

        # Order matters - create parent doctypes first
        ordered_doctypes = [
            "Membership Type",
            "Gym Class Type",
            "Gym Member",
            "Gym Attendance",
            "Membership",
            "Payment Handover Item",
            "Payment Handover",
        ]

        for doctype_name in ordered_doctypes:
            success, message = self.create_doctype(doctype_name)
            results[doctype_name] = (success, message)

            # If creation failed (and it's not because it already exists), stop
            if not success and "already exists" not in message:
                print(f"Failed to create {doctype_name}: {message}")

        return results

    def create_default_data(self) -> Dict[str, Tuple[bool, str]]:
        """Create default data like membership types and class types."""
        results = {}

        if not self._setup_connection():
            return {"error": (False, "ERPNext not configured")}

        # Default Membership Types
        default_memberships = [
            {"membership_name": "Monthly", "duration_months": 1, "price": 100, "is_active": 1},
            {"membership_name": "Quarterly", "duration_months": 3, "price": 270, "is_active": 1},
            {"membership_name": "Semi-Annual", "duration_months": 6, "price": 500, "is_active": 1},
            {"membership_name": "Annual", "duration_months": 12, "price": 900, "is_active": 1},
            {"membership_name": "Day Pass", "duration_months": 0, "price": 15, "is_active": 1},
        ]

        for membership in default_memberships:
            try:
                response = requests.post(
                    f"{self._url}/api/resource/Membership Type",
                    headers=self._headers,
                    json=membership,
                    timeout=10
                )
                if response.status_code in [200, 201]:
                    results[f"Membership: {membership['membership_name']}"] = (True, "Created")
                elif response.status_code == 409:  # Conflict - already exists
                    results[f"Membership: {membership['membership_name']}"] = (True, "Already exists")
                else:
                    results[f"Membership: {membership['membership_name']}"] = (False, response.text)
            except Exception as e:
                results[f"Membership: {membership['membership_name']}"] = (False, str(e))

        # Default Class Types
        default_classes = [
            {"class_name": "BJJ Fundamentals", "duration_minutes": 60, "color": "#10b981", "is_active": 1},
            {"class_name": "BJJ Advanced", "duration_minutes": 90, "color": "#3b82f6", "is_active": 1},
            {"class_name": "No-Gi", "duration_minutes": 60, "color": "#8b5cf6", "is_active": 1},
            {"class_name": "Open Mat", "duration_minutes": 120, "color": "#f59e0b", "is_active": 1},
            {"class_name": "Kids BJJ", "duration_minutes": 45, "color": "#ec4899", "is_active": 1},
        ]

        for class_type in default_classes:
            try:
                response = requests.post(
                    f"{self._url}/api/resource/Gym Class Type",
                    headers=self._headers,
                    json=class_type,
                    timeout=10
                )
                if response.status_code in [200, 201]:
                    results[f"Class: {class_type['class_name']}"] = (True, "Created")
                elif response.status_code == 409:
                    results[f"Class: {class_type['class_name']}"] = (True, "Already exists")
                else:
                    results[f"Class: {class_type['class_name']}"] = (False, response.text)
            except Exception as e:
                results[f"Class: {class_type['class_name']}"] = (False, str(e))

        return results


def get_initializer() -> ERPNextInitializer:
    """Get an ERPNext initializer instance."""
    return ERPNextInitializer()
