
import pandas as pd

# Load the file
# df = pd.read_excel(r"C:\Users\avikann\Documents\holiday_tracker.xlsx")
# df = pd.read_csv(r"C:\Users\avikann\Documents\holiday_tracker.csv")
# print(df.head(5))
# --- STEP 1: Identify the row that contains dates (Sunday, Monday, ...) ---


def check_if_person_working_today(date,login,df):
    working_code = ["S1", "S2", "S3", "S4", "wfh", "Wfh", "WFH"]
    date_row = df.iloc[1]   # The first row contains dates

    # Extract the mapping: column_name → actual date
    date_columns = {
        col: date_row[col]
        for col in df.columns
        if isinstance(date_row[col], pd.Timestamp)
    }

    # --- STEP 2: Extract login-name pairs ---
    people_df = df.iloc[2:,:2]   # Data starts from row index 2


    shift_schedule_df = df  # Shift schedule starts from row index 2 and column index 2
    # shift_schedule_df = shift_schedule_df.rename(columns={
    #     "Unnamed: 0": "Login",
    #     "Unnamed: 1": "Name"
    # })

    dates_raw = pd.to_datetime(df.iloc[0], errors="coerce",dayfirst=True)  # Dates are in the second row and columns 7 
    # date formatting 
    def format_date(d):
        if pd.isna(d):
            return None
        return d.strftime("%d/%m/%Y")

    dates_df = dates_raw.apply(format_date)
    shift_schedule_df.iloc[0]=dates_df
        
    # Find the column index for the given date in the 0th row
    date_row = shift_schedule_df.iloc[0]
    col_idx = None
    for idx, val in enumerate(date_row):
        if val == date:
            col_idx = idx
            break
    if col_idx is None:
        return "Date not found"

    # Find the row index for the given login
    login_row_idx = None
    # print(shift_schedule_df.head(5))
    people_row = people_df.iloc[:, 0]
    for idx, val in enumerate(people_row):
        if val == login:
            login_row_idx = idx
            break
    if login_row_idx is None:
        return "login not found"
    
    code = shift_schedule_df.iloc[login_row_idx+2, col_idx]
    if code in working_code:
        # print("Working")
        return "Working"
        
    else:
        return "Not Working"
        # print("Not Working")



# print(check_if_person_working_today("22/12/2025", "avikann"))
