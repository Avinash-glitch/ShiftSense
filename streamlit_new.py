# app.py - Daily Assignment Generator with improved UI
import streamlit as st
import pandas as pd
import json
import os
import sys
from datetime import datetime,timedelta
from daily_assignment import generate_daily_assignments
from coverage import calculate_coverage_from_shifts
from get_eligible_employees import clear_all_task_data
from debugger import get_debug_logs, clear_logs, get_all_logs
from parse_json import get_shift_groups_for_day
from test_dataextraction_holiday import check_if_person_working_today

# working_code = ["S1", "S2", "S3", "S4", "wfh", "Wfh", "WFH"]
def _ensure_employee_exists(person, all_employees):
    """Ensure employee exists in records"""
    TASKS = ["hypercare", "sim", "dor", "wims", "eod"]
    if person not in all_employees:
        all_employees[person] = {
            "history": {},
            "total_counts": {t: 0 for t in TASKS},
            "task_flags": {t: False for t in TASKS}
        }

def parse_shift_time(shift_str, base_date):
    """Parse shift time like '11:30-20:00' or '23:30-08:30' (overnight)"""
    start_str, end_str = shift_str.split('-')
    start_hour, start_min = map(int, start_str.split(':'))
    end_hour, end_min = map(int, end_str.split(':'))

    start_dt = f"{base_date}T{start_hour:02d}:{start_min:02d}:00"

    # If end time is earlier than start time, it's an overnight shift
    if end_hour < start_hour:
        next_date = datetime.strptime(base_date, '%Y-%m-%d') + timedelta(days=1)
        end_dt = f"{next_date.strftime('%Y-%m-%d')}T{end_hour:02d}:{end_min:02d}:00"
    else:
        end_dt = f"{base_date}T{end_hour:02d}:{end_min:02d}:00"

    return start_dt, end_dt



# Page configuration
st.set_page_config(
    page_title="Shift Sense",
    # page_icon="",
    layout="wide",
    initial_sidebar_state= "expanded",

)


# 👇 ADD THIS CSS TO REMOVE SIDEBAR PADDING
st.markdown("""
    <style>
            }
          .sidebar {
            padding: 0;          /* remove all padding */
            margin: 0;           /* remove margin if any */
        }

        .sidebar .image {
            margin: 0;           /* kill internal margins */
            padding: 0;          /* kill padding */
            display: block;      /* removes extra space from inline element */
        }
""", unsafe_allow_html=True)

# Custom CSS for styling
st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;

        font-family: "Orbitron", sans-serif;
        font-weight: 400;
 
        color: #1f77b4;
        margin-bottom: 1rem;
    }
    .instruction-box {
        background-color: #f0f2f6;
        padding: 1.5rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
        margin-bottom: 2rem;
    }
    .instruction-box h3 {
        margin-top: 0;
        color: #1f77b4;
    }
    </style>
""", unsafe_allow_html=True)




st.markdown("""
    <style>
    /* Classy Button Styling */
    .stButton > button,.stDownloadButton > button  {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        font-weight: bold;
        padding: 12px 24px;
        border: none;
        border-radius: 8px;
        cursor: pointer;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(0,0,0,0.3);
    }
    
    /* Primary Action Buttons */
    .primary-btn {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    
    /* Secondary Action Buttons */
    .secondary-btn {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
    }
    </style>
""", unsafe_allow_html=True)

# Get the base directory (works whether running from source or exe)
if getattr(sys, 'frozen', False):
    # Running as exe
    BASE_DIR = sys._MEIPASS
else:
    # Running as script
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))


# Define paths
LOGO_PATH = os.path.join(BASE_DIR, 'logo1.png')
ICON_PATH = os.path.join(BASE_DIR, 'icon.png')
# Sidebar
with st.sidebar:
    # Center the logo
    col1, col2 = st.columns([0.85, 0.15])
    
    with col1:
      
        st.image(LOGO_PATH, width=150)
    
    # st.markdown("---")
    st.markdown("<p style='text-align: left; color: gray; font-size: 12px;'>--Created by Avinash Kannan</p>", unsafe_allow_html=True)
    st.markdown("---")

    # # Hypercare list customization
    # col_icon_workingCode, col_title_workingCode = st.columns([0.15, 0.85])
    
    # with col_icon_workingCode:
    #     st.image(ICON_PATH, width=70)
    
    # with col_title_workingCode:
    #     st.markdown("Working Codes")
    
    # default_workingCodes = ["S1", "S2", "S3", "S4", "wfh", "Wfh", "WFH"]
    # workingCodesInput = st.text_area(
    #     "",
    #     ",".join(default_workingCodes),
    #     height=100,
    #     help="Edit List of working codes (comma separated) as mentioned in the Holiday tracker file",
    #     placeholder="Enter working codes separated by commas"
    # )
    # WorkingCodes = [x.strip().lower() for x in workingCodesInput.split(",") if x.strip()]

    # Hypercare list customization
    col_icon_hype, col_title_hype = st.columns([0.15, 0.85])
    
    with col_icon_hype:
        st.image(ICON_PATH, width=70)
    
    with col_title_hype:
        st.markdown("Hypercare Team")
    
    default_hypercare = ["wpatchan", "esinumac", "ratilalr", "mariebak", "azeemaj"]
    hypercare_input = st.text_area(
        "",
        ",".join(default_hypercare),
        height=100,
        help="Edit Hypercare List (comma separated)",
        placeholder="Enter hypercare logins separated by commas"
    )
    hypercare_list = [x.strip().lower() for x in hypercare_input.split(",") if x.strip()]
    with st.sidebar:
            # Center the logo
        col_icon_mark, col_title_mark = st.columns([0.15, 0.85])
    
        with col_icon_mark:
            st.image(ICON_PATH, width=100)
        
        with col_title_mark:
            st.markdown("Manage Assignments")
        col1, col2 = st.columns(2)
        
        # === MARK ===
        with col1:
            st.markdown("### ✅ Mark")
            
            employee = st.text_input("Employee Login", key="mark_login")
            task = st.selectbox("Task", ["hypercare", "sim", "dor", "wims", "eod"], key="mark_task")
            date_str = st.text_input("Date (DD/MM/YYYY)", placeholder="21/12/2025", key="mark_date")
            sim_slot = None
            
            if task == "sim":
                sim_slot = st.selectbox("SIM Slot", ["morning", "mid", "night", "midnight"], key="mark_sim_slot")
            
            if st.button("Mark", use_container_width=True, type="primary", key="mark_btn"):
                if not employee or not date_str:
                    st.error("❌ Please fill in all fields")
                else:
                    try:
                        from get_eligible_employees import mark_employee_assigned
                        mark_employee_assigned(employee, task, date_str, sim_slot=sim_slot)
                        st.success(f"✅ Marked {employee} for {task} on {date_str}")
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
        
        # === UNMARK ===
        with col2:
            st.markdown("### ❌Unmark ")
            
            employee_u = st.text_input("Employee Login", key="unmark_login")
            task_u = st.selectbox("Task", ["hypercare", "sim", "dor", "wims", "eod"], key="unmark_task")
            date_u = st.text_input("Date (DD/MM/YYYY)", placeholder="21/12/2025", key="unmark_date")
            sim_slot_u = None
            
            if task_u == "sim":
                sim_slot_u = st.selectbox("SIM Slot", ["morning", "mid", "night", "midnight"], key="unmark_sim_slot")
            
            if st.button("Unmark", use_container_width=True, key="unmark_btn"):
                if not employee_u or not date_u:
                    st.error("❌ Please fill in all fields")
                else:
                    try:
                        from get_eligible_employees import unmark_employee_assigned
                        unmark_employee_assigned(employee_u, task_u, date_u, sim_slot=sim_slot_u)
                        st.success(f"✅ Unmarked {employee_u} from {task_u} on {date_u}")
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")

    with st.sidebar:
            st.subheader("📤 Upload Edited rota")
            
            uploaded_file = st.file_uploader("Upload rota CSV file", type=['csv'], key="rota_upload")
            
            if uploaded_file:
                # Read CSV
                df = pd.read_csv(uploaded_file)
                
                st.markdown("### 📊 Preview & Edit")
                st.info("Edit the table below, then click 'Save Changes'")
                
                # Display editable dataframe
                edited_df = st.data_editor(
                    df,
                    use_container_width=True,
                    key="rota_editor",
                    height=400
                )
                
                if st.button("💾 Save Changes to task_data.json", type="primary", use_container_width=True, key="save_rota"):
                    try:
                        from get_eligible_employees import load_data, save_data
                        
                        data = load_data()
                        all_employees = data["employees"]
                        date_assignments = data["date_assignments"]
                        
                        processed_count = 0
                        
                        for idx, row in edited_df.iterrows():
                            date_str = str(row.get("Day", "")).strip()
                            
                            # Skip header/status rows
                            if "WIMS Status" in date_str or "status" in date_str.lower():
                                continue
                            
                            # Extract date
                            if "(" in date_str:
                                date_str = date_str.split("(")[0].strip()
                            
                            if not date_str or date_str.lower() == "day":
                                continue
                            
                            # Initialize date
                            if date_str not in date_assignments:
                                date_assignments[date_str] = {
                                    "hypercare": None,
                                    "sim": {"morning": None, "mid": None, "night": None, "midnight": None},
                                    "dor": None,
                                    "wims": [],
                                    "eod": None
                                }
                            
                            # Process Hypercare
                            hypercare = str(row.get("Hypercare", "")).strip()
                            if hypercare and hypercare.lower() not in ["na", "nan", ""]:
                                _ensure_employee_exists(hypercare, all_employees)
                                date_assignments[date_str]["hypercare"] = hypercare
                                processed_count += 1
                            
                            # Process SIM
                            sim_str = str(row.get("SIMs", "")).strip()
                            if sim_str and sim_str.lower() != "na":
                                parts = sim_str.split("|")
                                for part in parts:
                                    part = part.strip()
                                    if ":" in part:
                                        slot, person = part.split(":", 1)
                                        slot = slot.strip().lower()
                                        person = person.strip()
                                        
                                        slot_map = {"am": "morning", "pm": "mid", "night": "night"}
                                        slot = slot_map.get(slot, slot)
                                        
                                        if person and person.lower() not in ["na", "hyd"]:
                                            _ensure_employee_exists(person, all_employees)
                                            date_assignments[date_str]["sim"][slot] = person
                                            processed_count += 1
                            
                            # Process DOR
                            dor = str(row.get("DOR Call", "")).strip()
                            if dor and dor.lower() not in ["na", "nan", "no dor", ""]:
                                _ensure_employee_exists(dor, all_employees)
                                date_assignments[date_str]["dor"] = dor
                                processed_count += 1
                            
                            # Process EOD
                            eod = str(row.get("EOD Report", "")).strip()
                            if eod and eod.lower() not in ["na", "nan", ""]:
                                _ensure_employee_exists(eod, all_employees)
                                date_assignments[date_str]["eod"] = eod
                                processed_count += 1
                            
                            # Process WIMS
                            wims_str = str(row.get("WIMS Cases", "")).strip()
                            if wims_str and wims_str.lower() != "na":
                                people = [p.strip() for p in wims_str.split(",")]
                                date_assignments[date_str]["wims"] = []
                                for person in people:
                                    if person and person.lower() not in ["na", "nan", ""]:
                                        _ensure_employee_exists(person, all_employees)
                                        if person not in date_assignments[date_str]["wims"]:
                                            date_assignments[date_str]["wims"].append(person)
                                        processed_count += 1
                        
                        save_data(data)
                        st.success(f"✅ Saved {processed_count} assignments to task_data.json!")
                        st.balloons()
                        
                    except Exception as e:
                        st.error(f"❌ Error saving: {str(e)}")


# ==================== MAIN CONTENT ====================    
# Main content area
st.markdown('<div class="main-header">Smart Shift Planner</div>', unsafe_allow_html=True)

# Instruction box
st.markdown("""
    <div class="instruction-box">
        <h4>📌 How to Use</h4>
        <ol>
            <li><strong>Upload Files:</strong> Use the buttons below to upload your schedule and holiday tracker Excel files</li>
            <li><strong>Customize Team:</strong> Edit the hypercare list in the sidebar if needed</li>
            <li><strong>Generate:</strong> Click the "Generate Assignments" button to process the data</li>
            <li><strong>View Results:</strong> Switch between tabs to see assignments, coverage, and statistics</li>
            <li><strong>Export:</strong> Use the download buttons in each tab to save the tables as CSV</li>
        </ol>
    </div>
""", unsafe_allow_html=True)



st.markdown("---")

# File uploads
schedule_file = st.file_uploader(
    "Upload Schedule JSON",
    type=["json"],
    help="Upload your schedule.json file"
)

excel_file = st.file_uploader(
    "Upload Holiday Tracker",
    type=["xlsx", "xls"],
    help="Upload your holiday_tracker.xlsx file"
)

st.markdown("---")

# Generate button
generate_button = st.button("🚀 Generate Assignments", use_container_width=True, type="primary")


# Generate assignments
if schedule_file and excel_file:
    if generate_button:
        try:
            schedule_data = json.load(schedule_file)
            df = pd.read_excel(excel_file)
            assignments = generate_daily_assignments(schedule_data, df, hypercare_list)
            # # Get name mapping
            # login_to_name = get_login_to_name_mapping(df)

            # # Convert all logins to names for display
            # assignments_with_names = convert_rota_logins_to_names(assignments, login_to_name)
            # Store in session state for reuse
            st.session_state.assignments = assignments
            st.session_state.schedule_data = schedule_data
            st.session_state.df = df
            st.session_state.assignment_dates = [
                datetime.strptime(a['date'], "%d/%m/%Y").strftime("%a") 
                for a in assignments
            ]
            
            st.success("✅ Assignments generated successfully!")
            
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")


# Find this section in your streamlit_new.py where the Generate button is
# and replace it with this code:

# Display results if available
if hasattr(st.session_state, 'assignments'):
    assignments = st.session_state.assignments
    # After: assignments = generate_daily_assignments(...)


    

# Now use assignments_with_names for displaying/downloading
    schedule_data = st.session_state.schedule_data
    df = st.session_state.df
    assignment_dates = st.session_state.assignment_dates

    # Create tabs
    tab1, tab2, tab3= st.tabs(["Daily Assignments", "🕐 Coverage Summary", "📈 Shift Statistics"])

    
    
    # ==================== TAB 1: DAILY ASSIGNMENTS ====================
    with tab1:
        st.subheader("Daily Assignments")
        
        rows = []
        for a in assignments:
            hypercare_str = ", ".join(a["hypercare"]) if a["hypercare"] else "N/A"
            
            sim_parts = []
            for slot, person in a["sim"].items():
                if person:
                    sim_parts.append(f"{slot}: {person}")
            sim_str = " | ".join(sim_parts) if sim_parts else "N/A"
            
            wims_str = ", ".join(a["wims"]) if a["wims"] else "N/A"
            
            rows.append({
                "Day": f"{a['date']} ({a['day']})",
                "Hypercare": hypercare_str,
                "SIMs": sim_str,
                "DOR Call": a["dor"] if a["dor"] else "N/A",
                "WIMS Cases": wims_str,
                "EOD Report": a.get("eod", "N/A") if a.get("eod") else "N/A",
                "Break": "Fixed List"
            })
        
        status_row = {
            "Day": "WIMS Status",
            "Hypercare": "on project",
            "SIMs": "Available",
            "DOR Call": "In meeting",
            "WIMS Cases": "Available",
            "EOD Report": "On Project",
            "Break": ""
        }
        
        df_display = pd.DataFrame([status_row] + rows)
        st.dataframe(df_display, use_container_width=True)
        
        # Create 3 columns (left, center, right)
        col1, col2, col3 = st.columns(3)
        csv = df_display.to_csv(index=False)
        # Put button in the middle column
        with col2:
            st.download_button(
                label="📥 Download as CSV",
                data=csv,
                file_name="daily_assignments.csv",
                mime="text/csv",
                use_container_width=True,  # Make it fill the column
                key="download_daily_assignments"
            )
      
    
    # ==================== TAB 2: COVERAGE SUMMARY ====================
    with tab2:
        st.subheader("Daily Coverage Summary")
        
        coverage_rows = []
        next_day_hours = 0
        for a in assignments:
            cov = a.get("coverage", "No Coverage")
            
            # Use the coverage calculation function
            if cov != "No Coverage":
                all_shift_times = [cov]
                coverage_str, hours_breakdown = calculate_coverage_from_shifts(all_shift_times, test=False)
            else:
                coverage_str = "No Coverage"
                hours_breakdown = {"current_day": 0, "next_day": 0}
            
            total_hours = hours_breakdown["current_day"] + next_day_hours
            if total_hours > 24:
                total_hours = 24
            pct = total_hours / 24 * 100 if total_hours > 0 else 0
            next_day_hours = hours_breakdown["next_day"]
            
            coverage_rows.append({
                "Day": f"{a['date']} ({a['day']})",
                "Coverage Window": coverage_str,
                "Hours Covered": f"{total_hours:.1f}h",
                "Coverage %": f"{pct:.1f}%"
            })
        
        df_coverage = pd.DataFrame(coverage_rows)
        st.dataframe(df_coverage, use_container_width=True)
        
        col1, col2, col3 = st.columns(3)
        csv = df_display.to_csv(index=False)
        # Put button in the middle column
        with col2:
            st.download_button(
                label="📥 Download as CSV",
                data=csv,
                file_name="coverage_summary.csv",
                mime="text/csv",
                use_container_width=True,  # Make it fill the column
                key="download_coverage_csv"
            )
        
    
    # ==================== TAB 3: SHIFT STATISTICS ====================
    with tab3:
        st.subheader("Shift Statistics")
        
       
        
        stats_rows = []
        
        for i, a in enumerate(assignments):
            day_abbr = assignment_dates[i]
            shift_lists = get_shift_groups_for_day(schedule_data, day_abbr)
            
            shift_types_to_include = ["morning", "mid", "night", "midnight"]
            row_data = {"Day": f"{a['date']} ({a['day']})"}
            daily_total = 0
            
            for shift_type in shift_types_to_include:
                if shift_type not in shift_lists:
                    row_data[shift_type.upper()] = 0
                    continue
                
                names = shift_lists[shift_type]
                working_count = 0
                
                for login in names:
                    status = check_if_person_working_today(a['date'], login, df,WorkingCodes)
                    if status == "Working":
                        working_count += 1
                
                daily_total += working_count
                row_data[shift_type.upper()] = working_count
            
            row_data["TOTAL"] = daily_total
            stats_rows.append(row_data)
        
        df_stats = pd.DataFrame(stats_rows)
        st.dataframe(df_stats, use_container_width=True)
        
        col1, col2, col3 = st.columns(3)
        csv = df_display.to_csv(index=False)
        # Put button in the middle column
        with col2:
            st.download_button(
                label="📥 Download as CSV",
                data=csv,
                file_name="shift_statistics.csv",
                mime="text/csv",
                use_container_width=True,  # Make it fill the column
                key="download_shift_statistics_csv"
            )
    
    # ==================== SIDEBAR: SEARCH LOGIN HISTORY ====================
    with st.sidebar:
        st.markdown("---")
        col_icon_search, col_title_search = st.columns([0.15, 0.85])
    
        with col_icon_search:
            st.image(ICON_PATH, width=70)
        
        with col_title_search:
            st.markdown("Search Login History")
            # st.subheader("🔍 Search Login History")
        
        search_login = st.text_input("Enter login name to search:")
        if search_login:
            # Search through assignments
            found_assignments = []
            for a in assignments:
                # Check Hypercare
                if search_login.lower() in [x.lower() for x in a.get("hypercare", [])]:
                    found_assignments.append({"Date": a['date'], "Day": a['day'], "Role": "Hypercare"})
                
                # Check WIMS
                if search_login.lower() in [x.lower() for x in a.get("wims", [])]:
                    found_assignments.append({"Date": a['date'], "Day": a['day'], "Role": "WIMS"})
                
                # Check SIMs (dict with slots)
                sims_list = a.get("sim", {})
                if isinstance(sims_list, dict):
                    for slot, person in sims_list.items():
                        if person and search_login.lower() == person.lower():
                            found_assignments.append({"Date": a['date'], "Day": a['day'], "Role": f"SIM - {slot}"})
                
                # Check DOR (Direct on Rota)
                dor = a.get("dor", "")
                if dor and search_login.lower() == dor.lower():
                    found_assignments.append({"Date": a['date'], "Day": a['day'], "Role": "DOR Call"})
                
                # Check EOD Report
                eod = a.get("eod", "")
                if eod and search_login.lower() == eod.lower():
                    found_assignments.append({"Date": a['date'], "Day": a['day'], "Role": "EOD Report"})
            
            if found_assignments:
                st.success(f"✅ Found {len(found_assignments)} assignments for {search_login}")
                df_history = pd.DataFrame(found_assignments)
                st.dataframe(df_history, use_container_width=True)
                
                # Download history
                csv = df_history.to_csv(index=False)
                st.download_button(
                    label=" Download ",
                    data=csv,
                    file_name=f"{search_login}_assignments.csv",
                    mime="text/csv",
                    use_container_width=False
                )
            else:
                st.warning(f"❌ No assignments found for {search_login}")
        # Insert after the existing tabs section

 # ==================== ADMIN PANEL ====================
    st.markdown("---")
    
    # Admin panel tabs
    admin_tab1, admin_tab2, admin_tab3, admin_tab4 = st.tabs(["👤 View/Edit Member Shift", "➕ Add/Remove Members", "📋 View All Schedule","🗑️ Data Management"])
  

    # ==================== ADMIN TAB 1: VIEW/EDIT MEMBER SHIFT ====================
    with admin_tab1:
        st.subheader("👤 View & Edit Member Shift")
        
        # Get all logins from schedule
        all_logins = sorted(list(schedule_data.keys()))
        
        col1, col2 = st.columns([2, 1])
        with col1:
            selected_login = st.selectbox("Select Member", all_logins, key="member_select")
        
        if selected_login:
            # Display current shifts for the week
            member_data = schedule_data.get(selected_login, {})
            
            st.subheader(f"Shifts for {selected_login}")
            
            # Create editable table with unique keys per login
            shifts_dict = {}
            col1, col2, col3, col4, col5, col6, col7 = st.columns(7)
            
            days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
            
            with col1:
                shifts_dict["Mon"] = st.text_input("Monday", value=member_data.get("Mon", ""), key=f"{selected_login}_mon")
            with col2:
                shifts_dict["Tue"] = st.text_input("Tuesday", value=member_data.get("Tue", ""), key=f"{selected_login}_tue")
            with col3:
                shifts_dict["Wed"] = st.text_input("Wednesday", value=member_data.get("Wed", ""), key=f"{selected_login}_wed")
            with col4:
                shifts_dict["Thu"] = st.text_input("Thursday", value=member_data.get("Thu", ""), key=f"{selected_login}_thu")
            with col5:
                shifts_dict["Fri"] = st.text_input("Friday", value=member_data.get("Fri", ""), key=f"{selected_login}_fri")
            with col6:
                shifts_dict["Sat"] = st.text_input("Saturday", value=member_data.get("Sat", ""), key=f"{selected_login}_sat")
            with col7:
                shifts_dict["Sun"] = st.text_input("Sunday", value=member_data.get("Sun", ""), key=f"{selected_login}_sun")
            
            # Save button for member shifts
            if st.button("💾 Save Shifts", use_container_width=False, key=f"save_shifts_{selected_login}"):
                # Remove empty strings
                shifts_dict = {day: shift.strip() for day, shift in shifts_dict.items() if shift.strip()}
                
                schedule_data[selected_login] = shifts_dict
                
                # Save to JSON file
                try:
                    with open(r"schedule.json", "w") as f:
                        json.dump(schedule_data, f, indent=2)
                    
                    # Update session state
                    st.session_state.schedule_data = schedule_data
                    
                    st.success(f"✅ Shifts updated for {selected_login}!")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error saving: {str(e)}")
    
    # ==================== ADMIN TAB 2: ADD/REMOVE MEMBERS ====================
    with admin_tab2:
        st.subheader("➕ Add/Remove Members")
        
        col1, col2 = st.columns(2)
        
        # Add new member
        with col1:
            st.subheader("Add New Member")
            new_login = st.text_input("New Member Login", placeholder="e.g., johndoe")
            
            if new_login:
                st.info(f"Enter shifts for {new_login} (or leave blank for days off)")
                
                col_a, col_b, col_c, col_d, col_e, col_f, col_g = st.columns(7)
                new_shifts = {}
                
                with col_a:
                    new_shifts["Mon"] = st.text_input("Mon", value="", key="new_mon")
                with col_b:
                    new_shifts["Tue"] = st.text_input("Tue", value="", key="new_tue")
                with col_c:
                    new_shifts["Wed"] = st.text_input("Wed", value="", key="new_wed")
                with col_d:
                    new_shifts["Thu"] = st.text_input("Thu", value="", key="new_thu")
                with col_e:
                    new_shifts["Fri"] = st.text_input("Fri", value="", key="new_fri")
                with col_f:
                    new_shifts["Sat"] = st.text_input("Sat", value="", key="new_sat")
                with col_g:
                    new_shifts["Sun"] = st.text_input("Sun", value="", key="new_sun")
                
                if st.button("➕ Add Member", use_container_width=True, key="add_member"):
                    if new_login not in schedule_data:
                        schedule_data[new_login] = new_shifts
                        
                        try:
                            with open(r"C:\Users\avikann\rota\schedule.json", "w") as f:
                                json.dump(schedule_data, f, indent=2)
                            
                            # Update session state
                            st.session_state.schedule_data = schedule_data
                            
                            st.success(f"✅ Member {new_login} added successfully!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Error saving: {str(e)}")
                    else:
                        st.error(f"❌ {new_login} already exists!")
        
        # Remove member
        with col2:
            st.subheader("Remove Member")
            
            all_logins = sorted(list(schedule_data.keys()))
            member_to_remove = st.selectbox("Select Member to Remove", all_logins, key="remove_member_select")
            
            if member_to_remove:
                st.warning(f"⚠️ Are you sure you want to remove {member_to_remove}?")
                
                if st.button("❌ Remove Member", use_container_width=True, key="remove_member"):
                    del schedule_data[member_to_remove]
                    
                    try:
                        with open(r"C:\Users\avikann\rota\schedule.json", "w") as f:
                            json.dump(schedule_data, f, indent=2)
                        
                        # Update session state
                        st.session_state.schedule_data = schedule_data
                        
                        st.success(f"✅ Member {member_to_remove} removed!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Error saving: {str(e)}")
    
    # ==================== ADMIN TAB 3: VIEW ALL SCHEDULE ====================
    with admin_tab3:
        st.subheader("📋 Complete Schedule")
        
        # Convert schedule data to DataFrame for easy viewing
        schedule_df = pd.DataFrame.from_dict(schedule_data, orient="index")
        schedule_df.index.name = "Login"
        
        st.dataframe(schedule_df, use_container_width=True)
        
        # Export full schedule
        csv = schedule_df.to_csv()
        st.download_button(
            label="📥 Download Full Schedule as CSV",
            data=csv,
            file_name="complete_schedule.csv",
            mime="text/csv",
            use_container_width=False
        )
        
        # Export as JSON
        json_str = json.dumps(schedule_data, indent=2)
        st.download_button(
            label="📥 Download as JSON",
            data=json_str,
            file_name="schedule.json",
            mime="application/json",
            use_container_width=False
        )

    with admin_tab4:
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("""
                ### 📊 Task Data Statistics
                View current assignment data and employee statistics.
            """)
            
            if st.button("📊 View Current Task Data", use_container_width=False, key="view_task_data"):
                from get_eligible_employees import load_data
                data = load_data()
                
                st.success("✅ Current Task Data Loaded")
                
                total_employees = len(data.get("employees", {}))
                total_assignments = len(data.get("date_assignments", {}))
                
                col_a, col_b = st.columns(2)
                with col_a:
                    st.metric("👥 Total Employees", total_employees)
                with col_b:
                    st.metric("📅 Assignment Dates", total_assignments)
                
                with st.expander("📈 Employee Assignment Counts", expanded=False):
                    if data.get("employees"):
                        stats_list = []
                        for emp, info in data["employees"].items():
                            stats_list.append({
                                "Login": emp,
                                "Hypercare": info["total_counts"].get("hypercare", 0),
                                "SIM": info["total_counts"].get("sim", 0),
                                "DOR": info["total_counts"].get("dor", 0),
                                "EOD": info["total_counts"].get("eod", 0),
                                "WIMS": info["total_counts"].get("wims", 0),
                                "Total": sum(info["total_counts"].values())
                            })
                        
                        stats_df = pd.DataFrame(stats_list).sort_values("Total", ascending=False)
                        st.dataframe(stats_df, use_container_width=True)
                        
                        # Download stats
                        csv = stats_df.to_csv(index=False)
                        st.download_button(
                            label="📥 Download Stats as CSV",
                            data=csv,
                            file_name="task_data_stats.csv",
                            mime="text/csv",
                            key="download_task_stats"
                        )
                    else:
                        st.info("No employee data found")
        
        with col2:
            st.markdown("""
                ### 🗑️ Clear Assignment Data
                Permanently delete all assignment history and start fresh.
                
            """)
            
            if st.button("🗑️ Clear All Task Data", use_container_width=False, key="clear_task_data_btn"):
                st.session_state.show_clear_confirmation_admin = True
        
        # Confirmation dialog for admin tab
        if st.session_state.get("show_clear_confirmation_admin", False):
            st.error("⚠️ **WARNING: You are about to permanently delete all assignment history!**")
            st.write("This includes:")
            st.write("- All employee assignment records")
            st.write("- All date assignments")
            st.write("- All task cycle data")
            st.write("- All task flags and history")
            
            col_x, col_y = st.columns(2)
            
            with col_x:
                if st.button("✅ Yes, Clear Everything", use_container_width=True, key="confirm_clear"):
                    from get_eligible_employees import clear_all_task_data
                    
                    try:
                        clear_all_task_data()
                        st.success("✅ All task data has been cleared successfully!")
                        st.info("ℹ️ The page will refresh automatically...")
                        st.session_state.show_clear_confirmation_admin = False
                        import time
                        time.sleep(2)
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Error clearing data: {str(e)}")
            
            with col_y:
                if st.button("❌ Cancel", use_container_width=True, key="cancel_clear"):
                    st.session_state.show_clear_confirmation_admin = False
                    st.rerun()

    # REPLACE THIS LINE:
# admin_tab1, admin_tab2, admin_tab3, admin_tab4 = st.tabs([...])


# ... keep your existing admin_tab1, admin_tab2, admin_tab3, admin_tab4 code ...

# ============================================================================
# NEW TAB 5: MARK/UNMARK
# ============================================================================

   