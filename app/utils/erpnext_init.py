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
    "Belt Rank": {
        "doctype": "DocType",
        "name": "Belt Rank",
        "module": "Custom",
        "custom": 1,
        "autoname": "field:rank_name",
        "is_submittable": 0,
        "fields": [
            {"fieldname": "rank_name", "fieldtype": "Data", "label": "Rank Name", "reqd": 1, "unique": 1},
            {"fieldname": "rank_order", "fieldtype": "Int", "label": "Rank Order", "reqd": 1, "description": "Lower = beginner"},
            {"fieldname": "color", "fieldtype": "Color", "label": "Belt Color"},
            {"fieldname": "days_required", "fieldtype": "Int", "label": "Days Required for Next Rank", "default": "0"},
            {"fieldname": "stripes_available", "fieldtype": "Int", "label": "Stripes Available", "default": "4"},
            {"fieldname": "description", "fieldtype": "Small Text", "label": "Description"},
            {"fieldname": "is_active", "fieldtype": "Check", "label": "Is Active", "default": "1"},
        ],
        "permissions": [
            {"role": "System Manager", "read": 1, "write": 1, "create": 1, "delete": 1},
            {"role": "Sales User", "read": 1},
        ]
    },
    "Gym Staff": {
        "doctype": "DocType",
        "name": "Gym Staff",
        "module": "Custom",
        "custom": 1,
        "autoname": "field:staff_name",
        "is_submittable": 0,
        "fields": [
            {"fieldname": "company", "fieldtype": "Link", "label": "Company", "options": "Company", "remember_last_selected_value": 1},
            {"fieldname": "staff_name", "fieldtype": "Data", "label": "Full Name", "reqd": 1},
            {"fieldname": "role", "fieldtype": "Select", "label": "Role", "options": "Coach\nHead Coach\nTreasurer\nAdmin\nReceptionist", "reqd": 1},
            {"fieldname": "rfid_tag", "fieldtype": "Data", "label": "RFID Tag", "unique": 1},
            {"fieldname": "column_break_1", "fieldtype": "Column Break"},
            {"fieldname": "phone", "fieldtype": "Data", "label": "Phone"},
            {"fieldname": "email", "fieldtype": "Data", "label": "Email", "options": "Email"},
            {"fieldname": "user", "fieldtype": "Link", "label": "Linked User", "options": "User"},
            {"fieldname": "section_permissions", "fieldtype": "Section Break", "label": "Permissions"},
            {"fieldname": "can_promote", "fieldtype": "Check", "label": "Can Promote Members", "default": "0"},
            {"fieldname": "can_process_payments", "fieldtype": "Check", "label": "Can Process Payments", "default": "0"},
            {"fieldname": "can_manage_members", "fieldtype": "Check", "label": "Can Manage Members", "default": "0"},
            {"fieldname": "section_info", "fieldtype": "Section Break", "label": "Additional Info"},
            {"fieldname": "current_rank", "fieldtype": "Link", "label": "Staff Belt Rank", "options": "Belt Rank"},
            {"fieldname": "photo", "fieldtype": "Attach Image", "label": "Photo"},
            {"fieldname": "is_active", "fieldtype": "Check", "label": "Is Active", "default": "1"},
        ],
        "permissions": [
            {"role": "System Manager", "read": 1, "write": 1, "create": 1, "delete": 1},
            {"role": "Sales User", "read": 1},
        ]
    },
    "Membership Type": {
        "doctype": "DocType",
        "name": "Membership Type",
        "module": "Custom",
        "custom": 1,
        "autoname": "field:membership_name",
        "is_submittable": 0,
        "fields": [
            {"fieldname": "membership_name", "fieldtype": "Data", "label": "Membership Name", "reqd": 1, "unique": 1},
            {"fieldname": "membership_category", "fieldtype": "Select", "label": "Category",
             "options": "Subscription\nCommitment\nDay Pass\nStrip Card\nPrivate Lesson\nRental\nRegistration", "reqd": 1},
            {"fieldname": "duration_months", "fieldtype": "Int", "label": "Duration (Months)", "default": "1"},
            {"fieldname": "duration_days", "fieldtype": "Int", "label": "Duration (Days)", "default": "0", "description": "For day passes"},
            {"fieldname": "sessions_included", "fieldtype": "Int", "label": "Sessions Included", "default": "0", "description": "For strip cards"},
            {"fieldname": "column_break_1", "fieldtype": "Column Break"},
            {"fieldname": "price", "fieldtype": "Currency", "label": "Price (SRD)", "reqd": 1},
            {"fieldname": "requires_commitment", "fieldtype": "Check", "label": "Requires Commitment", "default": "0"},
            {"fieldname": "commitment_months", "fieldtype": "Int", "label": "Commitment Period (Months)", "default": "0"},
            {"fieldname": "is_recurring", "fieldtype": "Check", "label": "Is Recurring", "default": "0"},
            {"fieldname": "section_settings", "fieldtype": "Section Break", "label": "Settings"},
            {"fieldname": "counts_towards_rank", "fieldtype": "Check", "label": "Counts Towards Rank Progression", "default": "1"},
            {"fieldname": "description", "fieldtype": "Small Text", "label": "Description"},
            {"fieldname": "is_active", "fieldtype": "Check", "label": "Is Active", "default": "1"},
        ],
        "permissions": [
            {"role": "System Manager", "read": 1, "write": 1, "create": 1, "delete": 1},
            {"role": "Sales User", "read": 1},
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
            {"fieldname": "allowed_member_types", "fieldtype": "Select", "label": "Allowed Member Types",
             "options": "All\nAdults Only\nKids Only\nTeens Only", "default": "All"},
            {"fieldname": "column_break_1", "fieldtype": "Column Break"},
            {"fieldname": "color", "fieldtype": "Color", "label": "Color"},
            {"fieldname": "counts_towards_rank", "fieldtype": "Check", "label": "Counts Towards Rank", "default": "1"},
            {"fieldname": "is_active", "fieldtype": "Check", "label": "Is Active", "default": "1"},
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
            {"fieldname": "company", "fieldtype": "Link", "label": "Company", "options": "Company", "remember_last_selected_value": 1},
            {"fieldname": "naming_series", "fieldtype": "Select", "label": "Series", "options": "GYM-.YYYY.-", "reqd": 1},
            {"fieldname": "member_type", "fieldtype": "Select", "label": "Member Type",
             "options": "Adult\nTeenager\nChild", "reqd": 1, "default": "Adult"},
            {"fieldname": "first_name", "fieldtype": "Data", "label": "First Name", "reqd": 1},
            {"fieldname": "last_name", "fieldtype": "Data", "label": "Last Name", "reqd": 1},
            {"fieldname": "full_name", "fieldtype": "Data", "label": "Full Name", "read_only": 1},
            {"fieldname": "column_break_1", "fieldtype": "Column Break"},
            {"fieldname": "photo", "fieldtype": "Attach Image", "label": "Photo"},
            {"fieldname": "rfid_tag", "fieldtype": "Data", "label": "RFID Tag", "unique": 1},
            {"fieldname": "status", "fieldtype": "Select", "label": "Status",
             "options": "Active\nSuspended\nCancelled\nExpired", "default": "Active"},

            {"fieldname": "section_contact", "fieldtype": "Section Break", "label": "Contact Information"},
            {"fieldname": "email", "fieldtype": "Data", "label": "Email", "options": "Email"},
            {"fieldname": "phone", "fieldtype": "Data", "label": "Phone Number", "reqd": 1},
            {"fieldname": "address", "fieldtype": "Small Text", "label": "Address"},
            {"fieldname": "column_break_2", "fieldtype": "Column Break"},
            {"fieldname": "date_of_birth", "fieldtype": "Date", "label": "Date of Birth"},
            {"fieldname": "gender", "fieldtype": "Select", "label": "Gender", "options": "\nMale\nFemale\nOther"},
            {"fieldname": "emergency_contact", "fieldtype": "Data", "label": "Emergency Contact Name"},
            {"fieldname": "emergency_phone", "fieldtype": "Data", "label": "Emergency Phone"},

            {"fieldname": "section_parent", "fieldtype": "Section Break", "label": "Parent/Guardian (For Minors)",
             "depends_on": "eval:doc.member_type=='Child' || doc.member_type=='Teenager'"},
            {"fieldname": "parent_member", "fieldtype": "Link", "label": "Parent (If Member)", "options": "Gym Member",
             "description": "Optional: Link to adult member if parent also trains here"},
            {"fieldname": "parent_name", "fieldtype": "Data", "label": "Parent Name", "fetch_from": "parent_member.full_name", "read_only": 1,
             "depends_on": "parent_member"},
            {"fieldname": "parent_phone", "fieldtype": "Data", "label": "Parent Phone", "fetch_from": "parent_member.phone", "read_only": 1,
             "depends_on": "parent_member"},
            {"fieldname": "column_break_guardian", "fieldtype": "Column Break"},
            {"fieldname": "guardian_name", "fieldtype": "Data", "label": "Guardian Name",
             "description": "For parents/guardians who are not gym members"},
            {"fieldname": "guardian_phone", "fieldtype": "Data", "label": "Guardian Phone"},
            {"fieldname": "guardian_email", "fieldtype": "Data", "label": "Guardian Email", "options": "Email"},
            {"fieldname": "guardian_relationship", "fieldtype": "Select", "label": "Relationship",
             "options": "\nParent\nGuardian\nGrandparent\nSibling\nOther"},

            {"fieldname": "section_rank", "fieldtype": "Section Break", "label": "Belt Rank & Progression"},
            {"fieldname": "current_rank", "fieldtype": "Link", "label": "Current Belt Rank", "options": "Belt Rank"},
            {"fieldname": "current_stripes", "fieldtype": "Int", "label": "Current Stripes", "default": "0"},
            {"fieldname": "days_at_current_rank", "fieldtype": "Int", "label": "Training Days at Current Rank", "default": "0", "read_only": 1},
            {"fieldname": "column_break_3", "fieldtype": "Column Break"},
            {"fieldname": "total_training_days", "fieldtype": "Int", "label": "Total Training Days", "default": "0", "read_only": 1},
            {"fieldname": "last_promotion_date", "fieldtype": "Date", "label": "Last Promotion Date"},
            {"fieldname": "eligible_for_promotion", "fieldtype": "Check", "label": "Eligible for Promotion", "read_only": 1},

            {"fieldname": "section_membership", "fieldtype": "Section Break", "label": "Membership Details"},
            {"fieldname": "current_membership_type", "fieldtype": "Link", "label": "Membership Type", "options": "Membership Type"},
            {"fieldname": "membership_start_date", "fieldtype": "Date", "label": "Membership Start Date"},
            {"fieldname": "membership_end_date", "fieldtype": "Date", "label": "Membership End Date"},
            {"fieldname": "column_break_4", "fieldtype": "Column Break"},
            {"fieldname": "payment_status", "fieldtype": "Select", "label": "Payment Status",
             "options": "Current\nOverdue\nGrace Period", "default": "Current"},
            {"fieldname": "remaining_sessions", "fieldtype": "Int", "label": "Remaining Sessions", "default": "0",
             "description": "For strip card members"},
            {"fieldname": "join_date", "fieldtype": "Date", "label": "Join Date"},

            {"fieldname": "section_linked", "fieldtype": "Section Break", "label": "Linked Records"},
            {"fieldname": "customer", "fieldtype": "Link", "label": "Linked Customer", "options": "Customer"},

            {"fieldname": "section_notes", "fieldtype": "Section Break", "label": "Notes"},
            {"fieldname": "notes", "fieldtype": "Text", "label": "Notes"},
        ],
        "permissions": [
            {"role": "System Manager", "read": 1, "write": 1, "create": 1, "delete": 1},
            {"role": "Sales User", "read": 1, "write": 1, "create": 1},
        ]
    },
    "Rank History": {
        "doctype": "DocType",
        "name": "Rank History",
        "module": "Custom",
        "custom": 1,
        "autoname": "naming_series:",
        "is_submittable": 0,
        "fields": [
            {"fieldname": "naming_series", "fieldtype": "Select", "label": "Series", "options": "RANK-.YYYY.-", "reqd": 1},
            {"fieldname": "member", "fieldtype": "Link", "label": "Member", "options": "Gym Member", "reqd": 1},
            {"fieldname": "member_name", "fieldtype": "Data", "label": "Member Name", "fetch_from": "member.full_name", "read_only": 1},
            {"fieldname": "column_break_1", "fieldtype": "Column Break"},
            {"fieldname": "from_rank", "fieldtype": "Link", "label": "From Rank", "options": "Belt Rank"},
            {"fieldname": "to_rank", "fieldtype": "Link", "label": "To Rank", "options": "Belt Rank", "reqd": 1},
            {"fieldname": "section_details", "fieldtype": "Section Break", "label": "Promotion Details"},
            {"fieldname": "promotion_date", "fieldtype": "Date", "label": "Promotion Date", "reqd": 1},
            {"fieldname": "days_in_previous_rank", "fieldtype": "Int", "label": "Days in Previous Rank", "read_only": 1},
            {"fieldname": "column_break_2", "fieldtype": "Column Break"},
            {"fieldname": "promoted_by", "fieldtype": "Link", "label": "Promoted By", "options": "Gym Staff", "reqd": 1},
            {"fieldname": "promoter_rfid_verified", "fieldtype": "Check", "label": "RFID Verified", "read_only": 1},
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
            {"fieldname": "company", "fieldtype": "Link", "label": "Company", "options": "Company", "fetch_from": "member.company"},
            {"fieldname": "naming_series", "fieldtype": "Select", "label": "Series", "options": "ATT-.YYYY.-.#####", "reqd": 1},
            {"fieldname": "member", "fieldtype": "Link", "label": "Member", "options": "Gym Member", "reqd": 1},
            {"fieldname": "member_name", "fieldtype": "Data", "label": "Member Name", "fetch_from": "member.full_name", "read_only": 1},
            {"fieldname": "attendance_date", "fieldtype": "Date", "label": "Attendance Date", "reqd": 1},
            {"fieldname": "column_break_1", "fieldtype": "Column Break"},
            {"fieldname": "check_in_time", "fieldtype": "Time", "label": "Check In Time"},
            {"fieldname": "check_out_time", "fieldtype": "Time", "label": "Check Out Time"},
            {"fieldname": "rfid_tag", "fieldtype": "Data", "label": "RFID Tag Used"},
            {"fieldname": "section_class", "fieldtype": "Section Break", "label": "Class Information"},
            {"fieldname": "class_type", "fieldtype": "Link", "label": "Class Type", "options": "Gym Class Type"},
            {"fieldname": "counts_towards_rank", "fieldtype": "Check", "label": "Counts Towards Rank", "default": "1",
             "description": "Only counts if payment is current"},
            {"fieldname": "column_break_2", "fieldtype": "Column Break"},
            {"fieldname": "payment_was_current", "fieldtype": "Check", "label": "Payment Was Current", "read_only": 1},
            {"fieldname": "checked_in_by", "fieldtype": "Link", "label": "Checked In By", "options": "User"},
            {"fieldname": "notes", "fieldtype": "Small Text", "label": "Notes"},
        ],
        "permissions": [
            {"role": "System Manager", "read": 1, "write": 1, "create": 1, "delete": 1},
            {"role": "Sales User", "read": 1, "write": 1, "create": 1},
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
            {"fieldname": "member_name", "fieldtype": "Data", "label": "Member Name", "fetch_from": "member.full_name", "read_only": 1},
            {"fieldname": "membership_type", "fieldtype": "Link", "label": "Membership Type", "options": "Membership Type", "reqd": 1},
            {"fieldname": "column_break_1", "fieldtype": "Column Break"},
            {"fieldname": "start_date", "fieldtype": "Date", "label": "Start Date", "reqd": 1},
            {"fieldname": "end_date", "fieldtype": "Date", "label": "End Date", "reqd": 1},
            {"fieldname": "status", "fieldtype": "Select", "label": "Status", "options": "Active\nExpired\nCancelled\nSuspended", "default": "Active"},
            {"fieldname": "section_payment", "fieldtype": "Section Break", "label": "Payment Details"},
            {"fieldname": "amount", "fieldtype": "Currency", "label": "Amount (SRD)"},
            {"fieldname": "paid_amount", "fieldtype": "Currency", "label": "Paid Amount (SRD)"},
            {"fieldname": "payment_status", "fieldtype": "Select", "label": "Payment Status", "options": "Unpaid\nPartially Paid\nPaid", "default": "Unpaid"},
            {"fieldname": "column_break_3", "fieldtype": "Column Break"},
            {"fieldname": "sessions_remaining", "fieldtype": "Int", "label": "Sessions Remaining", "description": "For strip cards"},
            {"fieldname": "invoice", "fieldtype": "Link", "label": "Invoice", "options": "Sales Invoice"},
        ],
        "permissions": [
            {"role": "System Manager", "read": 1, "write": 1, "create": 1, "delete": 1, "submit": 1, "cancel": 1},
            {"role": "Sales User", "read": 1, "write": 1, "create": 1, "submit": 1},
        ]
    },
    "Gym Payment": {
        "doctype": "DocType",
        "name": "Gym Payment",
        "module": "Custom",
        "custom": 1,
        "autoname": "naming_series:",
        "is_submittable": 1,
        "fields": [
            {"fieldname": "company", "fieldtype": "Link", "label": "Company", "options": "Company", "fetch_from": "member.company"},
            {"fieldname": "naming_series", "fieldtype": "Select", "label": "Series", "options": "PAY-.YYYY.-", "reqd": 1},
            {"fieldname": "member", "fieldtype": "Link", "label": "Member", "options": "Gym Member", "reqd": 1},
            {"fieldname": "member_name", "fieldtype": "Data", "label": "Member Name", "fetch_from": "member.full_name", "read_only": 1},
            {"fieldname": "member_rfid", "fieldtype": "Data", "label": "Member RFID", "read_only": 1},
            {"fieldname": "column_break_1", "fieldtype": "Column Break"},
            {"fieldname": "payment_date", "fieldtype": "Date", "label": "Payment Date", "reqd": 1},
            {"fieldname": "payment_type", "fieldtype": "Select", "label": "Payment Type",
             "options": "Registration\nMonthly Subscription\nDay Pass\nStrip Card\nPrivate Lesson\nGi Rental\nOther", "reqd": 1},
            {"fieldname": "section_amount", "fieldtype": "Section Break", "label": "Amount"},
            {"fieldname": "amount", "fieldtype": "Currency", "label": "Amount (SRD)", "reqd": 1},
            {"fieldname": "payment_method", "fieldtype": "Select", "label": "Payment Method",
             "options": "Cash\nBank Transfer\nCard\nMobile Payment", "default": "Cash"},
            {"fieldname": "column_break_2", "fieldtype": "Column Break"},
            {"fieldname": "membership", "fieldtype": "Link", "label": "Related Membership", "options": "Membership"},
            {"fieldname": "reference", "fieldtype": "Data", "label": "Reference Number"},
            {"fieldname": "section_verification", "fieldtype": "Section Break", "label": "Verification"},
            {"fieldname": "processed_by", "fieldtype": "Link", "label": "Processed By", "options": "Gym Staff", "reqd": 1},
            {"fieldname": "processor_rfid_verified", "fieldtype": "Check", "label": "Staff RFID Verified", "read_only": 1},
            {"fieldname": "column_break_3", "fieldtype": "Column Break"},
            {"fieldname": "status", "fieldtype": "Select", "label": "Status",
             "options": "Pending\nCompleted\nCancelled\nRefunded", "default": "Pending"},
            {"fieldname": "section_notes", "fieldtype": "Section Break", "label": "Notes"},
            {"fieldname": "notes", "fieldtype": "Text", "label": "Notes"},
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
            {"fieldname": "company", "fieldtype": "Link", "label": "Company", "options": "Company", "remember_last_selected_value": 1},
            {"fieldname": "naming_series", "fieldtype": "Select", "label": "Series", "options": "HND-.YYYY.-", "reqd": 1},
            {"fieldname": "handover_date", "fieldtype": "Date", "label": "Handover Date", "reqd": 1},
            {"fieldname": "from_staff", "fieldtype": "Link", "label": "From Staff", "options": "Gym Staff", "reqd": 1},
            {"fieldname": "to_staff", "fieldtype": "Link", "label": "To Staff", "options": "Gym Staff", "reqd": 1},
            {"fieldname": "column_break_1", "fieldtype": "Column Break"},
            {"fieldname": "total_amount", "fieldtype": "Currency", "label": "Total Amount (SRD)", "reqd": 1},
            {"fieldname": "status", "fieldtype": "Select", "label": "Status", "options": "Pending\nCompleted\nCancelled", "default": "Pending"},
            {"fieldname": "from_rfid_verified", "fieldtype": "Check", "label": "From Staff RFID Verified", "read_only": 1},
            {"fieldname": "to_rfid_verified", "fieldtype": "Check", "label": "To Staff RFID Verified", "read_only": 1},
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
            {"fieldname": "gym_payment", "fieldtype": "Link", "label": "Gym Payment", "options": "Gym Payment"},
            {"fieldname": "payment_date", "fieldtype": "Date", "label": "Payment Date"},
            {"fieldname": "member", "fieldtype": "Link", "label": "Member", "options": "Gym Member"},
            {"fieldname": "amount", "fieldtype": "Currency", "label": "Amount (SRD)"},
            {"fieldname": "payment_type", "fieldtype": "Data", "label": "Payment Type"},
        ],
    },
}


# BJJ Adult Belt Ranks (16+ years)
BJJ_ADULT_RANKS = [
    {"rank_name": "White Belt", "rank_order": 10, "color": "#FFFFFF", "days_required": 0, "stripes_available": 4, "is_active": 1, "description": "Beginner - All adults start here"},
    {"rank_name": "Blue Belt", "rank_order": 20, "color": "#0066CC", "days_required": 100, "stripes_available": 4, "is_active": 1, "description": "Intermediate - Minimum 2 years training"},
    {"rank_name": "Purple Belt", "rank_order": 30, "color": "#6B21A8", "days_required": 200, "stripes_available": 4, "is_active": 1, "description": "Advanced - Minimum 1.5 years at blue"},
    {"rank_name": "Brown Belt", "rank_order": 40, "color": "#8B4513", "days_required": 300, "stripes_available": 4, "is_active": 1, "description": "Expert - Minimum 1.5 years at purple"},
    {"rank_name": "Black Belt", "rank_order": 50, "color": "#000000", "days_required": 400, "stripes_available": 6, "is_active": 1, "description": "Master - Minimum 1 year at brown"},
    {"rank_name": "Red/Black Belt (Coral)", "rank_order": 60, "color": "#FF0000", "days_required": 0, "stripes_available": 0, "is_active": 1, "description": "7th degree - 31+ years as black belt"},
    {"rank_name": "Red/White Belt (Coral)", "rank_order": 70, "color": "#FF6B6B", "days_required": 0, "stripes_available": 0, "is_active": 1, "description": "8th degree - 38+ years as black belt"},
    {"rank_name": "Red Belt", "rank_order": 80, "color": "#CC0000", "days_required": 0, "stripes_available": 0, "is_active": 1, "description": "9th/10th degree - Grandmaster"},
]

# BJJ Kids Belt Ranks (4-15 years) - IBJJF System
BJJ_KIDS_RANKS = [
    {"rank_name": "White Belt (Kids)", "rank_order": 100, "color": "#FFFFFF", "days_required": 0, "stripes_available": 4, "is_active": 1, "description": "Kids beginner belt"},
    {"rank_name": "Grey/White Belt", "rank_order": 110, "color": "#C0C0C0", "days_required": 40, "stripes_available": 4, "is_active": 1, "description": "Kids progression belt"},
    {"rank_name": "Grey Belt", "rank_order": 120, "color": "#808080", "days_required": 50, "stripes_available": 4, "is_active": 1, "description": "Kids grey belt"},
    {"rank_name": "Grey/Black Belt", "rank_order": 130, "color": "#606060", "days_required": 60, "stripes_available": 4, "is_active": 1, "description": "Kids progression belt"},
    {"rank_name": "Yellow/White Belt", "rank_order": 140, "color": "#FFFF99", "days_required": 70, "stripes_available": 4, "is_active": 1, "description": "Kids progression belt"},
    {"rank_name": "Yellow Belt", "rank_order": 150, "color": "#FFD700", "days_required": 80, "stripes_available": 4, "is_active": 1, "description": "Kids yellow belt"},
    {"rank_name": "Yellow/Black Belt", "rank_order": 160, "color": "#DAA520", "days_required": 90, "stripes_available": 4, "is_active": 1, "description": "Kids progression belt"},
    {"rank_name": "Orange/White Belt", "rank_order": 170, "color": "#FFCC80", "days_required": 100, "stripes_available": 4, "is_active": 1, "description": "Kids progression belt"},
    {"rank_name": "Orange Belt", "rank_order": 180, "color": "#FF8C00", "days_required": 110, "stripes_available": 4, "is_active": 1, "description": "Kids orange belt"},
    {"rank_name": "Orange/Black Belt", "rank_order": 190, "color": "#FF6600", "days_required": 120, "stripes_available": 4, "is_active": 1, "description": "Kids progression belt"},
    {"rank_name": "Green/White Belt", "rank_order": 200, "color": "#90EE90", "days_required": 130, "stripes_available": 4, "is_active": 1, "description": "Kids progression belt"},
    {"rank_name": "Green Belt", "rank_order": 210, "color": "#228B22", "days_required": 140, "stripes_available": 4, "is_active": 1, "description": "Kids green belt - highest kids rank"},
    {"rank_name": "Green/Black Belt", "rank_order": 220, "color": "#006400", "days_required": 150, "stripes_available": 4, "is_active": 1, "description": "Kids progression belt - transitions to adult ranks at 16"},
]

# Combined for backward compatibility
BJJ_BELT_RANKS = BJJ_ADULT_RANKS
KIDS_BELT_RANKS = BJJ_KIDS_RANKS

# Default Membership Types (Suriname pricing in SRD)
DEFAULT_MEMBERSHIP_TYPES = [
    {
        "membership_name": "Registration Fee",
        "membership_category": "Registration",
        "duration_months": 0,
        "price": 350,
        "is_recurring": 0,
        "counts_towards_rank": 0,
        "description": "One-time registration fee (Inschrijfgeld)"
    },
    {
        "membership_name": "12-Month Commitment",
        "membership_category": "Commitment",
        "duration_months": 1,
        "price": 600,
        "is_recurring": 1,
        "requires_commitment": 1,
        "commitment_months": 12,
        "counts_towards_rank": 1,
        "description": "Monthly contribution with 12-month commitment (SRD 600/maand)"
    },
    {
        "membership_name": "Month-to-Month",
        "membership_category": "Subscription",
        "duration_months": 1,
        "price": 700,
        "is_recurring": 1,
        "requires_commitment": 0,
        "counts_towards_rank": 1,
        "description": "Flexible month-to-month membership (SRD 700/maand)"
    },
    {
        "membership_name": "Day Training",
        "membership_category": "Day Pass",
        "duration_days": 1,
        "duration_months": 0,
        "price": 150,
        "is_recurring": 0,
        "counts_towards_rank": 1,
        "description": "Single day training pass (Dagtraining SRD 150)"
    },
    {
        "membership_name": "Gi Rental",
        "membership_category": "Rental",
        "duration_days": 1,
        "duration_months": 0,
        "price": 150,
        "is_recurring": 0,
        "counts_towards_rank": 0,
        "description": "Gi/kimono rental per session (Gi huur SRD 150)"
    },
    {
        "membership_name": "10-Lesson Strip Card",
        "membership_category": "Strip Card",
        "duration_months": 0,
        "sessions_included": 10,
        "price": 1350,
        "is_recurring": 0,
        "counts_towards_rank": 1,
        "description": "Strip card for 10 lessons (Strippenkaart SRD 1350)"
    },
    {
        "membership_name": "Private Lesson",
        "membership_category": "Private Lesson",
        "duration_days": 1,
        "duration_months": 0,
        "price": 1000,
        "is_recurring": 0,
        "counts_towards_rank": 1,
        "description": "Private one-on-one lesson (Privélessen SRD 1000/sessie)"
    },
]

# Default Class Types
DEFAULT_CLASS_TYPES = [
    {"class_name": "BJJ Fundamentals", "duration_minutes": 60, "color": "#10b981",
     "allowed_member_types": "All", "counts_towards_rank": 1, "description": "Basic techniques for all levels"},
    {"class_name": "BJJ Advanced", "duration_minutes": 90, "color": "#3b82f6",
     "allowed_member_types": "Adults Only", "counts_towards_rank": 1, "description": "Advanced techniques for blue belt and above"},
    {"class_name": "No-Gi", "duration_minutes": 60, "color": "#8b5cf6",
     "allowed_member_types": "All", "counts_towards_rank": 1, "description": "Training without the gi"},
    {"class_name": "Open Mat", "duration_minutes": 120, "color": "#f59e0b",
     "allowed_member_types": "All", "counts_towards_rank": 1, "description": "Free rolling and drilling"},
    {"class_name": "Kids BJJ", "duration_minutes": 45, "color": "#ec4899",
     "allowed_member_types": "Kids Only", "counts_towards_rank": 1, "description": "Brazilian Jiu-Jitsu for children"},
    {"class_name": "Teens BJJ", "duration_minutes": 60, "color": "#14b8a6",
     "allowed_member_types": "Teens Only", "counts_towards_rank": 1, "description": "Brazilian Jiu-Jitsu for teenagers"},
    {"class_name": "Competition Training", "duration_minutes": 90, "color": "#ef4444",
     "allowed_member_types": "All", "counts_towards_rank": 1, "description": "Intensive training for competitors"},
]


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

    def update_doctype_fields(self, doctype_name: str) -> Tuple[bool, str]:
        """Update an existing doctype with any missing fields from our definition."""
        if not self._setup_connection():
            return False, "ERPNext not configured"

        if doctype_name not in GYM_DOCTYPES:
            return False, f"Unknown doctype: {doctype_name}"

        if not self.check_doctype_exists(doctype_name):
            return False, f"{doctype_name} does not exist"

        try:
            # Get current doctype definition
            response = requests.get(
                f"{self._url}/api/resource/DocType/{doctype_name}",
                headers=self._headers,
                timeout=10
            )

            if response.status_code != 200:
                return False, f"Failed to get {doctype_name}"

            current_doc = response.json().get("data", {})
            current_fields = {f.get("fieldname"): f for f in current_doc.get("fields", [])}

            # Get our field definitions
            our_fields = GYM_DOCTYPES[doctype_name].get("fields", [])

            # Find missing fields
            missing_fields = []
            for field in our_fields:
                fieldname = field.get("fieldname")
                if fieldname and fieldname not in current_fields:
                    missing_fields.append(field)

            if not missing_fields:
                return True, f"{doctype_name} is up to date"

            # Add missing fields to current doc
            updated_fields = current_doc.get("fields", []) + missing_fields

            # Update the doctype
            update_response = requests.put(
                f"{self._url}/api/resource/DocType/{doctype_name}",
                headers=self._headers,
                json={"fields": updated_fields},
                timeout=30
            )

            if update_response.status_code == 200:
                # Clear cache and reload doctype to apply changes
                try:
                    requests.post(
                        f"{self._url}/api/method/frappe.client.clear_cache",
                        headers=self._headers,
                        json={"doctype": doctype_name},
                        timeout=10
                    )
                except:
                    pass  # Cache clear is optional

                field_names = [f.get("fieldname") for f in missing_fields]
                return True, f"Added fields to {doctype_name}: {', '.join(field_names)}"
            else:
                error_msg = update_response.json().get('exc', update_response.text)
                return False, f"Failed to update {doctype_name}: {error_msg[:200]}"

        except Exception as e:
            return False, f"Error updating {doctype_name}: {str(e)}"

    def update_all_doctypes(self) -> Dict[str, Dict]:
        """Update all doctypes with any missing fields."""
        results = {}

        for doctype_name in GYM_DOCTYPES.keys():
            if self.check_doctype_exists(doctype_name):
                success, message = self.update_doctype_fields(doctype_name)
                results[doctype_name] = {"success": success, "message": message}

        return results

    def initialize_all(self) -> Dict[str, Tuple[bool, str]]:
        """Initialize all required doctypes."""
        results = {}

        # Order matters - create parent doctypes first
        ordered_doctypes = [
            "Belt Rank",
            "Gym Staff",
            "Membership Type",
            "Gym Class Type",
            "Gym Member",
            "Rank History",
            "Gym Attendance",
            "Membership",
            "Gym Payment",
            "Payment Handover Item",
            "Payment Handover",
        ]

        for doctype_name in ordered_doctypes:
            success, message = self.create_doctype(doctype_name)
            results[doctype_name] = {"success": success, "message": message}

            # If creation failed (and it's not because it already exists), log it
            if not success and "already exists" not in message:
                print(f"Failed to create {doctype_name}: {message}")

        return results

    def _create_record(self, doctype: str, data: dict) -> Tuple[bool, str]:
        """Create a single record in ERPNext."""
        try:
            response = requests.post(
                f"{self._url}/api/resource/{doctype}",
                headers=self._headers,
                json=data,
                timeout=10
            )
            if response.status_code in [200, 201]:
                return True, "Created"
            elif response.status_code == 409 or "DuplicateEntryError" in response.text:
                return True, "Already exists"
            else:
                return False, response.text[:200]
        except Exception as e:
            return False, str(e)

    def create_default_data(self) -> Dict[str, Tuple[bool, str]]:
        """Create default data like belt ranks, membership types and class types."""
        results = {}

        if not self._setup_connection():
            return {"error": {"success": False, "message": "ERPNext not configured"}}

        # Create Adult Belt Ranks
        for rank in BJJ_ADULT_RANKS:
            success, message = self._create_record("Belt Rank", rank)
            results[f"Adult: {rank['rank_name']}"] = {"success": success, "message": message}

        # Create Kids Belt Ranks
        for rank in BJJ_KIDS_RANKS:
            success, message = self._create_record("Belt Rank", rank)
            results[f"Kids: {rank['rank_name']}"] = {"success": success, "message": message}

        # Create Membership Types
        for membership in DEFAULT_MEMBERSHIP_TYPES:
            success, message = self._create_record("Membership Type", membership)
            results[f"Membership: {membership['membership_name']}"] = {"success": success, "message": message}

        # Create Class Types
        for class_type in DEFAULT_CLASS_TYPES:
            success, message = self._create_record("Gym Class Type", class_type)
            results[f"Class: {class_type['class_name']}"] = {"success": success, "message": message}

        return results

    def create_belt_ranks_only(self) -> Dict[str, Tuple[bool, str]]:
        """Create only belt ranks (adult + kids)."""
        results = {}

        if not self._setup_connection():
            return {"error": {"success": False, "message": "ERPNext not configured"}}

        # Create Adult Belt Ranks
        for rank in BJJ_ADULT_RANKS:
            success, message = self._create_record("Belt Rank", rank)
            results[f"Adult: {rank['rank_name']}"] = {"success": success, "message": message}

        # Create Kids Belt Ranks
        for rank in BJJ_KIDS_RANKS:
            success, message = self._create_record("Belt Rank", rank)
            results[f"Kids: {rank['rank_name']}"] = {"success": success, "message": message}

        return results


def get_initializer() -> ERPNextInitializer:
    """Get an ERPNext initializer instance."""
    return ERPNextInitializer()
