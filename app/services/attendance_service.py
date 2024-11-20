from datetime import datetime, timedelta
import json
from collections import Counter
import calendar

class AttendanceService:
    def __init__(self, erp_client):
        self.erp_client = erp_client

    async def get_customer_attendance(self, customer_name: str, week_offset: int = 0) -> dict:
        try:
            # Fetch customer data
            customer = self.erp_client.search_customer_by_name(customer_name)
            if not customer:
                return self._create_empty_response(customer_name)

            # Get attendance data and handle empty/None case
            attendance_data = customer.get("custom_attendance", "[]")
            if attendance_data is None:
                attendance_data = "[]"

            # Parse attendance dates
            try:
                dates = json.loads(attendance_data)
                valid_dates = []
                for date_str in dates:
                    try:
                        # Clean and parse date string
                        cleaned_date = str(date_str).strip().replace('"', '')
                        if 'T' in cleaned_date:
                            dt = datetime.fromisoformat(cleaned_date.split('.')[0])
                            valid_dates.append(dt)
                    except (ValueError, TypeError) as e:
                        print(f"Invalid date: {date_str} - {e}")
                        continue
            except json.JSONDecodeError:
                valid_dates = []

            # Calculate week boundaries
            today = datetime.now()
            start_of_current_week = today - timedelta(days=today.weekday())
            target_week_start = start_of_current_week + timedelta(weeks=week_offset)
            target_week_end = target_week_start + timedelta(days=6)

            # Filter dates for the target week
            week_attendance = [
                date for date in valid_dates
                if target_week_start <= date <= target_week_end
            ]

            # Create week calendar
            week_calendar = []
            for i in range(7):
                current_date = target_week_start + timedelta(days=i)
                attended = any(d.date() == current_date.date() for d in week_attendance)
                week_calendar.append({
                    'date': current_date.strftime('%Y-%m-%d'),
                    'day_name': current_date.strftime('%A'),
                    'day': current_date.strftime('%d'),
                    'attended': attended,
                    'times': [
                        d.strftime('%I:%M %p') 
                        for d in week_attendance 
                        if d.date() == current_date.date()
                    ]
                })

            # Process image URL
            image_url = ""
            raw_image = customer.get("image", "")
            if isinstance(raw_image, str) and raw_image:
                image_url = raw_image.split('/')[-1]

            return {
                "customer": {
                    "name": customer.get("customer_name", ""),
                    "belt_rank": customer.get("custom_current_belt_rank", "Not assigned"),
                    "image": image_url
                },
                "week_info": {
                    "start_date": target_week_start.strftime('%Y-%m-%d'),
                    "end_date": target_week_end.strftime('%Y-%m-%d'),
                    "current_week": week_offset == 0,
                    "week_number": target_week_start.isocalendar()[1]
                },
                "calendar": week_calendar,
                "summary": {
                    "total_classes": len(valid_dates),
                    "classes_this_week": len(week_attendance)
                }
            }

        except Exception as e:
            print(f"Error processing attendance: {str(e)}")
            return self._create_empty_response(customer_name)

    def _create_empty_response(self, customer_name: str) -> dict:
        """Create an empty response structure when no data is available"""
        today = datetime.now()
        start_of_current_week = today - timedelta(days=today.weekday())
        
        # Create empty week calendar
        week_calendar = []
        for i in range(7):
            current_date = start_of_current_week + timedelta(days=i)
            week_calendar.append({
                'date': current_date.strftime('%Y-%m-%d'),
                'day_name': current_date.strftime('%A'),
                'day': current_date.strftime('%d'),
                'attended': False,
                'times': []
            })

        return {
            "customer": {
                "name": customer_name,
                "belt_rank": "Not assigned",
                "image": ""
            },
            "week_info": {
                "start_date": start_of_current_week.strftime('%Y-%m-%d'),
                "end_date": (start_of_current_week + timedelta(days=6)).strftime('%Y-%m-%d'),
                "current_week": True,
                "week_number": start_of_current_week.isocalendar()[1]
            },
            "calendar": week_calendar,
            "summary": {
                "total_classes": 0,
                "classes_this_week": 0
            }
        }