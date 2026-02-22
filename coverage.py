import re

def parse_time_to_minutes(time_str):
    """Convert time string like '06:30' or '23:30' to minutes since midnight"""
    time_str = time_str.strip().replace('\xa0', '')  # Remove non-breaking spaces
    match = re.match(r"(\d{1,2}):(\d{2})", time_str)
    if match:
        hours = int(match.group(1))
        minutes = int(match.group(2))
        return hours * 60 + minutes
    return None

def minutes_to_str(m):
    """Convert minutes to HH:MM format"""
    m = m % (24 * 60)
    h = m // 60
    mi = m % 60
    return f"{h:02d}:{mi:02d}"


def calculate_coverage_from_shifts(all_shift_times, test=False):
    """
    Calculate coverage string and hours breakdown from a list of shift times.
    
    Args:
        all_shift_times (list): List of shift time strings like ["06:30-15:00", "23:30-08:30"]
        test (bool): If True, enables print statements for debugging
    
    Returns:
        tuple: (coverage_str, hours_breakdown)
            - coverage_str (str): Coverage window like "06:30-23:00" or "No Coverage"
            - hours_breakdown (dict): {"current_day": hours, "next_day": hours}
    """
    coverage_str = "No Coverage"
    hours_breakdown = {"current_day": 0, "next_day": 0}
    
    if not all_shift_times:
        return coverage_str, hours_breakdown
    
    earliest_start = None
    latest_end = None
    
    if test:
        print(f"Processing shift times:")
    
    for shift_time in all_shift_times:
        # Parse shift time like "06:30-15:00" or "23:30-8:30"
        shift_time = shift_time.replace('\xa0', ' ').strip()
        parts = re.split(r'[-–]', shift_time)  # Handle both - and –
        
        if test:
            print(f"  Shift: {shift_time}")
        
        if len(parts) == 2:
            start_str = parts[0].strip()
            end_str = parts[1].strip()
            
            start_mins = parse_time_to_minutes(start_str)
            end_mins = parse_time_to_minutes(end_str)
            
            if start_mins is not None and end_mins is not None:
                # Handle overnight shifts (end < start means it crosses midnight)
                if end_mins <= parse_time_to_minutes("8:30"):  # 8:30 AM threshold to avoid misinterpretation
                    if test:
                        print(f"Overnight shift detected (end < start)")
                    # Add 24 hours to end time for comparison
                    end_mins += 24 * 60
                    
                    if test:
                        print(f"Adjusted end time: {end_mins} minutes")
                        
                if earliest_start is None or start_mins < earliest_start:
                    earliest_start = start_mins
                    if test:
                        print(f"New earliest start: {earliest_start} minutes")
                
                if latest_end is None or end_mins > latest_end:
                    latest_end = end_mins
                    if test:
                        print(f"New latest end: {latest_end} minutes")
    
    if earliest_start is not None and latest_end is not None:
        # Convert back to time strings
        start_str = minutes_to_str(earliest_start)
        end_str = minutes_to_str(latest_end)
        
        coverage_str = f"{start_str}-{end_str}"
        
        if test:
            print(f"Coverage calculation:")
            print(f"  Earliest start: {earliest_start} minutes ({start_str})")
            print(f"  Latest end: {latest_end} minutes ({end_str})")
            print(f"  Coverage string: {coverage_str}")
        
        # Calculate hours split between days
        midnight = 24 * 60  # Midnight in minutes
        
        if latest_end <= midnight:
            # No overnight coverage
            hours_breakdown["current_day"] = (latest_end - earliest_start) / 60
            
            hours_breakdown["next_day"] = 0
            if test:
                print(f"  No overnight coverage")
                print(f"  Current day hours: {hours_breakdown['current_day']:.2f}")
        else:
            # Coverage extends past midnight
            # Current day: from start to midnight
            hours_breakdown["current_day"] = (midnight - earliest_start) / 60
            # Next day: from midnight to end
            hours_breakdown["next_day"] = (latest_end - midnight) / 60
            if test:
                print(f"  Coverage extends past midnight")
                print(f"  Current day hours: {hours_breakdown['current_day']:.2f}")
                print(f"  Next day hours: {hours_breakdown['next_day']:.2f}")
    
    return coverage_str, hours_breakdown