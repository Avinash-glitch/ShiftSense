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
                # handle possible non-iso strings
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
        
        # Keep only last 52 weeks of history (prevent unbounded growth)
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
        # min_days_gap indicates the minimal number of days between assignments.
        # For "no consecutive days" use min_days_gap=2 (e.g., last = yesterday -> days_since_last=1 -> cannot assign)
        return days_since_last >= min_days_gap
    
    def get_eligible_sorted(self, people_list, task_type, current_date, min_days_gap=5, weeks_for_count=52):
        """Get eligible people sorted by assignment count (fairness)"""
        eligible = []
        for person in people_list:
            if self.can_assign(person, task_type, current_date, min_days_gap):
                count = self.get_assignment_count(person, task_type, weeks=weeks_for_count)
                eligible.append((person, count))
        
        # Sort by count (ascending) - people with fewer assignments first
        eligible.sort(key=lambda x: (x[1], x[0]))
        return [person for person, count in eligible]

# === SHIFT LEGENDS === (unchanged)
SHIFT_LEGENDS = {
    'A': {'description': 'AM Shift', 'time': '09:30-18:00', 'type': 'Morning'},
    'A1': {'description': 'Mid shift', 'time': '11:30-20:00', 'type': 'Mid'},
    'A2': {'description': 'PM shift', 'time': '14:00-22:30', 'type': 'Night'},
    'H': {'description': 'Annual Leave full day', 'time': 'Off', 'type': 'Holiday'},
    'P': {'description': 'Personal Leave', 'time': 'Off', 'type': 'Holiday'},
    'BH': {'description': 'UK Bank holiday', 'time': 'Off', 'type': 'Holiday'},
    'S': {'description': 'Sick leave', 'time': 'Off', 'type': 'Holiday'},
    'M/P': {'description': 'Maternity/Paternity leave', 'time': 'Off', 'type': 'Holiday'},
    'FL': {'description': 'Family Leave', 'time': 'Off', 'type': 'Holiday'},
    'H PT': {'description': 'Annual Leave - not a full day', 'time': 'Partial Off', 'type': 'Holiday'},
    'UPL': {'description': 'Unpaid Leave', 'time': 'Off', 'type': 'Holiday'},
    'PL': {'description': 'Parental Leave', 'time': 'Off', 'type': 'Holiday'},
    'RB1': {'description': 'Ramp Back', 'time': '13:00-17:00', 'type': 'Morning'},
    'WBHA': {'description': 'Working Bank Holidays', 'time': 'Variable', 'type': 'Morning'},
    'FH': {'description': 'Flexi Hours', 'time': 'Flexible', 'type': 'NA'},
    'BWTA': {'description': 'Balancing working time', 'time': 'Variable', 'type': 'NA'},
    'BWTAP': {'description': 'Balancing working time Premium', 'time': 'Variable', 'type': 'NA'},
    'BWT-': {'description': 'Time off due to working days balance', 'time': 'Off', 'type': 'Holiday'},
    'AFLX+8': {'description': 'Positive flexibility 8 hours', 'time': 'Variable', 'type': 'NA'},
    'FLXA-8': {'description': 'Negative flexibility -8 hours', 'time': 'Variable', 'type': 'NA'},
    'AFLX+1': {'description': 'Positive flexibility 1 hour end', 'time': 'Variable', 'type': 'NA'},
    'AFLX-1': {'description': 'Negative flexibility -1 hour end', 'time': 'Variable', 'type': 'NA'},
    'A1+FLX': {'description': 'Positive flexibility 1 hour start', 'time': 'Variable', 'type': 'NA'},
    'A1-FLX': {'description': 'Negative flexibility -1 hour start', 'time': 'Variable', 'type': 'NA'},
    'WBHE': {'description': 'Working Bank Holidays', 'time': 'Variable', 'type': 'Morning'},
    'AEW': {'description': 'Associate Experience week', 'time': 'Variable', 'type': 'NA'}
}

def get_shift_type(shift_str):
    """Classify shift as Morning, Mid, Night, Holiday, Off, or NA"""
    if pd.isna(shift_str) or str(shift_str).strip() == "":
        return "Off"
    
    shift_str = str(shift_str).strip()
    
    if shift_str in SHIFT_LEGENDS:
        return SHIFT_LEGENDS[shift_str]['type']
    
    # Check for time-based shifts
    if '11:30' in shift_str or '11-30' in shift_str:
        return "Mid"
    elif '14:00' in shift_str or '14-00' in shift_str or '14:30' in shift_str:
        return "Night"
    elif '09:30' in shift_str or '9:30' in shift_str or '8-9:30' in shift_str or '8-' in shift_str:
        return "Morning"
    
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
    """Automatically extract dates from the uploaded schedule"""
    day_start_idx = 3
    for i, col in enumerate(df.columns):
        if 'monday' in str(col).lower() or 'sunday' in str(col).lower():
            day_start_idx = i
            break
    
    day_columns = df.columns[day_start_idx:]
    
    for idx in range(min(5, len(df))):
        row = df.iloc[idx]
        date_count = 0
        
        for col in day_columns[:3]:
            val = str(row[col])
            if '/' in val and len(val.split('/')) >= 2:
                try:
                    parts = val.split('/')
                    if len(parts) == 3 and parts[2].isdigit() and len(parts[2]) == 4:
                        date_count += 1
                except:
                    pass
        
        if date_count >= 2:
            days_with_dates = []
            for col in day_columns:
                val = str(row[col])
                if '/' in val and val != 'nan':
                    day_name = col[:3]
                    days_with_dates.append(f"{day_name} {val}")
            
            return days_with_dates
    
    return []

def process_schedule_csv(df):
    """Process the uploaded schedule CSV/Excel"""
    login_col = None
    for col in df.columns:
        if 'login' in str(col).lower():
            login_col = col
            break
    
    if login_col is None:
        login_col = df.columns[0]
    
    df = df.rename(columns={login_col: 'login'})
    
    day_start_idx = 3
    for i, col in enumerate(df.columns):
        if 'monday' in str(col).lower() or '/' in str(col) or re.match(r'\d+/\d+', str(col)):
            day_start_idx = i
            break
    
    day_columns = df.columns[day_start_idx:]
    
    df = df[df['login'].notna()]
    df = df[df['login'] != 'Login']
    df = df[df['login'] != 'login']
    df = df.reset_index(drop=True)
    
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

# --- UPDATED: helper to choose person(s) for slot(s) based on dynamic limits ---
def select_people_for_slots(tracker, candidates, task_type, current_date, slots=1, min_days_gap=5, weeks_for_count=52, total_slots=1):
    """
    Select `slots` people from `candidates` for the given task_type using tracker:
      - prefer people who are eligible (respecting min_days_gap)
      - prefer people with the fewest assignments in the last `weeks_for_count` weeks
      - enforce soft per-person max based on number of candidates and total_slots (week-level)
    `total_slots` should reflect the total number of identical slots across the rota (e.g. number of days).
    Returns list of selected people (length <= slots).
    """
    candidates = list(candidates)
    if not candidates:
        return []
    
    num_people = len(candidates)
    if num_people == 0:
        return []
    
    # Compute soft max per-person across the rota
    soft_max = max(1, math.ceil(total_slots / num_people))
    
    # get eligible sorted by count
    eligible = tracker.get_eligible_sorted(candidates, task_type, current_date, min_days_gap=min_days_gap, weeks_for_count=weeks_for_count)
    # ADD THIS SECTION after getting eligible list
    # Group by count, then shuffle within each group
    count_groups = {}
    for person in eligible:
        count = tracker.get_assignment_count(person, task_type, weeks=weeks_for_count)
        if count not in count_groups:
            count_groups[count] = []
        count_groups[count].append(person)

    # Shuffle each group and rebuild eligible list
    randomized_eligible = []
    for count in sorted(count_groups.keys()):
        group = count_groups[count]
        random.shuffle(group)  # RANDOMIZE within same count
        randomized_eligible.extend(group)

    eligible = randomized_eligible

    if not eligible:
        # if nobody is eligible (because of gap), relax the gap constraint
        eligible = tracker.get_eligible_sorted(candidates, task_type, current_date, min_days_gap=0, weeks_for_count=weeks_for_count)
        if not eligible:
            return []
    
    # filter by those below soft_max first
    under_limit = [p for p in eligible if tracker.get_assignment_count(p, task_type, weeks=weeks_for_count) < soft_max]
    
    chosen = []
    # fill from under_limit first
    for p in under_limit:
        if len(chosen) >= slots:
            break
        chosen.append(p)
    
    # if still slots left, fill from remaining eligible
    if len(chosen) < slots:
        remaining = [p for p in eligible if p not in chosen]
        for p in remaining:
            if len(chosen) >= slots:
                break
            chosen.append(p)
    
    return chosen

def create_task_by_day_table_with_tracking(holiday_off_df, hypercare_list, hyd_team, days_of_week, break_table_text, tracker):
    """Creates the rota table with fair rotation tracking"""
    
    # We'll store generated table rows in table_data
    daily_assigned = {}
    table_data = []
    
    # Keep a copy of assignments so we can optionally save one rota later (do not auto-persist to tracker here)
    generated_assignments = []
    
    wims_status_row = {
        "Day": "WIMS Status",
        "Hypercare": "on project",
        "SIMs": "Available",
        "DOR Call": "In meeting",
        "WIMS Cases": "Available",
        "EOD Report": "On Project",
        "WIMS Breaks": break_table_text
    }
    table_data.append(wims_status_row)
    
    # Precompute total slots for sim AM/PM in this rota (helps compute soft_max)
    total_days = len(days_of_week)
    total_sim_am_slots = total_days
    total_sim_pm_slots = total_days
    total_sim_night_slots = total_days  # night coverage attempt each day (weekend fallback allowed)
    
    for day_index, day in enumerate(days_of_week):
        day_name = day.split()[0]
        is_weekend = day_name in ["Sun", "Sat","Mon"]
        no_dor = day_name in ["Sun", "Sat"]
        #date format here
        try:
            current_date = datetime.strptime(day, "%a %m/%d/%Y")
        except:
            current_date = datetime.now() + timedelta(days=day_index)
        
        morning_shift_people = []
        mid_shift_people = []
        night_shift_people = []
        all_working = []
        
        # find correct column in holiday_off_df
        if day not in holiday_off_df.columns:
            matches = [c for c in holiday_off_df.columns if c.startswith(day_name)]
            if matches:
                day_col = matches[0]
            else:
                # no column for day -> skip
                continue
        else:
            day_col = day
        
        for _, row in holiday_off_df.iterrows():
            person = row.name
            shift_status = get_shift_value(row, day_col)
            
            if isinstance(shift_status, str):
                if shift_status.lower() == 'morning':
                    morning_shift_people.append(person)
                    all_working.append(person)
                elif shift_status.lower() == 'mid':
                    mid_shift_people.append(person)
                    all_working.append(person)
                elif shift_status.lower() == 'night':
                    night_shift_people.append(person)
                    all_working.append(person)
        
        daily_assigned[day] = set()
        assignments = {
            "Hypercare": [],
            "SIMs": "",
            "DOR Call": [],
            "WIMS Cases": [],
            "EOD Report": []
        }
        
        # ---------- Hypercare ----------
        # rule: no consecutive days; otherwise no other restriction
        working_hypercare = [p for p in hypercare_list if p in all_working]
        # choose up to 2 on weekdays, 1 on weekends
        target_hypercare_slots = 1 if is_weekend else 2
        # Right before: hypercare_selected = select_people_for_slots(...)
        print(f"=== DEBUG: {day} ===")
        print(f"Working hypercare candidates: {working_hypercare}")
        for p in working_hypercare:
            last = tracker.get_last_assignment(p, 'Hypercare')
            count = tracker.get_assignment_count(p, 'Hypercare', weeks=52)
            print(f"  {p}: last={last}, count={count}")

        eligible = tracker.get_eligible_sorted(working_hypercare, "Hypercare", current_date, min_days_gap=2, weeks_for_count=52)
        print(f"Eligible after gap check: {eligible}")
        hypercare_selected = select_people_for_slots(
            tracker, working_hypercare, "Hypercare", current_date, slots=target_hypercare_slots, min_days_gap=2, weeks_for_count=52, total_slots=total_days
        )
        # Record selections locally (to temp tracker passed in)
        assignments["Hypercare"] = hypercare_selected
        for person in hypercare_selected:
            tracker.record_assignment(person, 'Hypercare', current_date)
            daily_assigned[day].add(person)
        
        # ---------- SIMs ----------
        sims_text_parts = []
        # AM
        available_morning = [p for p in morning_shift_people if p not in daily_assigned[day]]
        am_selected = select_people_for_slots(
            tracker, available_morning, "SIMs_AM", current_date, slots=1, min_days_gap=1, weeks_for_count=52, total_slots=total_sim_am_slots
        )
        if am_selected:
            morning_sim = am_selected[0]
            sims_text_parts.append(f"AM: {morning_sim}")
            tracker.record_assignment(morning_sim, 'SIMs_AM', current_date)
            daily_assigned[day].add(morning_sim)
        # PM
        available_mid = [p for p in mid_shift_people if p not in daily_assigned[day]]
        pm_selected = select_people_for_slots(
            tracker, available_mid, "SIMs_PM", current_date, slots=1, min_days_gap=1, weeks_for_count=52, total_slots=total_sim_pm_slots
        )
        if pm_selected:
            mid_sim = pm_selected[0]
            sims_text_parts.append(f"PM: {mid_sim}")
            tracker.record_assignment(mid_sim, 'SIMs_PM', current_date)
            daily_assigned[day].add(mid_sim)
        # Night (prefer HYD)
        hyd_night_cands = [p for p in night_shift_people if p in hyd_team and p not in daily_assigned[day]]
        night_selected = select_people_for_slots(
            tracker, hyd_night_cands, "SIMs_Night", current_date, slots=1, min_days_gap=1, weeks_for_count=52, total_slots=total_sim_night_slots
        )
        if night_selected:
            night_sim = night_selected[0]
            sims_text_parts.append(f"Night: {night_sim}")
            tracker.record_assignment(night_sim, 'SIMs_Night', current_date)
            daily_assigned[day].add(night_sim)
        else:
            sims_text_parts.append("Night: HYD (no coverage)")
        
        assignments["SIMs"] = " | ".join(sims_text_parts)
        
        # ---------- DOR CALL ----------
        available_for_dor = [p for p in all_working if p not in daily_assigned[day]]
        if available_for_dor and not no_dor:
            dor_selected = select_people_for_slots(tracker, available_for_dor, "DOR_Call", current_date, slots=1, min_days_gap=1, weeks_for_count=52, total_slots=total_days)
            if dor_selected:
                dor_person = dor_selected[0]
                assignments["DOR Call"] = [dor_person]
                tracker.record_assignment(dor_person, 'DOR_Call', current_date)
                daily_assigned[day].add(dor_person)
        
        # ---------- EOD REPORT ----------
        eligible_eod_pool = set(mid_shift_people + night_shift_people) | (set(hyd_team) & set(all_working))
        available_for_eod = [p for p in eligible_eod_pool if p not in daily_assigned[day]]
        if available_for_eod:
            eod_selected = select_people_for_slots(tracker, available_for_eod, "EOD_Report", current_date, slots=1, min_days_gap=1, weeks_for_count=52, total_slots=total_days)
            if eod_selected:
                eod_person = eod_selected[0]
                assignments["EOD Report"] = [eod_person]
                tracker.record_assignment(eod_person, 'EOD_Report', current_date)
                daily_assigned[day].add(eod_person)
        
        # ---------- WIMS Cases ----------
        wims_morning = [p for p in morning_shift_people if p not in daily_assigned[day]]
        wims_mid = [p for p in mid_shift_people if p not in daily_assigned[day]]
        wims_night = [p for p in night_shift_people if p in hyd_team and p not in daily_assigned[day]]
        wims_people = wims_morning + wims_mid + wims_night
        assignments["WIMS Cases"] = wims_people
        
        row = {
            "Day": day,
            "Hypercare": ", ".join(assignments["Hypercare"]) if assignments["Hypercare"] else "",
            "SIMs": assignments["SIMs"],
            "DOR Call": ", ".join(assignments["DOR Call"]) if assignments["DOR Call"] else "",
            "WIMS Cases": ", ".join(assignments["WIMS Cases"]) if assignments["WIMS Cases"] else "",
            "EOD Report": ", ".join(assignments["EOD Report"]) if assignments["EOD Report"] else "",
            "WIMS Breaks": break_table_text
        }
        table_data.append(row)
        generated_assignments.append(row)
    
    # Return table + a serialisable copy of generated_assignments for session storage
    return pd.DataFrame(table_data), generated_assignments

def create_daily_statistics_table(holiday_off_df, task_table, days_of_week):
    """Create statistics table"""
    random.seed()
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
    st.session_state.generated_rotas = []  # store generated rotas in-session; user chooses which to save

df = None

st.sidebar.header("⚙️ Configuration")

# Provide a convenience button to load the uploaded file that was provided earlier
SAMPLE_LOCAL_PATH = "/mnt/data/new_schedule.xlsx.csv"
if st.sidebar.button("Load sample uploaded file (provided)"):
    try:
        df = pd.read_csv(SAMPLE_LOCAL_PATH)
        st.sidebar.success(f"Loaded sample file from {SAMPLE_LOCAL_PATH}")
    except Exception as e:
        st.sidebar.error(f"Failed to load sample file: {e}")

uploaded_file = st.sidebar.file_uploader("Upload Schedule CSV", type=['csv', 'xlsx'])

if uploaded_file is not None:
    try:
        if uploaded_file.name.endswith('.csv'):
            # try default separator
            try:
                df = pd.read_csv(uploaded_file)
            except Exception:
                uploaded_file.seek(0)
                df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file, engine='openpyxl')
        st.sidebar.success("✅ File loaded successfully!")
    except Exception as e:
        st.sidebar.error(f"❌ Error reading file: {str(e)}")
        df = None

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
        days_default = "Sun 12/22/2025, Mon 12/23/2025, Tue 12/24/2025, Wed 12/25/2025, Thu 12/26/2025, Fri 12/27/2025, Sat 12/28/2025"
        st.sidebar.info("ℹ️ Using default dates")
else:
    days_default = "Sun 12/22/2025, Mon 12/23/2025, Tue 12/24/2025, Wed 12/25/2025, Thu 12/26/2025, Fri 12/27/2025, Sat 12/28/2025"

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

if df is not None:
    with st.expander("📋 Preview Uploaded Data"):
        st.dataframe(df.head(10))
    
    if st.button("🚀 Generate Rota", type="primary"):
        with st.spinner("Processing schedule with fair rotation..."):
            try:
                shift_summary, holiday_off_df = process_schedule_csv(df)
                
                # Use a deepcopy of the real tracker during generation so we don't mutate persistent history
                temp_tracker = AssignmentTracker()
                temp_tracker.history = copy.deepcopy(st.session_state.tracker.history)
                
                task_table, generated_assignments = create_task_by_day_table_with_tracking(
                    holiday_off_df, 
                    hypercare_list, 
                    hyd_team, 
                    days_of_week, 
                    break_input,
                    temp_tracker  # use temp tracker (deepcopy) for generation
                )
                
                stats_table = create_daily_statistics_table(
                    holiday_off_df, 
                    task_table, 
                    days_of_week
                )
                
                if task_table is not None:
                    st.success("✅ Fair rota generated with rotation tracking (in-memory)!")
                    
                    st.info("ℹ️ **Fair Rotation Active**: Assignments were tracked in-memory during generation to avoid duplicate picks in the same generation. Nothing is persisted to disk until you explicitly save a rota.")
                    
                    # store generated rota in session for user to pick from later
                    st.session_state.generated_rotas.append({
                        "dates": days_of_week,
                        "task_table": task_table.to_dict(orient='records'),
                        "generated_assignments": generated_assignments
                    })
                    
                    tab1, tab2, tab3, tab4 = st.tabs([
                        "📅 Weekly Rota", 
                        "📊 Daily Statistics",
                        "👥 Shift Summary", 
                        "🏖️ Holiday/Off Schedule"
                    ])
                    with tab1:
                        st.subheader("Weekly Task Assignments")
                        st.dataframe(task_table, use_container_width=True)
                        
                        csv_buffer = io.StringIO()
                        task_table.to_csv(csv_buffer, index=False)

                                                
    
                        # With this:
                       # Extract start and end dates from days_of_week
                        if days_of_week:
                            try:
                                first_day = days_of_week  # ← FIX: Added 
                                last_day = days_of_week[-1]

                                first_date_str = first_day.split()  # "11/03/2025"
                                last_date_str = last_day.split()    # "11/09/2025"

                                first_mm_dd = "/".join(first_date_str.split("/")[:2])  # "11/03"
                                last_mm_dd = "/".join(last_date_str.split("/")[:2])    # "11/09"

                                file_name = f"export_rota_{first_mm_dd}_{last_mm_dd}.csv"
                            except:
                                file_name = "weekly_rota.csv"
                        else:
                            file_name = "weekly_rota.csv"

                        st.download_button(
                            label="📥 Download Rota CSV",
                            data=csv_buffer.getvalue(),
                            file_name=file_name,
                            mime="text/csv"
                        )


                        
                        # --- UI to save the generated rota to assignment history (explicit) ---
                        st.markdown("### 💾 Save a generated rota")
                        if st.session_state.generated_rotas:
                            rota_options = [
                                f"Rota #{i+1} – {', '.join(r['dates'])}"
                                for i, r in enumerate(st.session_state.generated_rotas)
                            ]
                            selected = st.selectbox("Choose a generated rota to save (session only):", rota_options)
                            if selected:
                                idx = rota_options.index(selected)
                                if st.button("💾 Save Selected Rota to History"):
                                    chosen = st.session_state.generated_rotas[idx]
                                    # record each day's assignments into tracker persistently
                                    for row in chosen['task_table']:
                                        day = row.get('Day')
                                        if not day or day == 'WIMS Status':
                                            continue
                                        try:
                                            date_obj = datetime.strptime(day, "%a %m/%d/%Y")
                                        except:
                                            # fallback: use today's date + offset
                                            date_obj = datetime.now()
                                        # Hypercare
                                        for p in str(row.get('Hypercare', '')).split(','):
                                            p = p.strip()
                                            if p:
                                                st.session_state.tracker.record_assignment(p, 'Hypercare', date_obj)
                                        # SIMs - parse AM/PM/Night
                                        sims_str = str(row.get('SIMs', ''))
                                        parts = [s.strip() for s in sims_str.split('|')]
                                        for part in parts:
                                            if ':' in part:
                                                slot, name = part.split(':', 1)
                                                p = name.strip()
                                                if p and not p.startswith("HYD"):
                                                    # map slot to specific task_type
                                                    if slot.upper().startswith('AM'):
                                                        task = 'SIMs_AM'
                                                    elif slot.upper().startswith('PM'):
                                                        task = 'SIMs_PM'
                                                    elif slot.upper().startswith('NIGHT'):
                                                        task = 'SIMs_Night'
                                                    else:
                                                        task = 'SIMs'
                                                    st.session_state.tracker.record_assignment(p, task, date_obj)
                                        # DOR
                                        for p in str(row.get('DOR Call', '')).split(','):
                                            p = p.strip()
                                            if p:
                                                st.session_state.tracker.record_assignment(p, 'DOR_Call', date_obj)
                                        # EOD
                                        for p in str(row.get('EOD Report', '')).split(','):
                                            p = p.strip()
                                            if p:
                                                st.session_state.tracker.record_assignment(p, 'EOD_Report', date_obj)
                                        # WIMS Cases - multiple people
                                        for p in str(row.get('WIMS Cases', '')).split(','):
                                            p = p.strip()
                                            if p:
                                                st.session_state.tracker.record_assignment(p, 'WIMS_Case', date_obj)
                                    st.session_state.tracker.save_history()
                                    st.success("✅ Selected rota saved to assignment history and persisted to disk.")
                    
                    with tab2:
                        st.subheader("Daily Statistics & Task Counts")
                        
                        if not stats_table.empty and "Total Working" in stats_table.columns:
                            st.dataframe(stats_table, use_container_width=True)
                            
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                avg_working = stats_table["Total Working"].mean()
                                st.metric("Avg Working/Day", f"{avg_working:.1f}")
                            with col2:
                                total_holidays = stats_table["On Holiday"].sum()
                                st.metric("Total Holidays", int(total_holidays))
                            with col3:
                                total_off = stats_table["Day Off"].sum()
                                st.metric("Total Days Off", int(total_off))
                        else:
                            st.warning("⚠️ Statistics table is empty")
                    
                    with tab3:
                        st.subheader("Shift Summary")
                        st.dataframe(shift_summary, use_container_width=True)
                    
                    with tab4:
                        st.subheader("Holiday/Off Schedule")
                        st.dataframe(holiday_off_df, use_container_width=True)
            
            except Exception as e:
                st.error(f"❌ Error processing schedule: {str(e)}")
                st.exception(e)

else:
    st.info("👈 Please upload a schedule CSV or Excel file to get started (or use the 'Load sample uploaded file' button on the sidebar)")
