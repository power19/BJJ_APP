# app/utils/erp_client.py
import requests
import json
from typing import Dict, Any, List
import os
from dotenv import load_dotenv

load_dotenv()

class ERPNextClient:
    def __init__(self, base_url: str = "", api_key: str = "", api_secret: str = ""):
        self.base_url = base_url.rstrip('/')
        self.headers = {
            'Authorization': f'token {api_key}:{api_secret}',
            'Content-Type': 'application/json'
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def get_file_url(self, file_path: str) -> tuple[str, dict]:
        """Convert ERPNext file path to full URL with authentication"""
        if not file_path:
            return "", {}
        
        # Clean up the file path - remove any URL parts if present
        if 'private/files/' in file_path:
            file_name = file_path.split('private/files/')[-1]
        else:
            file_name = file_path.split('/')[-1]
        
        # Create the proper URL and return with headers
        url = f"{self.base_url}/private/files/{file_name}"
        
        return url, self.headers

    def search_customer_by_name(self, customer_name: str) -> Dict[str, Any]:
        """Search for a customer by name with detailed debugging"""
        try:
            print("\nDEBUG: Searching customer in ERPNext")
            endpoint = f"{self.base_url}/api/resource/Customer"
            
            params = {
                'fields': '["*"]',
                'filters': json.dumps([["customer_name", "=", customer_name]])
            }
            
            print(f"URL: {endpoint}")
            print(f"Params: {params}")
            
            response = self.session.get(endpoint, params=params)
            print(f"Response status: {response.status_code}")
            print(f"Response content: {response.text}")

            if response.status_code == 200:
                data = response.json()
                if data.get("data"):
                    customer_data = data["data"][0]
                    print("\nCustomer data received:")
                    print(json.dumps(customer_data, indent=2))
                    return customer_data
                else:
                    print("No customer data found in response")
                    return {}
            else:
                print(f"Error response from ERPNext: {response.status_code}")
                return {}

        except Exception as e:
            print(f"Error in search_customer_by_name: {str(e)}")
            return {}

    def search_customer(self, search_term: str) -> Dict[str, Any]:
        """Search for a customer by RFID and get family info"""
        try:
            print(f"\nDEBUG: Searching customer with term: {search_term}")
            endpoint = f"{self.base_url}/api/resource/Customer"
            
            # Search by custom_customer_rfid field
            params = {
                'fields': '["*"]',
                'filters': json.dumps([["custom_customer_rfid", "=", search_term]])
            }
            
            response = self.session.get(endpoint, params=params)
            if response.status_code == 200 and response.json().get("data"):
                customer_data = response.json()["data"][0]
                print("\nProcessed customer data:")
                print(json.dumps(customer_data, indent=2))
                
                # Get family group info
                family_group = self.get_family_group(customer_data["customer_name"])
                
                result = {
                    "customer": customer_data,
                    "is_family_member": False,
                    "family_group": None,
                    "primary_payer": None
                }
                
                if family_group:
                    if family_group.get("primary_payer") != customer_data["customer_name"]:
                        # If customer is not primary payer, get primary payer's info
                        primary_payer = self.search_customer_by_name(family_group["primary_payer"])
                        result.update({
                            "is_family_member": True,
                            "family_group": family_group,
                            "primary_payer": primary_payer
                        })
                    else:
                        result.update({
                            "family_group": family_group,
                            "primary_payer": customer_data
                        })
                
                return result
            
            return {}
            
        except Exception as e:
            print(f"Error in search: {str(e)}")
            return {}

    def get_family_group(self, customer_name: str) -> Dict[str, Any]:
        """Get family group information for a customer"""
        try:
            print(f"\nGetting family group for customer: {customer_name}")
            endpoint = f"{self.base_url}/api/resource/Family Group"
            
            # Get all active family groups
            response = self.session.get(endpoint, params={
                'fields': '["*"]',
                'filters': json.dumps([["status", "=", "Active"]])
            })
            
            print(f"Family groups response: {response.text}")
            
            if response.status_code == 200:
                data = response.json()
                all_groups = data.get('data', [])
                print(f"\nFound {len(all_groups)} family groups")
                
                for group in all_groups:
                    print(f"\nChecking group: {json.dumps(group, indent=2)}")
                    
                    # Get detailed group data including family members
                    group_response = self.session.get(f"{endpoint}/{group['name']}")
                    if group_response.status_code == 200:
                        group_data = group_response.json().get('data', {})
                        print(f"Detailed group data: {json.dumps(group_data, indent=2)}")
                        
                        # Check if primary payer
                        if group_data.get('primary_payer') == customer_name:
                            print(f"Found as primary payer in: {group_data.get('name')}")
                            return group_data
                        
                        # Check family members table
                        family_members = group_data.get('family_members', [])
                        print(f"Family members: {json.dumps(family_members, indent=2)}")
                        
                        for member in family_members:
                            print(f"Checking member: {member.get('member')} against {customer_name}")
                            if member.get('member') == customer_name:
                                print(f"Found as family member in: {group_data.get('name')}")
                                return group_data
                
                print("No matching family group found")
                return None
                
            else:
                print(f"Error getting family groups: {response.status_code}")
                print(f"Error response: {response.text}")
                return None
                
        except Exception as e:
            print(f"Error getting family group: {str(e)}")
            print(f"Error type: {type(e)}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            return None

    
    def verify_staff_rfid(self, rfid: str) -> Dict[str, Any]:
        """Verify if RFID belongs to authorized staff member"""
        try:
            print(f"Verifying staff RFID: {rfid}")
            
            # Get user with roles included
            user_endpoint = f"{self.base_url}/api/resource/User"
            user_response = self.session.get(
                user_endpoint,
                params={
                    'filters': json.dumps([
                        ["custom_user_rfid", "=", rfid],
                        ["enabled", "=", 1]
                    ]),
                    'fields': json.dumps([
                        "name", 
                        "full_name", 
                        "custom_user_rfid", 
                        "enabled",
                        "user_type",
                        "role_profile_name"
                    ])
                }
            )
            
            print(f"User response: {user_response.text}")
            
            if user_response.status_code == 200:
                users = user_response.json().get("data", [])
                
                if users:
                    user = users[0]
                    user_name = user.get("name")
                    
                    # Get user document with roles
                    detailed_user_endpoint = f"{self.base_url}/api/method/frappe.client.get"
                    detailed_response = self.session.get(
                        detailed_user_endpoint,
                        params={
                            'doctype': 'User',
                            'name': user_name
                        }
                    )
                    
                    print(f"Detailed user response: {detailed_response.text}")
                    
                    if detailed_response.status_code == 200:
                        user_data = detailed_response.json().get("message", {})
                        roles = [r.get("role") for r in user_data.get("roles", [])]
                        
                        print(f"User roles: {roles}")
                        
                        # Check if user has required roles
                        authorized_roles = ["Accounts User", "System Manager", "Administrator"]
                        if any(role in roles for role in authorized_roles):
                            return {
                                "verified": True,
                                "name": user.get("full_name"),
                                "roles": roles
                            }
                        else:
                            print(f"User doesn't have required roles. Required: {authorized_roles}, Has: {roles}")
                            return {
                                "verified": False,
                                "error": "User does not have required roles"
                            }
                
                return {
                    "verified": False,
                    "error": "Invalid RFID"
                }
                    
            return {
                "verified": False,
                "error": "Failed to verify user"
            }
                
        except Exception as e:
            print(f"Error verifying staff: {str(e)}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            return {
                "verified": False,
                "error": str(e)
            }

    def get_customer_transactions(self, customer_name: str) -> Dict[str, Any]:
        """Get all transactions and details for a customer"""
        try:
            print(f"\nFetching transactions for customer: {customer_name}")
            
            # First get customer details
            customer = self.search_customer_by_name(customer_name)
            if not customer:
                print(f"No customer found with name: {customer_name}")
                return {"data": []}
                    
            print(f"Found customer: {customer.get('customer_name')}")

            # Check if customer is part of a family group
            family_group = self.get_family_group(customer_name)
            if family_group and family_group.get('primary_payer') != customer_name:
                # If customer is a family member, get primary payer's transactions
                print(f"Customer is family member, getting primary payer's transactions")
                customer_name = family_group.get('primary_payer')
                print(f"Using primary payer: {customer_name}")

            # Get invoices using the working API method
            api_endpoint = f"{self.base_url}/api/method/frappe.client.get_list"
            params = {
                'doctype': 'Sales Invoice',
                'fields': '["*"]',
                'filters': json.dumps({
                    'customer': customer_name
                })
            }
            
            response = self.session.get(api_endpoint, params=params)
            print(f"Invoice response status: {response.status_code}")
            print(f"Invoice response: {response.text}")

            if response.status_code == 200:
                data = response.json()
                transactions = []
                
                for inv in data.get('message', []):
                    transactions.append({
                        'type': 'Sales Invoice',
                        'data': {
                            'name': inv.get('name'),
                            'posting_date': inv.get('posting_date'),
                            'due_date': inv.get('due_date'),
                            'grand_total': inv.get('grand_total', 0.0),
                            'outstanding_amount': inv.get('outstanding_amount', 0.0),
                            'status': inv.get('status', 'Unknown'),
                            'remarks': inv.get('remarks', '')
                        }
                    })
                    
                print(f"Found {len(transactions)} transactions")
                return {"data": transactions}
                
            print(f"No transactions found, status code: {response.status_code}")
            return {"data": []}

        except Exception as e:
            print(f"Error in get_customer_transactions: {str(e)}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            return {"data": []}

def get_erp_client():
    return ERPNextClient(
        base_url=os.getenv("ERPNEXT_URL"),
        api_key=os.getenv("ERPNEXT_API_KEY"),
        api_secret=os.getenv("ERPNEXT_API_SECRET")
    )