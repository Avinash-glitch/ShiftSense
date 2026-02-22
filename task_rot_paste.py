import streamlit as st
import pandas as pd
import re
from datetime import datetime, timedelta
import random
from collections import deque
import io
import json
from pathlib import Path
import math
import copy
import os
import io

# Page configuration
st.set_page_config(
    page_title="Amazon Rota System",
    page_icon="📅",
    layout="wide"
)

st.title("📅 Amazon Rota System Generator")
st.markdown("Generate weekly task assignments with fair rotation tracking")

# === ASSIGNMENT HISTORY MANAGEMENT ===
class AssignmentTracker:
    """Track assignment history to ensure fair rotation"""
    
    def __init__(self, history_file='assignment_history.json'):
        self.history_file = history_file
        self.history = self.load_history()
    
    def load_history(self):
        """Load assignment history from file"""
        if Path(self.history_file).exists():
            try:
                with open(self.history_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def save_history(self):
        """Save assignment history to file"""
        with open(self.history_file, 'w') as f:
            json.dump(self.history, f, indent=2)
    
    def _key(self, person, task_type):
        return f"{person}_{task_type}"
    
    def get_last_assignment(self, person, task_type):
        """Get the last assignment date for a person and task type"""
        key = self._key(person, task_type)
        if key in self.history and 'last_date' in self.history[key]:
            try:
                return datetime.fromisoformat(self.history[key]['last_date'])
            except:
                return None
        return None
    
    def get_assignment_count(self, person, task_type, weeks=52):
        """Get assignment count for a person in the last N weeks (default 52 weeks)"""
        key = self._key(person, task_type)
        if key not in self.history:
            return 0
        
        cutoff_date = datetime.now() - timedelta(weeks=weeks)
        count = 0
        for date_str in self.history[key].get('dates', []):
            try:
                if datetime.fromisoformat(date_str) > cutoff_date:
                    count += 1
            except:
                pass
        return count
    
    def record_assignment(self, person, task_type, date):
        """Record a new assignment"""
        key = self._key(person, task_type)
        if key not in self.history:
            self.history[key] = {'dates': [], 'total_count': 0}
        
        date_str = date.isoformat() if isinstance(date, datetime) else date
        self.history[key]['dates'].append(date_str)
        self.history[key]['last_date'] = date_str
        self.history[key]['total_count'] = self.history[key].get('total_count', 0) + 1
        
        cutoff_date = datetime.now() - timedelta(weeks=52)
        self.history[key]['dates'] = [
            d for d in self.history[key]['dates']
            if (lambda ds: (datetime.fromisoformat(ds) > cutoff_date) if isinstance(ds, str) and ds.count("-")>=2 else False)(d)
        ]
    
    def can_assign(self, person, task_type, current_date, min_days_gap=5):
        """Check if a person can be assigned to a task (enforces min days gap)"""
        last_assignment = self.get_last_assignment(person, task_type)
        if last_assignment is None:
            return True
        
        if isinstance(current_date, str):
            try:
                current_date = datetime.strptime(current_date, "%a %m/%d/%Y")
            except:
                return True
        
        days_since_last = (current_date - last_assignment).days
        return days_since_last >= min_days_gap
    
    def get_eligible_sorted(self, people_list, task_type, current_date, min_days_gap=5, weeks_for_count=52):
        """Get eligible people sorted by assignment count (fairness)"""
        eligible = []
        for person in people_list:
            if self.can_assign(person, task_type, current_date, min_days_gap):
                count = self.get_assignment_count(person, task_type, weeks=weeks_for_count)
                eligible.append((person, count))
        
        eligible.sort(key=lambda x: (x[1], x[0]))
        return [person for person, count in eligible]


# === SHIFT LEGENDS (kept for compatibility) ===
SHIFT_LEGENDS = {
    'S1': {'description': 'Early Morning Shift', 'time': '05:00-08:30', 'type': 'Morning'},
    'S2': {'description': 'Morning Shift', 'time': '09:00-13:00', 'type': 'Mid'},
    'S3': {'description': 'Afternoon Shift', 'time': '13:30-18:30', 'type': 'Mid'},
    'S4': {'description': 'Night Shift', 'time': '19:00-04:30', 'type': 'Night'},
    'OT': {'description': 'Overtime', 'time': 'Variable', 'type': 'NA'},
    'H': {'description': 'Holiday', 'time': 'Off', 'type': 'Holiday'},
    'BH': {'description': 'Bank holiday', 'time': 'Off', 'type': 'Holiday'},
    'S': {'description': 'Sick leave', 'time': 'Off', 'type': 'Holiday'},
    'PL': {'description': 'Personal Leave', 'time': 'Off', 'type': 'Holiday'},
    'UPL': {'description': 'Unpaid Leave', 'time': 'Off', 'type': 'Holiday'},
    'M/P': {'description': 'Maternity/Paternity leave', 'time': 'Off', 'type': 'Holiday'}
}


# functions to load fixed schedule JSON and rota_holiday.xlsx, then merge ===
def load_schedule_and_holiday_data(schedule_path='schedule.json', holiday_file=None):
    """Load schedule.json and rota_holiday file"""

    # Load schedule.json
    schedule_data = None
    if Path(schedule_path).exists():
        with open(schedule_path, 'r') as f:
            schedule_data = json.load(f)

    # Load rota_holiday - handle corrupted Excel files
    #rota_df = None
    if holiday_file is not None:
        try:
            holiday_file.seek(0)

            # Try reading as tab-separated CSV first (works for corrupted Excel)
            try:
                content = holiday_file.read()
                if isinstance(content, bytes):
                    content = content.decode('utf-8')
                rota_df = pd.read_csv(io.StringIO(content), sep='\t')
            except:
                # Try regular CSV
                holiday_file.seek(0)
                rota_df = pd.read_csv(holiday_file)

                # Remove any header rows with "Week" text
                if rota_df is not None and len(rota_df) > 0:
                    if any('Week' in str(val) for val in rota_df.values.flatten() if pd.notna(val)):
                        rota_df = rota_df.iloc[1:].reset_index(drop=True)


                # Ensure Login column exists
                if 'Login' not in rota_df.columns:
                    rota_df = rota_df.rename(columns={rota_df.columns: 'Login'})

                return schedule_data, rota_df
        except Exception as e:
            st.sidebar.error(f"Error reading file: {str(e)}")
            return schedule_data, None

    return schedule_data, None



def try_load_holiday_file(uploaded_file):
    """Load and parse the holiday file (auto-detect delimiter)"""
    try:
        uploaded_file.seek(0)
        content = uploaded_file.read()
        if isinstance(content, bytes):
            content = content.decode('utf-8')

        # Try to detect the delimiter by checking the first few lines
        lines = content.split('
')[:3]

        # Check if it's tab-separated or comma-separated
        if '\t' in lines:  # Row 3 should have tabs
            delimiter = '\t'
            st.sidebar.info("📋 Detected tab-separated file")
        elif ',' in lines:
            delimiter = ','
            st.sidebar.info("📋 Detected comma-separated file")
        else:
            st.sidebar.error("❌ Could not detect file delimiter")
            return None

        # Read with detected delimiter, skipping first 2 rows
        df = pd.read_csv(io.StringIO(content), sep=delimiter, skiprows=2)

        # Debug: Show what columns we got
        st.sidebar.info(f"📋 First 3 columns: {df.columns.tolist()[:3]}")

        # Check if Login column exists
        if 'Login' not in df.columns:
            st.sidebar.error(f"❌ 'Login' column not found!")
            st.sidebar.error(f"All columns: {df.columns.tolist()}")
            return None

        # Rename day columns based on structure
        # For tab-separated: Week 45, Unnamed: 8-13
        # For comma-separated: might be different
        rename_dict = {}

        # Find columns that look like day columns (after Manager column)
        cols = df.columns.tolist()
        if 'Manager' in cols:
            manager_idx = cols.index('Manager')
            day_cols = cols[manager_idx + 1:]  # Columns after Manager

            # Map to day names
            day_names = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
            for i, col in enumerate(day_cols[:7]):  # Take first 7 columns after Manager
                rename_dict[col] = day_names[i]

        if not rename_dict:
            st.sidebar.error("❌ Could not identify day columns")
            return None

        df = df.rename(columns=rename_dict)

        st.sidebar.info(f"📋 Renamed columns: {list(rename_dict.values())}")

        # Set Login as index
        df = df.set_index('Login')

        # Keep only day columns
        day_columns = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
        existing_days = [col for col in day_columns if col in df.columns]

        if not existing_days:
            st.sidebar.error("❌ No day columns found after renaming!")
            return None

        df = df[existing_days]

        return df

    except Exception as e:
        st.sidebar.error(f"❌ Error reading holiday file: {str(e)}")
        import traceback
        st.sidebar.error(traceback.format_exc())
        return None


def is_on_holiday(status):
    """
    Check if an employee is on holiday.
    Returns True if status is anything OTHER than S1, S2, S3, S4.
    """
    if pd.isna(status) or status == '':
        return False
    if status in ['S1', 'S2', 'S3', 'S4']:
        return False
    return True

def get_working_logins(df, date_column):
    """
    Get list of employee logins who are working (S1, S2, S3, S4) on a specific date.
    """
    working_logins = []

    for login in df.index:
        status = df.loc[login, date_column]
        if pd.notna(status) and status in ['S1', 'S2', 'S3', 'S4']:
            working_logins.append(login)

    return working_logins

def get_holiday_logins(df, date_column):
    """
    Get dictionary of employee logins on holiday/unavailable.
    Returns {login: holiday_code} for H, PL, BH, etc.
    """
    holiday_logins = {}

    for login in df.index:
        status = df.loc[login, date_column]
        if is_on_holiday(status):
            holiday_logins[login] = status

    return holiday_logins

def weekday_abbrev_to_full(abbrev):
    mapping = {
        "Sun": "Sunday",
        "Mon": "Monday",
        "Tue": "Tuesday",
        "Wed": "Wednesday",
        "Thu": "Thursday",
        "Fri": "Friday",
        "Sat": "Saturday"
    }
    return mapping.get(abbrev, abbrev)

def build_availability_matrix(schedule_data, holiday_df, days_of_week):
    """
    Build availability matrix combining schedule.json (shift times)
    and holiday_df (S1/S2/S3/S4 vs H/BH/PL)
    """
    availability = {}

    day_mapping = {
        'Sun': 'Sunday', 'Mon': 'Monday', 'Tue': 'Tuesday',
        'Wed': 'Wednesday', 'Thu': 'Thursday', 'Fri': 'Friday', 'Sat': 'Saturday'
    }

    for emp_login, emp_data in schedule_data.items():
        availability[emp_login] = {}

        for day_str in days_of_week:
            # Extract day abbreviation (e.g., "Mon" from "Mon 11/03/2025")
            day_abbrev = day_str.split()
            day_full = day_mapping.get(day_abbrev, day_abbrev)

            # Check holiday status from holiday_df
            if holiday_df is not None and emp_login in holiday_df.index:
                status_code = holiday_df.loc[emp_login, day_full]

                # If on holiday (H, BH, PL, etc.), mark as unavailable
                if is_on_holiday(status_code):
                    availability[emp_login][day_full] = {
                        'status': 'Holiday',
                        'shift_type': None,
                        'holiday_code': status_code
                    }
                    continue

            # If working (S1/S2/S3/S4), get shift details from schedule.json
            if day_abbrev in emp_data:
                shift_info = emp_data[day_abbrev]
                availability[emp_login][day_full] = {
                    'status': 'Working',
                    'shift_type': shift_info.get('shift_type'),
                    'start_time': shift_info.get('start_time'),
                    'end_time': shift_info.get('end_time')
                }
            else:
                availability[emp_login][day_full] = {
                    'status': 'Off',
                    'shift_type': None
                }

    return availability

# === existing helper functions (mostly unchanged) ===

def get_shift_type(shift_str):
    """Classify shift as Morning, Mid, Night, Holiday, Off, or NA - kept for compatibility"""
    if pd.isna(shift_str) or str(shift_str).strip() == "":
        return "Off"
    
    shift_str = str(shift_str).strip()
    
    # Check for S1, S2, S3 shift codes
    if shift_str == 'S1':
        return "Morning"
    elif shift_str == 'S2':
        return "Mid"
    elif shift_str == 'S3':
        return "Night"
    
    # Check if it's in SHIFT_LEGENDS
    if shift_str in SHIFT_LEGENDS:
        return SHIFT_LEGENDS[shift_str]['type']
    
    return "NA"

def get_shift_value(row, day_col):
    """Return the shift status for a row and day column"""
    val = row.get(day_col, "")
    if pd.isna(val):
        return ""
    if isinstance(val, str):
        return val.strip()
    return val

def extract_dates_from_schedule(df):
    """If a schedule with dates is uploaded, attempt to extract days row (kept for compatibility).
    If not present we will rely on the days input text area."""
    days_with_dates = []
    
    # Find day columns (Sunday, Monday, etc.)
    day_cols = []
    for i, col in enumerate(df.columns):
        col_str = str(col)
        if any(day in col_str for day in ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']):
            day_cols.append((i, col_str))
    
    # Get dates from first row (row 0)
    if len(df) > 0:
        date_row = df.iloc[0]
        for idx, day_name in day_cols:
            date_val = date_row.iloc[idx] if idx < len(date_row) else None
            if pd.notna(date_val):
                try:
                    # Handle datetime objects directly
                    if isinstance(date_val, datetime):
                        formatted_date = date_val.strftime("%m/%d/%Y")
                        days_with_dates.append(f"{day_name} {formatted_date}")
                    else:
                        # Try parsing string format
                        date_str = str(date_val)
                        if '-' in date_str:
                            day_part, month_part = date_str.split('-')
                            date_obj = datetime.strptime(f"{day_part}-{month_part}-2025", "%d-%b-%Y")
                            formatted_date = date_obj.strftime("%m/%d/%Y")
                            days_with_dates.append(f"{day_name} {formatted_date}")
                except Exception as e:
                    pass
    
    return days_with_dates

def process_schedule_csv(df):
    """Kept for backwards compatibility but we will not depend on it for shift types anymore."""
    # Skip the first row (dates) and start from row 1
    df = df.iloc[1:].reset_index(drop=True)
    
    # Find login column
    login_col = None
    for col in df.columns:
        if 'login' in str(col).lower():
            login_col = col
            break
    
    if login_col is None:
        login_col = df.columns[0]
    
    df = df.rename(columns={login_col: 'login'})
    
    # Find day columns (Sunday, Monday, etc.)
    day_start_idx = None
    for i, col in enumerate(df.columns):
        if any(day in str(col) for day in ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']):
            day_start_idx = i
            break
    
    if day_start_idx is None:
        day_start_idx = 7  # Default to column 7
    
    day_columns = df.columns[day_start_idx:]
    
    # Clean data
    df = df[df['login'].notna()]
    df = df[df['login'] != 'Login']
    df = df.reset_index(drop=True)
    
    # Melt and process
    long_df = df.melt(id_vars=["login"], value_vars=day_columns, var_name="Day", value_name="Shift")
    long_df["ShiftType"] = long_df["Shift"].apply(get_shift_type)
    
    shift_summary = (
        long_df[long_df["ShiftType"].isin(["Morning", "Mid", "Night"])]
        .groupby("login")["ShiftType"]
        .agg(lambda x: x.mode().iloc[0] if not x.mode().empty else "NA")
        .reset_index()
    )
    shift_summary.columns = ['login', 'ShiftType']
    
    holiday_off_df = long_df.pivot_table(
        index="login", columns="Day", values="ShiftType", aggfunc="first"
    ).fillna("Off")
    
    return shift_summary, holiday_off_df

def extract_s2_shift_mapping(df):
    """
    Dynamically extract S2 employee shift patterns from uploaded schedule (kept for compatibility)
    Returns dict with S2_MORNING and S2_MID employee lists
    """
    s2_morning = []  # 09:30-18:00
    s2_mid = []      # 11:30-20:00

    # Skip first row if it contains dates
    data_df = df.iloc[1:] if len(df) > 1 else df

    for idx, row in data_df.iterrows():
        login = row.get('login', row.iloc) if 'login' in row else row.iloc
        if pd.isna(login) or login == 'login':
            continue

        shifts = []
        for col in data_df.columns[1:]:
            shift_val = str(row[col]).strip() if pd.notna(row[col]) else ""
            if shift_val:
                shifts.append(shift_val)

        # Check if person works S2 shifts
        has_morning_s2 = any('09:30-18:00' in s for s in shifts)
        has_mid_s2 = any('11:30-20:00' in s for s in shifts)

        if has_morning_s2:
            s2_morning.append(str(login).strip())
        if has_mid_s2:
            s2_mid.append(str(login).strip())

    return {
        'S2_MORNING': s2_morning,
        'S2_MID': s2_mid
    }

def select_people_for_slots(tracker, candidates, task_type, current_date, slots=1, min_days_gap=5, weeks_for_count=52, total_slots=1):
    """
    Select people with RANDOMIZATION for variety across regenerations
    """
    candidates = list(candidates)
    if not candidates:
        return []
    
    num_people = len(candidates)
    if num_people == 0:
        return []
    
    soft_max = max(1, math.ceil(total_slots / num_people))
    
    eligible = tracker.get_eligible_sorted(candidates, task_type, current_date, min_days_gap=min_days_gap, weeks_for_count=weeks_for_count)
    
    if not eligible:
        eligible = tracker.get_eligible_sorted(candidates, task_type, current_date, min_days_gap=max(1, min_days_gap-1), weeks_for_count=weeks_for_count)
        if not eligible:
            eligible = tracker.get_eligible_sorted(candidates, task_type, current_date, min_days_gap=0, weeks_for_count=weeks_for_count)
            if not eligible:
                return []
    
    # ADD RANDOMIZATION: shuffle people with the same assignment count
    count_groups = {}
    for person in eligible:
        count = tracker.get_assignment_count(person, task_type, weeks=weeks_for_count)
        if count not in count_groups:
            count_groups[count] = []
        count_groups[count].append(person)
    
    randomized_eligible = []
    for count in sorted(count_groups.keys()):
        group = count_groups[count]
        random.shuffle(group)
        randomized_eligible.extend(group)
    
    eligible = randomized_eligible
    
    under_limit = [p for p in eligible if tracker.get_assignment_count(p, task_type, weeks=weeks_for_count) < soft_max]
    
    chosen = []
    for p in under_limit:
        if len(chosen) >= slots:
            break
        chosen.append(p)
    
    if len(chosen) < slots:
        remaining = [p for p in eligible if p not in chosen]
        for p in remaining:
            if len(chosen) >= slots:
                break
            chosen.append(p)
    
    return chosen

def generate_rota_from_availability(availability, hypercare_list, hyd_team, days_of_week, break_schedule, tracker):
    """Generate rota assignments from availability matrix with fair rotation"""

    date_columns = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']

    def get_working_by_shift(day, shift_type):
        employees = []
        for emp, days in availability.items():
            day_info = days.get(day, {})
            if day_info.get('status') == 'Working' and day_info.get('shift_type') == shift_type:
                employees.append(emp)
        return employees

    def get_all_working(day):
        employees = []
        for emp, days in availability.items():
            day_info = days.get(day, {})
            if day_info.get('status') == 'Working':
                employees.append(emp)
        return employees

    rota_table = []
    total_days = len(days_of_week)

    # Header row
    header_row = {
        "Day": "WIMS Status",
        "Hypercare": "on project",
        "SIMs": "Available",
        "DOR Call": "In meeting",
        "WIMS Cases": "Available",
        "EOD Report": "On Project",
        "WIMS Breaks": break_schedule
    }
    rota_table.append(header_row)

    for idx, (date_str, day_name) in enumerate(zip(days_of_week, date_columns)):
        day_abbrev = date_str.split()
        is_weekend = day_abbrev in ["Sun", "Sat"]

        # Parse date
        try:
            current_date = datetime.strptime(date_str, "%a %m/%d/%Y")
        except:
            current_date = datetime.now() + timedelta(days=idx)

        all_working = get_all_working(day_name)
        morning_shift = get_working_by_shift(day_name, 'Morning')
        mid_shift = get_working_by_shift(day_name, 'Mid')
        night_shift = get_working_by_shift(day_name, 'Night')

        assigned_today = set()

        # 1. HYPERCARE
        working_hypercare = [p for p in hypercare_list if p in all_working]
        target_hypercare_slots = 1 if is_weekend else 2
        hypercare_selected = select_people_for_slots(
            tracker, working_hypercare, "Hypercare", current_date,
            slots=target_hypercare_slots, min_days_gap=2, weeks_for_count=52, total_slots=total_days
        )
        for person in hypercare_selected:
            tracker.record_assignment(person, 'Hypercare', current_date)
            assigned_today.add(person)

        # 2. SIMs COVERAGE
        sims_parts = []

        # AM
        available_morning = [p for p in morning_shift if p not in assigned_today]
        am_selected = select_people_for_slots(
            tracker, available_morning, "SIMs_AM", current_date,
            slots=1, min_days_gap=1, weeks_for_count=52, total_slots=total_days
        )
        if am_selected:
            morning_sim = am_selected
            sims_parts.append(f"AM: {morning_sim}")
            tracker.record_assignment(morning_sim, 'SIMs_AM', current_date)
            assigned_today.add(morning_sim)

        # PM
        available_mid = [p for p in mid_shift if p not in assigned_today]
        pm_selected = select_people_for_slots(
            tracker, available_mid, "SIMs_PM", current_date,
            slots=1, min_days_gap=1, weeks_for_count=52, total_slots=total_days
        )
        if pm_selected:
            mid_sim = pm_selected
            sims_parts.append(f"PM: {mid_sim}")
            tracker.record_assignment(mid_sim, 'SIMs_PM', current_date)
            assigned_today.add(mid_sim)

        # Night (prefer HYD)
        hyd_night_cands = [p for p in night_shift if p in hyd_team and p not in assigned_today]
        night_selected = select_people_for_slots(
            tracker, hyd_night_cands, "SIMs_Night", current_date,
            slots=1, min_days_gap=1, weeks_for_count=52, total_slots=total_days
        )
        if night_selected:
            night_sim = night_selected
            sims_parts.append(f"Night: {night_sim}")
            tracker.record_assignment(night_sim, 'SIMs_Night', current_date)
            assigned_today.add(night_sim)
        else:
            sims_parts.append("Night: HYD (no coverage)")

        sims_text = " | ".join(sims_parts)

        # 3. DOR CALL
        dor_assigned = []
        if not is_weekend:
            available_for_dor = [p for p in all_working if p not in assigned_today]
            dor_selected = select_people_for_slots(
                tracker, available_for_dor, "DOR_Call", current_date,
                slots=1, min_days_gap=1, weeks_for_count=52, total_slots=total_days
            )
            if dor_selected:
                dor_person = dor_selected
                dor_assigned = [dor_person]
                tracker.record_assignment(dor_person, 'DOR_Call', current_date)
                assigned_today.add(dor_person)

        # 4. EOD REPORT
        eligible_eod_pool = set(mid_shift + night_shift) | (set(hyd_team) & set(all_working))
        available_for_eod = [p for p in eligible_eod_pool if p not in assigned_today]
        eod_selected = select_people_for_slots(
            tracker, available_for_eod, "EOD_Report", current_date,
            slots=1, min_days_gap=1, weeks_for_count=52, total_slots=total_days
        )
        eod_assigned = []
        if eod_selected:
            eod_person = eod_selected
            eod_assigned = [eod_person]
            tracker.record_assignment(eod_person, 'EOD_Report', current_date)
            assigned_today.add(eod_person)

        # 5. WIMS CASES
        wims_pool = [p for p in all_working if p not in assigned_today]

        row = {
            "Day": date_str,
            "Hypercare": ", ".join(hypercare_selected),
            "SIMs": sims_text,
            "DOR Call": ", ".join(dor_assigned),
            "WIMS Cases": ", ".join(wims_pool),
            "EOD Report": ", ".join(eod_assigned),
            "WIMS Breaks": break_schedule
        }
        rota_table.append(row)

    return pd.DataFrame(rota_table)

def create_daily_statistics_table(holiday_off_df, task_table, days_of_week):
    """Create statistics table"""
    stats_data = []
    
    for day in days_of_week:
        day_name = day.split()[0]
        
        day_col = None
        if day in holiday_off_df.columns:
            day_col = day
        else:
            matches = [c for c in holiday_off_df.columns if c.startswith(day_name)]
            if matches:
                day_col = matches[0]
        
        if day_col is None:
            continue
        
        working_count = 0
        holiday_count = 0
        off_count = 0
        morning_count = 0
        mid_count = 0
        night_count = 0
        
        for idx, row in holiday_off_df.iterrows():
            shift_type = row.get(day_col, "Off")
            
            if shift_type == "Morning":
                morning_count += 1
                working_count += 1
            elif shift_type == "Mid":
                mid_count += 1
                working_count += 1
            elif shift_type == "Night":
                night_count += 1
                working_count += 1
            elif shift_type == "Holiday":
                holiday_count += 1
            elif shift_type == "Off":
                off_count += 1
        
        task_row = task_table[task_table['Day'] == day]
        
        if not task_row.empty and task_row.iloc[0]['Day'] != 'WIMS Status':
            row_data = task_row.iloc[0]
            
            hypercare_str = str(row_data.get('Hypercare', ''))
            hypercare_count = len([x for x in hypercare_str.split(',') if x.strip()]) if hypercare_str else 0
            
            sims_str = str(row_data.get('SIMs', ''))
            sims_count = sims_str.count('|') + 1 if sims_str else 0
            
            dor_str = str(row_data.get('DOR Call', ''))
            dor_count = len([x for x in dor_str.split(',') if x.strip()]) if dor_str else 0
            
            eod_str = str(row_data.get('EOD Report', ''))
            eod_count = len([x for x in eod_str.split(',') if x.strip()]) if eod_str else 0
            
            wims_str = str(row_data.get('WIMS Cases', ''))
            wims_count = len([x for x in wims_str.split(',') if x.strip()]) if wims_str else 0
        else:
            is_weekend = day_name in ["Sun", "Sat"]
            hypercare_count = 1 if is_weekend else 2
            sims_count = 3
            dor_count = 0 if day_name in ["Sun", "Sat"] else 1
            eod_count = 1
            wims_count = max(0, working_count - hypercare_count - dor_count - eod_count)
        
        stats_row = {
            "Day": day,
            "Total Working": working_count,
            "Morning Shift": morning_count,
            "Mid Shift": mid_count,
            "Night Shift": night_count,
            "On Holiday": holiday_count,
            "Day Off": off_count,
            "Hypercare": hypercare_count,
            "SIMs Coverage": sims_count,
            "DOR Call": dor_count,
            "EOD Report": eod_count,
            "WIMS Cases": wims_count
        }
        stats_data.append(stats_row)
    
    return pd.DataFrame(stats_data)


# === Streamlit UI ===

if 'tracker' not in st.session_state:
    st.session_state.tracker = AssignmentTracker()

if 'generated_rotas' not in st.session_state:
    st.session_state.generated_rotas = []

df = None

st.sidebar.header("⚙️ Configuration")

uploaded_holiday_file = st.sidebar.file_uploader("Upload rota_holiday CSV/Excel (Option A format)", type=['csv', 'xlsx'])

# Attempt to load fixed schedule JSON automatically
# Load schedule.json
# Load schedule.json
schedule_path = "schedule.json"
schedule_data = None
if Path(schedule_path).exists():
    try:
        with open(schedule_path, 'r') as f:
            schedule_data = json.load(f)
        st.sidebar.success("✅ schedule.json loaded successfully")
    except Exception as e:
        st.sidebar.error(f"❌ Error loading schedule.json: {str(e)}")

# Load holiday file
holiday_df = None
if uploaded_holiday_file is not None:
    holiday_df = try_load_holiday_file(uploaded_holiday_file)
    if holiday_df is not None:
        st.sidebar.success(f"✅ Holiday file loaded: {len(holiday_df)} employees")
    else:
        st.sidebar.error("❌ Could not load holiday file")


st.sidebar.subheader("Hypercare Team")
hypercare_default = "wpatchan, esinumac, ratilalr, mariebak, azeemaj"
hypercare_input = st.sidebar.text_area("Hypercare List (comma-separated)", value=hypercare_default)
hypercare_list = [name.strip() for name in hypercare_input.split(',') if name.strip()]

st.sidebar.subheader("Hyderabad Team")
hyd_default = "tparinay, shirisap, chalhars, sheshasa"
hyd_input = st.sidebar.text_area("Hyderabad Team (comma-separated)", value=hyd_default)
hyd_team = [name.strip() for name in hyd_input.split(',') if name.strip()]

st.sidebar.subheader("Week Days")

if df is not None:
    detected_dates = extract_dates_from_schedule(df)
    if detected_dates:
        days_default = ", ".join(detected_dates)
        st.sidebar.success(f"✅ Auto-detected {len(detected_dates)} days from file")
    else:
        days_default = "Sun 11/02/2025, Mon 11/03/2025, Tue 11/04/2025, Wed 11/05/2025, Thu 11/06/2025, Fri 11/07/2025, Sat 11/08/2025"
        st.sidebar.info("ℹ️ Using default dates")
else:
    days_default = "Sun 11/02/2025, Mon 11/03/2025, Tue 11/04/2025, Wed 11/05/2025, Thu 11/06/2025, Fri 11/07/2025, Sat 11/08/2025"

days_input = st.sidebar.text_area("Days (comma-separated)", value=days_default)
days_of_week = [day.strip() for day in days_input.split(',') if day.strip()]
st.sidebar.subheader("Break Schedule")
break_default = "Kapil 14:00 / Ans 14:30 / Anushka 15:00 / Darshan 15:30 / Tommaso 16:00"
break_input = st.sidebar.text_area("Break Table", value=break_default, height=100)

st.sidebar.subheader("📊 Assignment History")
if st.sidebar.button("🔄 Reset Assignment History"):
    st.session_state.tracker = AssignmentTracker()
    st.sidebar.success("✅ History reset!")

if st.sidebar.button("💾 Save History to disk"):
    st.session_state.tracker.save_history()
    st.sidebar.success("✅ History saved!")

# Load schedule and holiday data
if uploaded_holiday_file is not None or Path('schedule.json').exists():
    try:
        schedule_data, rota_df = load_schedule_and_holiday_data(
            schedule_path='schedule.json',
            holiday_file=uploaded_holiday_file
        )

        if rota_df is not None and not rota_df.empty:
            # Build availability matrix
            availability = build_availability_matrix(schedule_data, rota_df, days_of_week)

            # Convert availability to holiday_off_df format for compatibility
            # This creates a DataFrame with employees as rows and days as columns
            employees = list(availability.keys())
            date_columns = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']

            holiday_off_df = pd.DataFrame(index=employees, columns=days_of_week)

            for emp in employees:
                for day_full, day_date in zip(date_columns, days_of_week):
                    day_info = availability[emp].get(day_full, {})
                    status = day_info.get('status', 'Off')
                    shift_type = day_info.get('shift_type', None)

                    if status == 'Working' and shift_type:
                        holiday_off_df.at[emp, day_date] = shift_type
                    elif status == 'Holiday':
                        holiday_off_df.at[emp, day_date] = 'Holiday'
                    else:
                        holiday_off_df.at[emp, day_date] = 'Off'

            st.sidebar.success("✅ Schedule and holiday data loaded successfully!")
        else:
            st.sidebar.warning("⚠️ Could not load rota_holiday file")
            holiday_off_df = pd.DataFrame()
    except Exception as e:
        st.sidebar.error(f"❌ Error loading data: {str(e)}")
        holiday_off_df = pd.DataFrame()
else:
    st.sidebar.info("ℹ️ Please upload schedule.json and rota_holiday file")
    holiday_off_df = pd.DataFrame()


if df is not None:
    with st.expander("📋 Preview Uploaded Data"):
        st.dataframe(df.head(10))
    
    if st.button("🚀 Generate Rota", type="primary"):
        with st.spinner("Generating rota from schedule.json and rota_holiday..."):
            try:
                # Load data
                schedule_data, rota_df = load_schedule_and_holiday_data(
                    schedule_path='schedule.json',
                    holiday_file=uploaded_holiday_file
                )

                if rota_df is None:
                    st.error("❌ Could not load rota_holiday file. Please upload it.")
                else:
                    # Build availability matrix
                    availability = build_availability_matrix(schedule_data, rota_df, days_of_week)

                    # Use a temp tracker for generation
                    temp_tracker = AssignmentTracker()
                    temp_tracker.history = copy.deepcopy(st.session_state.tracker.history)

                    task_table = generate_rota_from_availability(
                        availability,
                        hypercare_list,
                        hyd_team,
                        days_of_week,
                        break_input,
                        temp_tracker  # Pass tracker for fair rotation
                    )

                    st.success("✅ Rota generated successfully!")

                    # Display results
                    st.subheader("📅 Weekly Rota")
                    st.dataframe(task_table, use_container_width=True)

                    # Download button
                    csv_buffer = io.StringIO()
                    task_table.to_csv(csv_buffer, index=False)
                    st.download_button(
                        label="📥 Download Rota CSV",
                        data=csv_buffer.getvalue(),
                        file_name="generated_rota.csv",
                        mime="text/csv"
                    )

            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
                st.exception(e)
