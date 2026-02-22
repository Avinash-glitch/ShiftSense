

from create_shift_lists import get_filtered_shifts
from get_eligible_employees import get_eligible_employees, mark_employee_assigned, unmark_employee_assigned
import random
from datetime import datetime
import pandas as pd
from debugger import get_debug_logs, clear_logs, get_all_logs, log_debug as log_message
def build_hypercare_weekly_assignments(eligible_by_day, week_dates, week_days):
    """
    Build hypercare assignments ensuring no consecutive day assignments.
    People CAN be assigned multiple times in the same week, just not on back-to-back days.
    Uses constraint-based greedy assignment (most constrained days first).
    Does NOT mark assignments - that's done later in generate_daily_assignments.
    
    Priority system:
    - Level 1 (highest): Days where available slots exactly match requirements
    - Level 2: Days with shortages (fewer people than needed)
    - Level 3 (lowest): Days with surplus (more people than needed)
    
    Args:
        eligible_by_day: List of eligible employees per day
        week_dates: List of date strings in DD/MM/YYYY format
        week_days: List of day abbreviations (Mon, Tue, etc.)
    """
    n_days = len(week_days)
    assignments = [None] * n_days
    
    # Default requirements: 1 for Sun/Sat/Thu, 2 for others
    requirements_by_day = {
        "Sun": 1, "Sat": 1, "Thu": 1,
        "Mon": 2, "Tue": 2, "Wed": 2, "Fri": 2
    }
    
    # Make a working copy to modify
    working_eligible = [day[:] for day in eligible_by_day]
    
    # Build priority queue based on constraint level
    priority = []
    for day_idx in range(n_days):
        day_name = week_days[day_idx]
        required = requirements_by_day.get(day_name, 2)
        num_eligible = len(working_eligible[day_idx])
        
        # Calculate constraint levels:
        # Level 1 (highest priority): exact match (slots == required)
        # Level 2: shortage (slots < required)
        # Level 3 (lowest priority): surplus (slots > required)
        
        if num_eligible == required:
            constraint_level = 1  # Exact match - highest priority
            constraint_score = 0
        elif num_eligible < required:
            constraint_level = 2  # Shortage - second priority
            constraint_score = required - num_eligible  # How short we are
        else:
            constraint_level = 3  # Surplus - lowest priority
            constraint_score = num_eligible - required  # How much surplus
        
        priority.append((constraint_level, constraint_score, day_idx, required))
    
    # Sort by constraint level first, then by score within each level
    priority.sort()
    
    # Process days in priority order
    for constraint_level, constraint_score, day_idx, required in priority:
        eligible = working_eligible[day_idx]
        
        # Filter out people assigned YESTERDAY and TOMORROW (avoid consecutive days)
        filtered = eligible[:]
        
        # Remove people assigned yesterday
        if day_idx > 0 and assignments[day_idx - 1] is not None:
            filtered = [p for p in filtered if p not in assignments[day_idx - 1]]
        
        # Remove people assigned tomorrow (if already assigned)
        if day_idx < n_days - 1 and assignments[day_idx + 1] is not None:
            filtered = [p for p in filtered if p not in assignments[day_idx + 1]]
        
        # If filtering removes everyone, use original list
        if not filtered:
            filtered = eligible[:]
        
        # Assign based on availability
        if len(filtered) == 0:
            assignments[day_idx] = []  # No one available
        elif len(filtered) <= required:
            # Not enough people - take everyone available
            assignments[day_idx] = filtered[:]
        else:
            # Enough people - sample randomly
            assignments[day_idx] = random.sample(filtered, k=required)
        
        # DO NOT remove assigned people from future days
        # They can be assigned again, just not consecutively
    
    return assignments


def generate_daily_assignments(schedule_data, df, hypercare_list, custom_requirements=None):
    """
    Generate daily assignments for all tasks.
    
    Args:
        schedule_data: Schedule JSON data
        df: Holiday tracker DataFrame
        hypercare_list: List of people eligible for hypercare
        custom_requirements: Optional dict mapping day names to required hypercare slots
                           Example: {"Mon": 2, "Tue": 3, "Wed": 2, "Thu": 1, "Fri": 4, "Sat": 1, "Sun": 1}
    """
    # Extract week dates
    dates_raw = pd.to_datetime(df.iloc[0], errors="coerce")
    week_dates = [d.strftime("%d/%m/%Y") for d in dates_raw if not pd.isna(d)]
    week_days = [datetime.strptime(d, "%d/%m/%Y").strftime("%a") for d in week_dates]

    # Build eligible_by_day for hypercare
    eligible_by_day = []
    for excel_date, day in zip(week_dates, week_days):
        filtered_lists, coverage = get_filtered_shifts(schedule_data, df, excel_date)
        
        # Get all working people from all shifts
        all_working = []
        for slot in ["morning", "mid", "night", "midnight"]:
            all_working.extend(filtered_lists.get(slot, []))
        
        # Filter to only hypercare list members who are working
        working_hypercare = [p for p in hypercare_list if p in all_working]
        
        # Get eligible based on cycle (who hasn't done hypercare yet)
        eligible = get_eligible_employees(working_hypercare, "hypercare", excel_date)

        eligible_by_day.append(eligible)
    # Determine hypercare requirements per day
        
    # Build hypercare weekly assignments with optional custom requirements
    hypercare_assignments = build_hypercare_weekly_assignments(
        eligible_by_day, 
        week_dates, 
        week_days,
    )

    # Generate daily assignments
    daily_assignments = []
    
    for i, (excel_date, day) in enumerate(zip(week_dates, week_days)):
        filtered_lists, coverage = get_filtered_shifts(schedule_data, df, excel_date)
        hypercare_today = hypercare_assignments[i]

        # Mark hypercare assignments FIRST (so they're excluded from other tasks)
        for person in hypercare_today:
            mark_employee_assigned(person, "hypercare", str(excel_date))


        # SIM - one per shift slot
        sim_assignments = {}
        for slot in ["morning", "mid", "night", "midnight"]:
            candidates = [p for p in filtered_lists.get(slot, []) if p not in hypercare_today]
            if candidates:
                eligible_sim = get_eligible_employees(candidates, "sim", excel_date)
                if eligible_sim:
                    chosen = random.choice(eligible_sim)
                    sim_assignments[slot] = chosen
                    # mark_employee_assigned(chosen, "sim", str(excel_date))
                    # For SIM assignments
                    mark_employee_assigned(sim_assignments[slot], "sim", excel_date, sim_slot=slot)
                    # For WIMS (multiple people)
                    

                    # For unmark (when reassigning mid SIM)
                    
            else:
                sim_assignments[slot] = "NA"


        # === NEW LOGIC: Check if morning fallback is needed ===
        old_mid_sim = sim_assignments.get("mid", None)
        if sim_assignments["morning"] == "NA" and get_eligible_employees(filtered_lists.get("morning_fallback"), "sim", excel_date):
            # morning_fallback_used = True
            
            sim_assignments["morning"] = random.choice(get_eligible_employees(filtered_lists.get("morning_fallback"), "sim", excel_date))
            mark_employee_assigned(sim_assignments["morning"], "sim", str(excel_date), sim_slot='morning')
            
            # === NOW REASSIGN MID SIM ===
            # Get people on 11:30-20:00 shift (mid shift time)
            mid_shift_1130 = [p for p in filtered_lists.get("mid", []) if p not in hypercare_today and p not in filtered_lists.get('morning_fallback', [])]
            
            # Remove the old mid SIM from candidates
            # if old_mid_sim and old_mid_sim in mid_shift_1130:
            #     mid_shift_1130.remove(old_mid_sim)
            # UNMARK the old mid SIM person
            if old_mid_sim and old_mid_sim != "NA":
                unmark_employee_assigned(old_mid_sim, "sim", excel_date)
            if mid_shift_1130:
                eligible_mid = get_eligible_employees(mid_shift_1130, "sim", excel_date)
                if eligible_mid:
                    new_mid_sim = random.choice(eligible_mid)
                    sim_assignments["mid"] = new_mid_sim  # UPDATE to new person
                    mark_employee_assigned(new_mid_sim, "sim", excel_date, sim_slot='mid')
                    mid_shift_1130.remove(new_mid_sim)
        # === END NEW LOGIC ===
        # if sim_assignments["morning"] == "NA" and get_eligible_employees(filtered_lists.get("morning_fallback"), "sim", excel_date):

        #     sim_assignments["morning"]  = random.choice(get_eligible_employees(filtered_lists.get("morning_fallback"), "sim", excel_date))
            
        #     mark_employee_assigned(sim_assignments["morning"], "sim", excel_date, sim_slot='morning')

        if sim_assignments["night"] =="NA" and get_eligible_employees(filtered_lists.get("night_fallback"), "sim", excel_date):
            sim_assignments["night"]  = random.choice(get_eligible_employees(filtered_lists.get("night_fallback"), "sim", excel_date))
            mark_employee_assigned(sim_assignments["night"], "sim", str(excel_date),sim_slot='night')

        # DOR - from morning/mid/night shifts only
        dor_candidates = []
        for shift in ["morning", "mid", "night"]:
            dor_candidates.extend(filtered_lists.get(shift, []))
        
        # Remove hypercare and SIM people
        dor_candidates = [p for p in dor_candidates if p not in hypercare_today and p not in sim_assignments.values()]
        
        DOR_assignment = None
        if day not in ["Sat", "Sun"]:
            eligible_dor = get_eligible_employees(dor_candidates, "dor", excel_date)
            if eligible_dor:
                DOR_assignment = random.choice(eligible_dor)
                mark_employee_assigned(DOR_assignment, "dor", str(excel_date))
        else:
            DOR_assignment = "No DOR"

        # EOD REPORT - from mid + night only
        possible_eod = mid_shift_1130  + filtered_lists.get("night", [])
        
        # Remove hypercare, SIM, and DOR people
        possible_eod = [
            p for p in possible_eod 
            if p not in hypercare_today 
            and p != DOR_assignment
        ]
        
        EOD_assignment = None
        if possible_eod:
            eligible_eod = get_eligible_employees(possible_eod, "eod", excel_date)
            if eligible_eod:
                EOD_assignment = random.choice(eligible_eod)
                mark_employee_assigned(EOD_assignment, "eod", str(excel_date))

        # WIMS - everyone working except hypercare
        all_working = set()
        for slot in filtered_lists:
            all_working.update(filtered_lists.get(slot, []))
        
        wims_assignments = [p for p in all_working if p not in hypercare_today]
        for person in wims_assignments:
            mark_employee_assigned(person, "wims", excel_date)
        daily_assignments.append({
            "date": excel_date,
            "day": day,
            "hypercare": hypercare_today,
            "sim": sim_assignments,
            "dor": DOR_assignment,
            "eod": EOD_assignment,
            "wims": list(wims_assignments),
            "coverage": coverage
        })

    return daily_assignments


# Example usage
if __name__ == "__main__":
    import json
    
    # Load your data
    with open(r"C:\Users\avikann\Downloads\schedule.json") as f:
        schedule_data = json.load(f)
    
    df = pd.read_csv(r'C:\Users\avikann\Documents\holiday_tracker.xlsx', sep='\t')
    
    hypercare_list = ["wpatchan", "esinumac", "ratilalr", "mariebak", "azeemaj"]
    
    # Option 1: Use default requirements (1 for Sun/Sat/Thu, 2 for others)
    assignments = generate_daily_assignments(schedule_data, df, hypercare_list)
    
    # Option 2: Use custom requirements (e.g., up to 4 people)
    custom_reqs = {
        "Mon": 2, "Tue": 2, "Wed": 3, "Thu": 1,
        "Fri": 4, "Sat": 1, "Sun": 1
    }
    assignments = generate_daily_assignments(
        schedule_data, 
        df, 
        hypercare_list,
        custom_requirements=custom_reqs
    )
    
    # Print results
    for day_assignment in assignments:
        print(f"{day_assignment['day']} {day_assignment['date']}:")
        print(f"Hypercare: {day_assignment['hypercare']}")
        print(f"SIM: {day_assignment['sim']}")
        print(f"DOR: {day_assignment['dor']}")
        print(f"EOD: {day_assignment['eod']}")
        print(f"Coverage: {day_assignment['coverage']}")