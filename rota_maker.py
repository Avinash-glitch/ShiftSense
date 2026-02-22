
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

# === Functions ===
def extract_shift_time(shift_str):
    if not isinstance(shift_str, str):
        return None
    match = re.search(r"(\d{1,2}:\d{2}\s*-\s*\d{1,2}:\d{2})", shift_str)
    return match.group(1) if match else None

def get_shift_type(shift_str):
    """Classify shift as Morning, Evening, Holiday, Off, or NA"""
    if pd.isna(shift_str) or str(shift_str).strip() == "":
        return "Off"
    
    shift_str = str(shift_str).strip()
    
    # Explicit holidays
    if shift_str == "H" or " H" in shift_str or "Holiday" in shift_str:
        return "Holiday"
    
    # Try time-based detection
    match = re.search(r"(\d{1,2}:\d{2})", shift_str)
    if match:
        start_time = datetime.strptime(match.group(1), "%H:%M")
        return "Morning" if start_time.hour < 10 else "Evening"
    
    # Explicit morning codes
    elif any(code in shift_str for code in ["FBH0730", "FP0730"]):
        return "Morning"
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
    """Process the uploaded schedule CSV"""
    # Melt DataFrame so each person-day is a row
    long_df = df.melt(id_vars=["login"], var_name="Day", value_name="Shift")
    
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

# === Streamlit UI ===

# Sidebar for configuration
st.sidebar.header("⚙️ Configuration")

# File upload
uploaded_file = st.sidebar.file_uploader("Upload Schedule CSV", type=['csv'])

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
        # Read the uploaded CSV
        df = pd.read_csv(uploaded_file)
        
        st.success("✅ Schedule CSV uploaded successfully!")
        
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
                
                if task_table is not None:
                    st.success("✅ Rota generated successfully!")
                    
                    # Display results in tabs
                    tab1, tab2, tab3 = st.tabs(["📅 Weekly Rota", "📊 Shift Summary", "🏖️ Holiday/Off Schedule"])
                    
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
                    
                    with tab3:
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
    st.info("👈 Please upload a schedule CSV file to get started")
    
    st.markdown("""
    ### 📖 How to Use
    
    1. **Upload your schedule CSV** in the sidebar
       - Must contain a 'login' column with employee usernames
       - Should have columns for each day with shift information
    
    2. **Configure your teams** in the sidebar:
       - Hypercare team members
       - Hyderabad team members
       - Week days to schedule
       - Break schedule
    
    3. **Click "Generate Rota"** to create the weekly assignments
    
    4. **Download the results** as CSV files
    
    ### 📋 CSV Format Example
    
    Your CSV should look like this:
    
    | login | Sun 19Oct2025 | Mon 20Oct2025 | Tue 21Oct2025 | ... |
    |-------|---------------|---------------|---------------|-----|
    | user1 | Morning       | Evening       | Off           | ... |
    | user2 | Evening       | Morning       | Holiday       | ... |
    """)

# Footer
st.sidebar.markdown("---")
st.sidebar.markdown("**Amazon Rota System v1.0**")