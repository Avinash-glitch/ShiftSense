import json
import os
from datetime import datetime

FILE = "task_data.json"
TASKS = ["hypercare", "sim", "dor", "wims", "eod"]

def load_data():
    """Load task data from JSON file, or initialize if file does not exist."""
    if os.path.exists(FILE):
        with open(FILE, "r") as f:
            return json.load(f)
    return {"employees": {}, "date_assignments": {}, "task_cycles": {}}

def save_data(data):
    """Save task data to JSON file."""
    with open(FILE, "w") as f:
        json.dump(data, f, indent=4)

def add_employees_from_list(data, employee_list):
    """
    Ensure all employees in employee_list exist in the JSON.
    """
    all_employees = data["employees"]
    
    for e in employee_list:
        if e not in all_employees:
            all_employees[e] = {
                "history": {},  # {date: [tasks]}
                "total_counts": {t: 0 for t in TASKS},  # Lifetime counts
                "task_flags": {t: False for t in TASKS}  # Has done task this cycle
            }
    
    return data
def mark_employee_assigned(employee, task, date_str,sim_slot=None):
    """
    After choosing an employee for a task:
    - Record assignment for this date
    - Increment their lifetime task count
    - Set their flag to True for this task (they've done it this cycle)
    
    Args:
        employee (str): Employee login
        task (str): Task type (hypercare, sim, dor, wims, eod)
        date_str (str): Date in DD/MM/YYYY format
        sim_slot (str): For SIM tasks ONLY - the slot (morning, mid, night, midnight)
    """
    data = load_data()
    all_employees = data["employees"]
    date_assignments = data["date_assignments"]
    
    # Ensure employee exists
    if employee not in all_employees:
        all_employees[employee] = {
            "history": {},
            "total_counts": {t: 0 for t in TASKS},
            "task_flags": {t: False for t in TASKS}
        }
    
    date_str = str(date_str)
    
    # Initialize date if needed
    if date_str not in date_assignments:
        date_assignments[date_str] = {
            "hypercare": [],
            "sim": {"morning": None, "mid": None, "night": None, "midnight": None},  # ✅ DICT with slots
            "dor": None,
            "wims": [],  # List for multiple people
            "eod": None
        }
    
    # ✅ Record assignment for this date
    if task == "sim":
        # SIM MUST have a sim_slot
        if not sim_slot:
            print(f"❌ ERROR: sim_slot required for SIM task! Use sim_slot='morning'|'mid'|'night'|'midnight'")
            return False
        
        # Make sure sim is a dict
        if not isinstance(date_assignments[date_str]["sim"], dict):
            date_assignments[date_str]["sim"] = {"morning": None, "mid": None, "night": None, "midnight": None}
        
        # Assign to specific slot
        date_assignments[date_str]["sim"][sim_slot] = employee
        print(f"✅ Marked {employee} for SIM ({sim_slot}) on {date_str}")
        
    elif task == "wims":
        # WIMS is a list of multiple people
        if not isinstance(date_assignments[date_str]["wims"], list):
            date_assignments[date_str]["wims"] = []
        
        if employee not in date_assignments[date_str]["wims"]:
            date_assignments[date_str]["wims"].append(employee)
        print(f"✅ Marked {employee} for WIMS on {date_str}")

    elif task == "hypercare":
        # WIMS is a list of multiple people
        if not isinstance(date_assignments[date_str]["hypercare"], list):
            date_assignments[date_str]["hypercare"] = []
        
        if employee not in date_assignments[date_str]["hypercare"]:
            date_assignments[date_str]["hypercare"].append(employee)
        print(f"✅ Marked {employee} for hypercare on {date_str}")
    
    else:
        # Other tasks ( dor, eod) are single values
        date_assignments[date_str][task] = employee
        print(f"✅ Marked {employee} for {task} on {date_str}")
    
    # Update history
    if date_str not in all_employees[employee]["history"]:
        all_employees[employee]["history"][date_str] = []
    
    if task not in all_employees[employee]["history"][date_str]:
        all_employees[employee]["history"][date_str].append(task)
    
    # Update lifetime count (only once per task per date)
    if task not in all_employees[employee]["total_counts"]:
        all_employees[employee]["total_counts"][task] = 0
    all_employees[employee]["total_counts"][task] += 1
    
    # Set flag to True (employee has done this task in current cycle)
    all_employees[employee]["task_flags"][task] = True
    
    save_data(data)
    return True


def unmark_employee_assigned(employee, task, date_str, sim_slot=None):
    """
    Remove an employee's assignment for a specific task on a specific date.
    - Remove from history for that date
    - Decrement their lifetime task count
    - Remove from date_assignments
    - Reset task flag to False
    
    Args:
        employee (str): The employee's login name
        task (str): The task type (hypercare, sim, dor, wims, eod)
        date_str (str): Date in DD/MM/YYYY format
        sim_slot (str): For SIM tasks ONLY - the slot (morning, mid, night, midnight)
    """
    data = load_data()
    all_employees = data["employees"]
    date_assignments = data["date_assignments"]
    
    date_str = str(date_str)
    
    # Check if employee exists
    if employee not in all_employees:
        print(f"⚠️ Employee {employee} not found in records")
        return False
    
    # Remove from history
    if date_str in all_employees[employee]["history"]:
        if task in all_employees[employee]["history"][date_str]:
            all_employees[employee]["history"][date_str].remove(task)
            # If no tasks left for this date, remove the date entry
            if not all_employees[employee]["history"][date_str]:
                del all_employees[employee]["history"][date_str]
    
    # Decrement lifetime count
    if task in all_employees[employee]["total_counts"]:
        if all_employees[employee]["total_counts"][task] > 0:
            all_employees[employee]["total_counts"][task] -= 1
    
    # RESET the task flag to False
    all_employees[employee]["task_flags"][task] = False
    
    # Remove from date_assignments
    if date_str in date_assignments:
        if task == "sim":
            # SIM is a dict with slots
            if not sim_slot:
                print(f"❌ ERROR: sim_slot required to unmark SIM!")
                return False
            
            if isinstance(date_assignments[date_str]["sim"], dict):
                if date_assignments[date_str]["sim"].get(sim_slot) == employee:
                    date_assignments[date_str]["sim"][sim_slot] = None
            print(f"✅ Unmarked {employee} from SIM ({sim_slot}) on {date_str}")
            
        elif task == "wims":
            # WIMS is a list
            if isinstance(date_assignments[date_str]["wims"], list):
                if employee in date_assignments[date_str]["wims"]:
                    date_assignments[date_str]["wims"].remove(employee)
            print(f"✅ Unmarked {employee} from WIMS on {date_str}")
        elif task == "hypercare":
            # WIMS is a list
            if isinstance(date_assignments[date_str]["hypercare"], list):
                if employee in date_assignments[date_str]["hypercare"]:
                    date_assignments[date_str]["hypercare"].remove(employee)
            print(f"✅ Unmarked {employee} from hypercare on {date_str}")
            
        else:
            # Other tasks are single values
            if date_assignments[date_str].get(task) == employee:
                date_assignments[date_str][task] = None
            print(f"✅ Unmarked {employee} from {task} on {date_str}")
    
    save_data(data)
    print(f"✅ Unmarked {employee} from {task} on {date_str}")
    return True


# ============================================================================
# HOW TO USE IN daily_assignment.py:
# ============================================================================

# Example 1: Mark a hypercare assignment
# mark_employee_assigned("mariebak", "hypercare", "21/12/2025")

# Example 2: Mark a SIM assignment (with slot)
# mark_employee_assigned("poshaln", "sim", "21/12/2025", sim_slot="morning")
# mark_employee_assigned("chosen_mid", "sim", "21/12/2025", sim_slot="mid")
# mark_employee_assigned("chosen_night", "sim", "21/12/2025", sim_slot="night")

# Example 3: Mark a WIMS assignment (multiple people)
# mark_employee_assigned("sajidnaz", "wims", "21/12/2025")
# mark_employee_assigned("someone_else", "wims", "21/12/2025")

# Example 4: Mark other tasks
# mark_employee_assigned("dor_person", "dor", "21/12/2025")
# mark_employee_assigned("eod_person", "eod", "21/12/2025")

# Example 5: Unmark a SIM assignment
# unmark_employee_assigned("old_mid_sim", "sim", "21/12/2025", sim_slot="mid")

# Example 6: Unmark a WIMS assignment
# unmark_employee_assigned("sajidnaz", "wims", "21/12/2025")
def clear_assignments_for_week(week_dates):
    """
    Clear assignments ONLY for the dates in the given week.
    This allows regenerating the same week without clearing other weeks' data.
    Resets employee flags and counts for those specific dates only.
    
    Args:
        week_dates (list): List of date strings in DD/MM/YYYY format
    """
    data = load_data()
    all_employees = data["employees"]
    date_assignments = data["date_assignments"]
    
    week_dates_str = [str(d) for d in week_dates]
    
    # For each date in this week, clear assignments and reset employee flags
    for date_str in week_dates_str:
        if date_str in date_assignments:
            # Get all employees assigned to this date
            assignments = date_assignments[date_str]
            
            for task, employee in assignments.items():
                if employee:
                    # Remove from history
                    if date_str in all_employees[employee]["history"]:
                        if task in all_employees[employee]["history"][date_str]:
                            all_employees[employee]["history"][date_str].remove(task)
                    
                    # Decrement their count
                    if all_employees[employee]["total_counts"][task] > 0:
                        all_employees[employee]["total_counts"][task] -= 1
                    
                    # Reset their flag
                    all_employees[employee]["task_flags"][task] = False
            
            # Clear this date's assignments
            del date_assignments[date_str]
    
    save_data(data)
    print(f"✅ Cleared assignments for week: {week_dates_str}")

def get_eligible_employees(available_today, task, date_str):
    """
    Returns a list of employees available today for a specific task.
    
    Logic:
    1. Filter to employees who haven't done this task YET (flag = False)
    2. If all have done it (all flags = True), reset flags and use all
    3. Sort by lifetime count (least assigned first)
    
    Args:
        available_today: List of employees working today
        task: The task to assign (hypercare, sim, dor, wims, eod)
        date_str: Date in DD/MM/YYYY format
    
    Returns:
        list: Employees sorted by assignment count (least assigned first)
    """
    data = load_data()
    data = add_employees_from_list(data, available_today)
    
    all_employees = data["employees"]
    
    # Get employees who haven't done this task yet (flag = False)
    not_done_yet = [
        e for e in available_today
        if not all_employees[e]["task_flags"].get(task, True)
    ]
    
    # If everyone has done it (all flags = True), reset all flags for this task
    if not not_done_yet:
        for emp in available_today:
            all_employees[emp]["task_flags"][task] = False
        # Now everyone is available
        not_done_yet = available_today[:]
    
    # Sort by lifetime count (least assigned first)
    not_done_yet.sort(
        key=lambda e: all_employees[e]["total_counts"].get(task, 0)
    )
    
    save_data(data)
    return not_done_yet

def get_date_assignment(date_str, task):
    """
    Get who was assigned to a specific task on a specific date.
    
    Args:
        date_str (str): Date in DD/MM/YYYY format
        task (str): Task type (hypercare, sim, dor, wims, eod)
    
    Returns:
        str or None: Employee login name or None if not assigned
    """
    data = load_data()
    date_assignments = data["date_assignments"]
    
    date_str = str(date_str)
    if date_str in date_assignments:
        return date_assignments[date_str].get(task, None)
    return None

def clear_date_assignments(date_str):
    """
    Clear all assignments for a specific date.
    Used when regenerating assignments for the same date.
    
    Args:
        date_str (str): Date in DD/MM/YYYY format
    """
    data = load_data()
    date_str = str(date_str)
    
    if date_str in data["date_assignments"]:
        del data["date_assignments"][date_str]
    
    save_data(data)
    print(f"✅ Cleared all assignments for {date_str}")

def reset_task_cycle(task):
    """
    Manually reset flags for a specific task across all employees.
    Used to allow employees to be assigned again in a new cycle.
    
    Args:
        task (str): Task type (hypercare, sim, dor, wims, eod)
    """
    data = load_data()
    all_employees = data["employees"]
    
    for emp in all_employees:
        all_employees[emp]["task_flags"][task] = False
    
    save_data(data)
    print(f"✅ Reset cycle flags for task: {task}")

def get_assignment_stats(task=None):
    """
    Get statistics about task assignments.
    If task is specified, returns counts for that task.
    Otherwise returns all counts.
    
    Args:
        task (str, optional): Specific task to get stats for
    
    Returns:
        dict: Employee assignment statistics
    """
    data = load_data()
    all_employees = data["employees"]
    
    stats = {}
    for emp, info in all_employees.items():
        if task:
            stats[emp] = info["total_counts"].get(task, 0)
        else:
            stats[emp] = info["total_counts"]
    
    return stats

def clear_all_task_data():
    """
    Completely clear all task data from task_data.json
    Resets the entire assignment history and cycle tracking.
    
    WARNING: This action cannot be undone!
    
    Returns:
        bool: True if successful
    """
    data = {
        "employees": {},
        "date_assignments": {},
        "task_cycles": {}
    }
    
    with open(FILE, "w") as f:
        json.dump(data, f, indent=4)
    
    print("✅ All task data cleared successfully!")
    return True

def get_employee_history(employee):
    """
    Get the full assignment history for a specific employee.
    
    Args:
        employee (str): Employee login name
    
    Returns:
        dict: Employee's history and statistics
    """
    data = load_data()
    all_employees = data["employees"]
    
    if employee not in all_employees:
        return None
    
    return all_employees[employee]

def get_week_assignments(week_dates):
    """
    Get all assignments for a specific week.
    
    Args:
        week_dates (list): List of date strings in DD/MM/YYYY format
    
    Returns:
        dict: All assignments for the week
    """
    data = load_data()
    date_assignments = data["date_assignments"]
    
    week_assignments = {}
    for date_str in week_dates:
        date_str = str(date_str)
        if date_str in date_assignments:
            week_assignments[date_str] = date_assignments[date_str]
    
    return week_assignments

def export_task_data(filename="task_data_backup.json"):
    """
    Export task data to a backup file.
    
    Args:
        filename (str): Name of backup file to create
    
    Returns:
        bool: True if successful
    """
    try:
        data = load_data()
        with open(filename, "w") as f:
            json.dump(data, f, indent=4)
        print(f"✅ Task data exported to {filename}")
        return True
    except Exception as e:
        print(f"❌ Error exporting task data: {str(e)}")
        return False

def import_task_data(filename="task_data_backup.json"):
    """
    Import task data from a backup file.
    WARNING: This will overwrite current task data!
    
    Args:
        filename (str): Name of backup file to import
    
    Returns:
        bool: True if successful
    """
    try:
        if not os.path.exists(filename):
            print(f"❌ Backup file not found: {filename}")
            return False
        
        with open(filename, "r") as f:
            data = json.load(f)
        
        with open(FILE, "w") as f:
            json.dump(data, f, indent=4)
        
        print(f"✅ Task data imported from {filename}")
        return True
    except Exception as e:
        print(f"❌ Error importing task data: {str(e)}")
        return False