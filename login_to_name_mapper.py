import pandas as pd

def get_login_to_name_mapping(df):
    """
    Extract login to first name mapping from holiday tracker.
    
    Assumes:
    - Row 0: Dates
    - Row 1: Day names
    - Row 2+: Data with Login in column 0, Name in column 1
    
    Args:
        df: Holiday tracker DataFrame
    
    Returns:
        dict: {login: first_name} mapping
    """
    login_to_name = {}
    
    try:
        # Get login column (usually column 0)
        logins = df.iloc[2:, 0].dropna()  # Start from row 2 (skip header)
        
        # Get name column (usually column 1)
        names = df.iloc[2:, 1].dropna()
        
        # Create mapping with first name only
        for login, name in zip(logins, names):
            login_str = str(login).strip()
            name_str = str(name).strip()
            
            if login_str and name_str:
                # ✅ Extract first name only
                first_name = name_str.split()[0]
                login_to_name[login_str] = first_name
        
        print(f"✅ Extracted {len(login_to_name)} login-name mappings")
        return login_to_name
        
    except Exception as e:
        print(f"⚠️ Error extracting names: {str(e)}")
        return {}


def convert_login_to_name(login, login_to_name_dict):
    """
    Convert login to name using mapping.
    Falls back to login if name not found.
    
    Args:
        login (str): Employee login
        login_to_name_dict (dict): Mapping of login to name
    
    Returns:
        str: Employee name or login if not found
    """
    if not login or login == "NA" or login == "No DOR":
        return login
    
    login_str = str(login).strip()
    return login_to_name_dict.get(login_str, login_str)


def convert_rota_logins_to_names(daily_assignments, login_to_name_dict):
    """
    Convert all logins in rota to names.
    
    Args:
        daily_assignments (list): List of day assignments
        login_to_name_dict (dict): Mapping of login to name
    
    Returns:
        list: Updated assignments with names instead of logins
    """
    for day_assignment in daily_assignments:
        
        # Convert hypercare
        if day_assignment["hypercare"]:
            day_assignment["hypercare"] = [
                convert_login_to_name(login, login_to_name_dict) 
                for login in day_assignment["hypercare"]
            ]
        
        # Convert SIM slots
        if day_assignment["sim"]:
            for slot in day_assignment["sim"]:
                day_assignment["sim"][slot] = convert_login_to_name(
                    day_assignment["sim"][slot], 
                    login_to_name_dict
                )
        
        # Convert DOR
        if day_assignment["dor"]:
            day_assignment["dor"] = convert_login_to_name(
                day_assignment["dor"], 
                login_to_name_dict
            )
        
        # Convert EOD
        if day_assignment["eod"]:
            day_assignment["eod"] = convert_login_to_name(
                day_assignment["eod"], 
                login_to_name_dict
            )
        
        # Convert WIMS
        if day_assignment["wims"]:
            day_assignment["wims"] = [
                convert_login_to_name(login, login_to_name_dict) 
                for login in day_assignment["wims"]
            ]
    
    return daily_assignments


# ============================================================================
# HOW TO USE IN streamlit_new.py:
# ============================================================================

"""
After generating assignments, add this:

# Get name mapping from holiday tracker
login_to_name = get_login_to_name_mapping(df)

# Convert all logins to names
assignments_with_names = convert_rota_logins_to_names(
    st.session_state.generated_rota, 
    login_to_name
)

# Now display/download with names instead of logins
"""

# ============================================================================
# EXAMPLE USAGE:
# ============================================================================

if __name__ == "__main__":
    # Load holiday tracker
    df = pd.read_excel(r'C:\Users\avikann\Documents\holiday_tracker.xlsx')
    
    # Get mapping
    mapping = get_login_to_name_mapping(df)
    print(mapping)
    
    # Example assignments
    sample_assignments = [
        {
            "date": "21/12/2025",
            "day": "Sun",
            "hypercare": ["wpatchan"],
            "sim": {"morning": "poshaln", "mid": "robjlew", "night": "darshbs"},
            "dor": None,
            "eod": "maneadf",
            "wims": ["sajidnaz", "hjoiser"]
        }
    ]
    
    # Convert to names
    converted = convert_rota_logins_to_names(sample_assignments, mapping)
    print(converted)