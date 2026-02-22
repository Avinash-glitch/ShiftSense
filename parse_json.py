

import json
import re
def get_shift_groups_for_day(schedule_data, day):
    morning_times = ["06:30-15:00"]
    morning_fallback_times = ["08:00-16:10", "09:30-18:00", "10:30-18:00"]
    mid_times = ["10:30-18:00", "08:00-16:10", "09:30-18:00", "11:30-20:00", "13:00-21:10"]
    night_times = ["14:30-23:00"]
    night_fallback_times = ["23:30-08:30"]
    midnight_times = ["23:30-08:30"]

    morning = []
    mid = []
    morning_fallback = []
    night_fallback = []
    night = []
    midnight = []

    morning_shifts = []
    mid_shifts=[]
    midnight_shifts = []
    night_shifts = []

    for login, days in schedule_data.items():
        # Fix for trailing spaces in day keys
        shift = None
        for k in days.keys():
            if k.strip() == day.strip():
                shift = days[k].strip()
                break
        if not shift:
            continue

        if shift in morning_times:
            morning.append(login)
            morning_shifts.append(shift)
        
        elif shift in mid_times:
            mid.append(login)
            mid_shifts.append(shift)

        elif shift in night_times:
            night.append(login)
            night_shifts.append(shift)

        
        elif shift in midnight_times:
            midnight.append(login)
            midnight_shifts.append(shift)
            pass

    for login, days in schedule_data.items():
        shift = None
        for k in days.keys():
            if k.strip() == day.strip():
                shift = days[k].strip()
                break
        if not shift:
            continue
        if shift in morning_fallback_times:
            morning_fallback.append(login)
            pass
        elif shift in night_fallback_times:
            night_fallback.append(login)
            pass
        else:
            continue
    

    def get_start_time(shifts):
        times = []
        for s in shifts:
            match = re.match(r"(\d{1,2}):(\d{2})-(\d{1,2}):(\d{2})", s)
            if match:
                start = int(match.group(1)) * 60 + int(match.group(2))
                times.append(start)
        return min(times) if times else None

    def get_end_time(shifts):
        times = []
        for s in shifts:
            match = re.match(r"(\d{1,2}):(\d{2})-(\d{1,2}):(\d{2})", s)
            if match:
                end = int(match.group(3)) * 60 + int(match.group(4))
                times.append(end)
        return max(times) if times else None

    def minutes_to_str(m):
        h = m // 60
        mi = m % 60
        return f"{h:02d}:{mi:02d}"

    # Coverage calculation
    start_time = get_start_time(morning_shifts)
    # Prefer midnight shifts for end time, else night shifts
    if midnight_shifts: end_time = get_end_time(midnight_shifts) 
    else:
        if night_shifts: end_time=get_end_time(night_shifts)

        else: end_time=get_end_time(mid_shifts)

    coverage = None
    if start_time is not None and end_time is not None:
        coverage = {
            "start": minutes_to_str(start_time),
            "end": minutes_to_str(end_time)
        }

    return {
        "morning": morning,
        "mid": mid,
        "morning_fallback": morning_fallback,
        "night": night,
        "night_fallback": night_fallback,
        "midnight": midnight,
        "coverage": coverage
    }
# # Example usage:
# with open(r"C:\Users\avikann\rota\schedule.json") as f:
#     schedule_data = json.load(f)
# result = get_shift_groups_for_day(schedule_data, "Sat")
# print(result)