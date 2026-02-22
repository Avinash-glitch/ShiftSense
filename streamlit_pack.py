# app.py or wherever your Streamlit code is
import streamlit as st
import pandas as pd
import json
from daily_assignment import generate_daily_assignments
from coverage import calculate_coverage_from_shifts

st.title("Daily Assignment Generator")

# Upload inputs
schedule_file = st.file_uploader("Upload schedule JSON", type=["json"])
excel_file = st.file_uploader("Upload Excel", type=["xlsx"])

# Allow editing hypercare list
default_hypercare = ["wpatchan", "esinumac", "ratilalr", "mariebak", "azeemaj"]
hypercare_input = st.text_area(
    "Hypercare List (comma separated usernames)",
    ",".join(default_hypercare)
)
hypercare_list = [x.strip().lower() for x in hypercare_input.split(",") if x.strip()]

if schedule_file and excel_file:
    schedule_data = json.load(schedule_file)
    df = pd.read_excel(excel_file)
    assignments = generate_daily_assignments(schedule_data, df, hypercare_list)
    
    # -----------------------------
    # Display formatted table
    # -----------------------------
    st.subheader("Daily Assignments")
    
    rows = []
    for a in assignments:
        # Format hypercare: join list with comma
        hypercare_str = ", ".join(a["hypercare"]) if a["hypercare"] else "N/A"
        
        # Format SIM assignments
        sim_parts = []
        for slot, person in a["sim"].items():
            if person:
                sim_parts.append(f"{slot}: {person}")
        sim_str = " | ".join(sim_parts) if sim_parts else "N/A"
        
        # Format WIMS
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
    
    # Add the special header row (WIMS Status row)
    status_row = {
        "Day": "WIMS Status",
        "Hypercare": "on project",
        "SIMs": "Available",
        "DOR Call": "In meeting",
        "WIMS Cases": "Available",
        "EOD Report": "On Project",
        "Break": ""
    }
    
    # Convert to DataFrame
    df_display = pd.DataFrame([status_row] + rows)
    st.dataframe(df_display, use_container_width=True)
    
    # ---------------------------------------
    # DAILY COVERAGE SUMMARY
    # ---------------------------------------
    st.subheader("Daily Coverage Summary")
    coverage_rows = []
    next_day_hours = 0
    for a in assignments:
        cov = a.get("coverage", "No Coverage")
  
        # Use the coverage calculation function
        # Convert coverage string back to shift times list for calculation
        if cov != "No Coverage":
            all_shift_times = [cov]
            coverage_str, hours_breakdown = calculate_coverage_from_shifts(all_shift_times, test=False)
        else:
            coverage_str = "No Coverage"
            hours_breakdown = {"current_day": 0, "next_day": 0}
        
        total_hours = hours_breakdown["current_day"] + next_day_hours
        if total_hours >24:
            total_hours =24

        next_day_hours = hours_breakdown["next_day"]
        pct = total_hours / 24 * 100 if total_hours > 0 else 0
        
        coverage_rows.append({
            "Day": f"{a['date']} ({a['day']})",
            "Coverage Window": coverage_str,
            "Hours Covered": f"{total_hours:.1f}",
            "Coverage %": f"{pct:.1f}%"
        })
    
    # Display the coverage table
    df_coverage = pd.DataFrame(coverage_rows)
    st.dataframe(df_coverage, use_container_width=True)

    # ---------------------------------------
    