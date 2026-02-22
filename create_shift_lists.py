
from parse_json import get_shift_groups_for_day
from test_dataextraction_holiday import check_if_person_working_today

from coverage import calculate_coverage_from_shifts
from datetime import datetime, timedelta
import os
import pandas as pd

def get_filtered_shifts(schedule_data, df, excel_date, test=False,working_codes=[]):
    """
    Returns a dictionary of shift types mapped to employees who are working on a specific date.
    Args:
        schedule_data (dict): Already loaded schedule JSON.
        df (pd.DataFrame): Holiday tracker Excel sheet loaded as a DataFrame.
        excel_date (str): Date string in DD/MM/YYYY format.
        test (bool): If True, enables print statements and testing output.
    Returns:
        dict: {shift_type: [employee_logins]} for those actually working on the date.
        str: Coverage string like "06:30-23:00" or "06:30-08:00" for overnight
    """
    if test:
        print(f"{'='*60}")
        print(f"Testing get_filtered_shifts for date: {excel_date}")
        print(f"{'='*60}")
    
    # Parse date and get day abbreviation
    date_obj = datetime.strptime(excel_date, "%d/%m/%Y")
    day_abbr = date_obj.strftime("%a")  # 'Mon', 'Tue', etc.
    
    if test:
        print(f"Parsed date: {date_obj}")
        print(f"Day abbreviation: {day_abbr}")
    
    # Get shift groups for the day
    shift_lists = get_shift_groups_for_day(schedule_data, day_abbr)
    
    if test:
        print(f"Shift groups for {day_abbr}:")
        for shift_type, names in shift_lists.items():
            if shift_type != "coverage":
                print(f"  {shift_type}: {len(names)} employees - {names}")
    
    # Filter by employees actually working
    filtered = {}
    all_shift_times = []  # Collect all shift times from working employees
    
    if test:
        print(f"{'='*60}")
        print("Filtering employees by working status:")
        print(f"{'='*60}")
    
    for shift_type, names in shift_lists.items():
        if shift_type == "coverage":
            continue
        filtered[shift_type] = []
        
        if test:
             print(f"{shift_type.upper()} Shift:")
        
        for login in names:
            status = check_if_person_working_today(excel_date, login, df)
            
            if test:
                print(f"  {login}: {status}")
            
            if status == "Working":
                filtered[shift_type].append(login)
                
                # Get this person's shift time from schedule_data
                if login in schedule_data and day_abbr in schedule_data[login]:
                    shift_time = schedule_data[login][day_abbr]
                    all_shift_times.append(shift_time)
                    if test:
                        print(f"-> Added to {shift_type}, shift time: {shift_time}")
        
            
    if test:
        print(f"{'='*60}")
        print("Calculating coverage from actual shift times:")
        print(f"{'='*60}")
        print(f"All shift times collected: {all_shift_times}")
    
    # Use the coverage calculation function
    coverage_str, hours_breakdown = calculate_coverage_from_shifts(all_shift_times, test=test)
    
    if test:
        print(f"{'='*60}")
        print("FINAL RESULTS:")
        print(f"{'='*60}")
        print(f"Filtered shifts (working employees only):")
        for shift_type, names in filtered.items():
            print(f"  {shift_type}: {len(names)} employees - {names}")
        print(f"Coverage: {coverage_str}")
        print(f"{'='*60}")
    
    return filtered, coverage_str


# Testing code - set test=True to enable
if __name__ == "__main__":
    TEST_MODE = False # Change this to True to enable testing
    
    if TEST_MODE:
        import pandas as pd
        import json
        
        print("Loading test data...")
        import json
    file_path = r"C:\Users\avikann\rota\schedule.json"

    # Check if file exists
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
    else:
        print(f"File found: {file_path}")
        try:
            with open(file_path) as f:
                schedule_data = json.load(f)
            print("JSON loaded successfully!")
            print(f"Keys in schedule_data: {list(schedule_data.keys())[:5]}")  # Show first 5 keys
        except json.JSONDecodeError as e:
            print(f"Invalid JSON format: {e}")
        except Exception as e:
            print(f"Error loading file: {e}")
        
        # Load holiday tracker
        df = pd.read_excel(r"C:\Users\avikann\Documents\holiday_tracker.xlsx")
        
        # Test dates
        test_dates = [
            "12/12/2025",  # Today (Saturday)
            
        ]
        
        for test_date in test_dates:
            filtered, coverage = get_filtered_shifts(
                schedule_data, 
                df, 
                test_date, 
                test=True
            )
            
            # Add a separator between test runs
            print(f"" + "="*60 + "")

else: 
    print("Testing disabled. Set TEST_MODE = True to enable testing.")