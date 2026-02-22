
import streamlit as st
import pandas as pd
import re
from datetime import datetime
import random
from collections import deque
import io
# Page configuration
st.set_page_config(
    page_title="Amazon Rota System",
    page_icon="📅",
    layout="wide"
)

st.title("📅 Amazon Rota System Generator")
st.markdown("Generate weekly task assignments for your team")

# === SHIFT LEGENDS AND PARSING FUNCTIONS ===

SHIFT_LEGENDS = {
    'A': {'description': 'AM Shift', 'time': '09:30-18:00', 'type': 'Morning'},
    'A1': {'description': 'Mid shift', 'time': '11:30-20:00', 'type': 'Evening'},
    'A2': {'description': 'PM shift', 'time': '14:00-22:30', 'type': 'Evening'},
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

def extract_shift_time(shift_str):
    """Extract time from shift string"""
    if not isinstance(shift_str, str):
        return None
    
    shift_str = shift_str.strip()
    
    # Check if it's in the legend
    if shift_str in SHIFT_LEGENDS:
        return SHIFT_LEGENDS[shift_str]['time']
    
    # Try to extract custom time format
    match = re.search(r"(\d{1,2}:\d{2}\s*-\s*\d{1,2}:\d{2})", shift_str)
    if match:
        return match.group(1)
    
    # Handle formats like "8-9:30/14:30-18:00"
    if '/' in shift_str or '-' in shift_str:
        return shift_str
    
    return None

def get_shift_type(shift_str):
    """Classify shift as Morning, Evening, Holiday, Off, or NA"""
    if pd.isna(shift_str) or str(shift_str).strip() == "":
        return "Off"
    
    shift_str = str(shift_str).strip()
    
    # Check if it's in the legend
    if shift_str in SHIFT_LEGENDS:
        return SHIFT_LEGENDS[shift_str]['type']
    
    # Try time-based detection for custom formats
    match = re.search(r"(\d{1,2}):(\d{2})", shift_str)
    if match:
        hour = int(match.group(1))
        return "Morning" if hour < 12 else "Evening"
    
    return "NA"

def get_shift_value(row, day_col):
    """Return the shift status for a row and day column, safely handling NaN."""
    val = row.get(day_col, "")
    if pd.isna(val):
        return ""
    if isinstance(val, str):
        return val.strip()
    return val

def process_schedule_csv(df):
    """Process the uploaded schedule CSV/Excel with proper column handling"""
    
    # Find the login column
    login_col = None
    for col in df.columns:
        if 'login' in str(col).lower():
            login_col = col
            break
    
    if login_col is None:
        login_col = df.columns[0]
    
    # Rename to standard 'login'
    df = df.rename(columns={login_col: 'login'})
    
    # Get day columns - typically everything after the first 3 columns
    day_start_idx = 3
    for i, col in enumerate(df.columns):
        if 'monday' in str(col).lower() or '/' in str(col) or re.match(r'\d+/\d+', str(col)):
            day_start_idx = i
            break
    
    day_columns = df.columns[day_start_idx:]
    
    # Remove header rows
    df = df[df['login'].notna()]
    df = df[df['login'] != 'Login']
    df = df[df['login'] != 'login']
    df = df.reset_index(drop=True)
    
    # Melt DataFrame so each person-day is a row
    long_df = df.melt(id_vars=["login"], value_vars=day_columns, var_name="Day", value_name="Shift")
    
    # Apply classification
    long_df["ShiftType"] = long_df["Shift"].apply(get_shift_type)
    long_df["ShiftTime"] = long_df["Shift"].apply(extract_shift_time)
    
    # Weekly Shift Summary
    shift_summary = (
        long_df[long_df["ShiftType"].isin(["Morning", "Evening"])]
        .groupby("login")["ShiftType"]
        .agg(lambda x: x.mode().iloc[0] if not x.mode().empty else "NA")
        .reset_index()
    )
    shift_summary.columns = ['login', 'ShiftType']
    
    # Daily Holiday/Off Table
    holiday_off_df = long_df.pivot_table(
        index="login", columns="Day", values="ShiftType", aggfunc="first"
    ).fillna("Off")
    
    return shift_summary, holiday_off_df
    
def create_task_by_day_table(holiday_off_df, hypercare_list, hyd_team, days_of_week, break_table_text, random_seed):
    """Creates the rota table per the specified rules"""
    
    random.seed(random_seed)
    
    # Track assignments and constraints
    hypercare_count = {person: 0 for person in hypercare_list}
    assigned_morning_sims = set()
    assigned_evening_sims = set()
    assigned_dor = set()
    assigned_eod = set()
    
    table_data = []
    
    # Add WIMS Status row at the top
    wims_status_row = {
        "Day": "WIMS Status",
        "Hypercare": "on project",
        "SIMs": "Available",
        "DOR Call": "In meeting",
        "WIMS Cases": "Available",
        "EOD Report": "On Project",
        "WIMS Breaks (merged)": break_table_text
    }
    table_data.append(wims_status_row)
    
    previous_day_hypercare = set()
    hc_deque = deque(hypercare_list)
    random.shuffle(hc_deque)
    
    for day_index, day in enumerate(days_of_week):
        hc_deque.rotate(1)
        rotated_hypercare = list(hc_deque)
        
        day_name = day.split()[0]
        is_weekend = day_name in ["Sun", "Mon", "Sat"]
        no_dor = day_name in ["Sun", "Sat"]
        
        morning_shift_people = []
        evening_shift_people = []
        all_working = []
        
        if day not in holiday_off_df.columns:
            matches = [c for c in holiday_off_df.columns if c.startswith(day_name)]
            if matches:
                day_col = matches[0]
            else:
                st.error(f"Day column '{day}' not found in CSV")
                return None
        else:
            day_col = day
        
        for _, row in holiday_off_df.iterrows():
            person = row.name  # ✅ Use row.name to get the index value

            shift_status = get_shift_value(row, day_col)
            if isinstance(shift_status, str) and shift_status.lower() == 'morning':
                morning_shift_people.append(person)
                all_working.append(person)
            elif isinstance(shift_status, str) and shift_status.lower() == 'evening':
                evening_shift_people.append(person)
                all_working.append(person)
            else:
                if isinstance(shift_status, str) and "11:30" in shift_status:
                    evening_shift_people.append(person)
                    all_working.append(person)
        
        random.shuffle(morning_shift_people)
        random.shuffle(evening_shift_people)
        random.shuffle(all_working)
        
        assignments = {
            "Hypercare": [],
            "SIMs": "",
            "DOR Call": [],
            "WIMS Cases": [],
            "EOD Report": ""
        }
        
        # Hypercare selection
        working_today = set(all_working)
        available_hypercare_today = [
            p for p in rotated_hypercare
            if p in working_today
            and hypercare_count.get(p, 0) < 3
            and p not in previous_day_hypercare
        ]
        
        hypercare_assignments = []
        
        if is_weekend:
            weekend_candidates = [p for p in available_hypercare_today ]
            if weekend_candidates:
                person = random.choice(weekend_candidates)
                hypercare_assignments.append(person)
                hypercare_count[person] += 1
        else:
            if available_hypercare_today:
                p1 = random.choice(available_hypercare_today)
                hypercare_assignments.append(p1)
                hypercare_count[p1] += 1
                available_hypercare_today = [p for p in available_hypercare_today if p != p1]
            if available_hypercare_today:
                p2 = random.choice(available_hypercare_today)
                hypercare_assignments.append(p2)
                hypercare_count[p2] += 1
        
        assignments["Hypercare"] = hypercare_assignments
        
        # SIMs assignment
        sims_text_parts = []
        available_morning = [p for p in morning_shift_people if p not in hypercare_assignments and p not in assigned_morning_sims]
        if available_morning:
            morning_sim_person = random.choice(available_morning)
            assigned_morning_sims.add(morning_sim_person)
            sims_text_parts.append(f"AM: {morning_sim_person}")
        available_evening = [p for p in evening_shift_people if p not in hypercare_assignments and p not in assigned_evening_sims]
        if available_evening:
            evening_sim_person = random.choice(available_evening)
            assigned_evening_sims.add(evening_sim_person)
            sims_text_parts.append(f"PM: {evening_sim_person}")
        
        sims_text_parts.append("Night: HYD")
        assignments["SIMs"] = " ".join(sims_text_parts)
        
        # DOR assignment
        already_assigned = set(hypercare_assignments) | assigned_morning_sims | assigned_evening_sims | assigned_dor
        available_for_dor = [p for p in all_working if p not in already_assigned]
        if available_for_dor and not no_dor:
            dor_person = random.choice(available_for_dor)
            assignments["DOR Call"] = [dor_person]
            assigned_dor.add(dor_person)
        else:
            assignments["DOR Call"] = []
        
        # EOD Report assignment
        eligible_eod = set(evening_shift_people) | (set(hyd_team) & working_today)
        already_assigned_for_eod = set(hypercare_assignments) | set(assignments["DOR Call"]) | assigned_eod
        eligible_for_eod = [p for p in eligible_eod if p not in already_assigned_for_eod]
        if not eligible_for_eod:
            eligible_for_eod = [p for p in all_working if p not in already_assigned_for_eod]
        if eligible_for_eod:
            eod_person = random.choice(eligible_for_eod)
            assignments["EOD Report"] = [eod_person]
            assigned_eod.add(eod_person)
        else:
            assignments["EOD Report"] = []
        
        # WIMS Cases
        on_special_tasks = set(hypercare_assignments)
        wims_people = [p for p in all_working if p not in on_special_tasks]
        assignments["WIMS Cases"] = wims_people
        
        row = {
            "Day": day,
            "Hypercare": ", ".join(assignments["Hypercare"]) if assignments["Hypercare"] else "",
            "SIMs": assignments["SIMs"],
            "DOR Call": ", ".join(assignments["DOR Call"]) if assignments["DOR Call"] else "",
            "WIMS Cases": ", ".join(assignments["WIMS Cases"]) if assignments["WIMS Cases"] else "",
            "EOD Report": ", ".join(assignments["EOD Report"]) if assignments["EOD Report"] else "",
            "WIMS Breaks (merged)": break_table_text
        }
        table_data.append(row)
        
        previous_day_hypercare = set(hypercare_assignments)
    
    df = pd.DataFrame(table_data)
    return df

def create_daily_statistics_table(holiday_off_df, task_table, days_of_week):
    """
    Create a statistics table showing actual counts from the generated rota
    
    Args:
        holiday_off_df: DataFrame with holiday/off status per person per day
        task_table: Generated rota table with task assignments
        days_of_week: List of days to analyze
    
    Returns:
        DataFrame with daily statistics
    """
    stats_data = []
    
    for day in days_of_week:
        day_name = day.split()[0]
        
        # Find matching column in holiday_off_df
        day_col = None
        if day in holiday_off_df.columns:
            day_col = day
        else:
            matches = [c for c in holiday_off_df.columns if c.startswith(day_name)]
            if matches:
                day_col = matches[0]
        
        if day_col is None:
            continue
        
        # Count people by status from holiday_off_df
        working_count = 0
        holiday_count = 0
        off_count = 0
        morning_count = 0
        evening_count = 0
        
        for idx, row in holiday_off_df.iterrows():
            shift_type = row.get(day_col, "Off")
            
            if shift_type == "Morning":
                morning_count += 1
                working_count += 1
            elif shift_type == "Evening":
                evening_count += 1
                working_count += 1
            elif shift_type == "Holiday":
                holiday_count += 1
            elif shift_type == "Off":
                off_count += 1
        
        # Get actual task counts from the generated rota table
        task_row = task_table[task_table['Day'] == day]
        
        if not task_row.empty and task_row.iloc[0]['Day'] != 'WIMS Status':
            row_data = task_row.iloc[0]
            
            # Count Hypercare
            hypercare_str = str(row_data.get('Hypercare', ''))
            hypercare_count = len([x for x in hypercare_str.split(',') if x.strip()]) if hypercare_str else 0
            
            # Count SIMs (AM + PM + Night)
            sims_str = str(row_data.get('SIMs', ''))
            sims_count = sims_str.count(':') if sims_str else 0
            
            # Count DOR
            dor_str = str(row_data.get('DOR Call', ''))
            dor_count = len([x for x in dor_str.split(',') if x.strip()]) if dor_str else 0
            
            # Count EOD
            eod_str = str(row_data.get('EOD Report', ''))
            eod_count = len([x for x in eod_str.split(',') if x.strip()]) if eod_str else 0
            
            # Count WIMS Cases
            wims_str = str(row_data.get('WIMS Cases', ''))
            wims_count = len([x for x in wims_str.split(',') if x.strip()]) if wims_str else 0
        else:
            # Default values if task row not found
            is_weekend = day_name in ["Sun", "Mon", "Sat"]
            hypercare_count = 1 if is_weekend else 2
            sims_count = 3  # AM + PM + Night
            dor_count = 0 if day_name in ["Sun", "Sat"] else 1
            eod_count = 1
            wims_count = max(0, working_count - hypercare_count - dor_count - eod_count)
        
        stats_row = {
            "Day": day,
            "Total Working": working_count,
            "Morning Shift": morning_count,
            "Evening Shift": evening_count,
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


# Sidebar for configuration
st.sidebar.header("⚙️ Configuration")

# File upload
uploaded_file = st.sidebar.file_uploader("Upload Schedule CSV", type=['csv', 'xlsx'])

# Hypercare list input
st.sidebar.subheader("Hypercare Team")
hypercare_default = "wpatchan, esinumac, ratilalr, mariebak, azeemaj"
hypercare_input = st.sidebar.text_area("Hypercare List (comma-separated)", value=hypercare_default)
hypercare_list = [name.strip() for name in hypercare_input.split(',')]

# Hyderabad team input
st.sidebar.subheader("Hyderabad Team")
hyd_default = "harshith, parinay, shrisha, tulasi, rajkumar, nishanth"
hyd_input = st.sidebar.text_area("Hyderabad Team (comma-separated)", value=hyd_default)
hyd_team = [name.strip() for name in hyd_input.split(',')]

# Days of week input
st.sidebar.subheader("Week Days")

# Auto-detect dates if file is uploaded
if uploaded_file is not None and df is not None:
    detected_dates = extract_dates_from_schedule(df)
    if detected_dates:
        days_default = ", ".join(detected_dates)
        st.sidebar.success(f"✅ Auto-detected {len(detected_dates)} days from file")
    else:
        days_default = "Sun 19Oct2025, Mon 20Oct2025, Tue 21Oct2025, Wed 22Oct2025, Thu 23Oct2025, Fri 24Oct2025, Sat 25Oct2025"
        st.sidebar.info("ℹ️ Using default dates (no dates found in file)")
else:
    days_default = "Sun 19Oct2025, Mon 20Oct2025, Tue 21Oct2025, Wed 22Oct2025, Thu 23Oct2025, Fri 24Oct2025, Sat 25Oct2025"

days_input = st.sidebar.text_area("Days (comma-separated)", value=days_default)
days_of_week = [day.strip() for day in days_input.split(',')]

# Break table input
st.sidebar.subheader("Break Schedule")
break_default = "Kapil 14:00 / Ans 14:30 / Anushka 15:00 / Darshan 15:30 / Tommaso 16:00 / Azeem 15:30 / Jose 16:30 / Keerthi 16:00 / Delia 15:30 / MB 13:00 / Moses 13:30 / Priyesha 13:30 / Prasad 13:30 / Sajid 14:30 / Marie 13:00 / Luis 12:30 / Andrea P 15:15"
break_input = st.sidebar.text_area("Break Table", value=break_default, height=100)

# Random seed
random_seed = st.sidebar.number_input("Random Seed (for reproducibility)", value=42, min_value=0)

# Main content
if uploaded_file is not None:
    try:
        # Read the uploaded file (CSV or Excel)
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file, engine='openpyxl')
        
        st.success("✅ Schedule file uploaded successfully!")
        
        # Show preview
        with st.expander("📋 Preview Uploaded Data"):
            st.dataframe(df.head(10))
        
        # Process button
        if st.button("🚀 Generate Rota", type="primary"):
            with st.spinner("Processing schedule..."):
                # Process the schedule
                shift_summary, holiday_off_df = process_schedule_csv(df)
                
                # Create task table
                task_table = create_task_by_day_table(
                    holiday_off_df, 
                    hypercare_list, 
                    hyd_team, 
                    days_of_week, 
                    break_input,
                    random_seed
                )
                
                # Create statistics table
                stats_table = create_daily_statistics_table(
                    holiday_off_df, 
                    task_table, 
                    days_of_week
                )
                
                if task_table is not None:
                    st.success("✅ Rota generated successfully!")
                    
                    # Display results in tabs
                    tab1, tab2, tab3, tab4 = st.tabs([
                        "📅 Weekly Rota", 
                        "📊 Daily Statistics",
                        "👥 Shift Summary", 
                        "🏖️ Holiday/Off Schedule"
                    ])
                    
                    with tab1:
                        st.subheader("Weekly Task Assignments")
                        st.dataframe(task_table, use_container_width=True)
                        
                        # Download button
                        csv_buffer = io.StringIO()
                        task_table.to_csv(csv_buffer, index=False)
                        st.download_button(
                            label="📥 Download Rota CSV",
                            data=csv_buffer.getvalue(),
                            file_name="task_rota_generated.csv",
                            mime="text/csv"
                        )
                    
                    with tab2:
                        st.subheader("Daily Statistics & Task Counts")
                        st.dataframe(stats_table, use_container_width=True)
                        
                        # Add summary metrics
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
                        
                        csv_buffer_stats = io.StringIO()
                        stats_table.to_csv(csv_buffer_stats, index=False)
                        st.download_button(
                            label="📥 Download Statistics",
                            data=csv_buffer_stats.getvalue(),
                            file_name="daily_statistics.csv",
                            mime="text/csv"
                        )
                    
                    with tab3:
                        st.subheader("Shift Summary")
                        st.dataframe(shift_summary, use_container_width=True)
                        
                        csv_buffer2 = io.StringIO()
                        shift_summary.to_csv(csv_buffer2, index=False)
                        st.download_button(
                            label="📥 Download Shift Summary",
                            data=csv_buffer2.getvalue(),
                            file_name="shift_summary.csv",
                            mime="text/csv"
                        )
                    
                    with tab4:
                        st.subheader("Holiday/Off Schedule")
                        st.dataframe(holiday_off_df, use_container_width=True)
                        
                        csv_buffer3 = io.StringIO()
                        holiday_off_df.to_csv(csv_buffer3)
                        st.download_button(
                            label="📥 Download Holiday/Off Schedule",
                            data=csv_buffer3.getvalue(),
                            file_name="holiday_off_schedule.csv",
                            mime="text/csv"
                        )
    
    except Exception as e:
        st.error(f"❌ Error processing file: {str(e)}")
        st.exception(e)

else:
    st.info("👈 Please upload a schedule CSV or Excel file to get started")
    
    st.markdown("""
    ### 📖 How to Use
    
    1. **Upload your schedule file** in the sidebar
       - Supports CSV (.csv) or Excel (.xlsx) files
       - Must contain a 'login' column with employee usernames
       - Should have columns for each day with shift codes (A, A1, A2, H, BH, etc.)
    
    2. **Configure your teams** in the sidebar:
       - Hypercare team members
       - Hyderabad team members
       - Week days to schedule
       - Break schedule
    
    3. **Click "Generate Rota"** to create the weekly assignments
    
    4. **Download the results** as CSV files from each tab
    
    ### 📋 File Format Example
    
    Your file should look like this:
    
    | Login | Name | Base | Monday | Tuesday | Wednesday | ... |
    |-------|------|------|--------|---------|-----------|-----|
    | user1 | John | BHX2 | A      | A1      | H         | ... |
    | user2 | Jane | BCN14| A1     | A2      | BH        | ... |
    
    ### 🔤 Shift Codes
    
    - **A** = AM Shift (09:30-18:00)
    - **A1** = Mid shift (11:30-20:00)
    - **A2** = PM shift (14:00-22:30)
    - **H** = Annual Leave
    - **BH** = Bank Holiday
    - **P** = Personal Leave
    - **S** = Sick Leave
    - And more... (see shift legends in code)
    """)

# Footer
st.sidebar.markdown("---")
st.sidebar.markdown("**Amazon Rota System v1.0**")
st.sidebar.markdown("*Built with Streamlit*")

