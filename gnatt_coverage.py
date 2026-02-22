from datetime import datetime, timedelta

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

def merge_overlapping_intervals(intervals):
    """
    Merge overlapping time intervals into continuous blocks
    intervals: list of (start_datetime, end_datetime) tuples
    Returns: list of merged (start_datetime, end_datetime) tuples
    """
    if not intervals:
        return []

    # Sort by start time
    sorted_intervals = sorted(intervals, key=lambda x: x)
    merged = [sorted_intervals]

    for current_start, current_end in sorted_intervals[1:]:
        last_start, last_end = merged[-1]

        # If current interval overlaps or touches the last one, merge them
        if current_start <= last_end:
            merged[-1] = (last_start, max(last_end, current_end))
        else:
            # No overlap, add as separate block
            merged.append((current_start, current_end))

    return merged

def generate_coverage_gantt(date_str, day_of_week, task_data, schedule_data):
    """
    Generate Gantt chart showing ACTUAL coverage blocks
    Merges overlapping shifts into continuous bars, shows gaps as separate blocks
    """
    # Convert date to base_date format
    date_obj = datetime.strptime(date_str, '%d/%m/%Y')
    base_date = date_obj.strftime('%Y-%m-%d')

    # Get assignments for this date
    assignments = task_data['date_assignments'].get(date_str, {})

    # Build Gantt chart configuration
    gantt_config = {
        "chart": {"type": "xrange"},
        "title": {"text": f"Task Coverage - {date_obj.strftime('%A, %B %d, %Y')}"},
        "subtitle": {"text": "Actual coverage blocks (merged overlapping shifts)"},
        "xAxis": {
            "type": "datetime",
            "labels": {"format": "{value:%H:%M}"},
            "min": f"{base_date}T00:00:00",
            "max": f"{base_date}T23:59:59"
        },
        "yAxis": {
            "title": {"text": "Tasks"},
            "categories": ["HYPERCARE", "SIM", "WIMS"],
            "reversed": True
        },
        "legend": {"enabled": True},
        "tooltip": {
            "headerFormat": "<b>{point.yCategory}</b><br/>",
            "pointFormat": "Covered: {point.x:%H:%M} - {point.x2:%H:%M}<br/>Duration: {point.duration}"
        },
        "plotOptions": {
            "xrange": {
                "borderRadius": 0,
                "borderWidth": 0,
                "dataLabels": {
                    "enabled": True,
                    "format": "{point.duration}"
                }
            }
        },
        "series": []
    }

    # Task colors
    task_colors = {
        'hypercare': '#E74C3C',
        'sim': '#3498DB',
        'wims': '#2ECC71'
    }

    # Task map for y-axis
    task_map = {'hypercare': 0, 'sim': 1, 'wims': 2}

    # Process each task type
    tasks_to_show = ['hypercare', 'sim', 'wims']

    for task_type in tasks_to_show:
        # Collect ALL coverage intervals for this task
        coverage_intervals = []

        # Get assigned employee(s) for this task
        assigned = assignments.get(task_type)

        # Handle different assignment formats
        employees_to_check = []

        if isinstance(assigned, list):
            # Multiple employees (like hypercare on weekdays)
            employees_to_check = assigned
        elif isinstance(assigned, dict):
            # SIM slots (AM, PM, Night)
            employees_to_check = [emp for emp in assigned.values() if emp]
        elif isinstance(assigned, str):
            # Single employee
            employees_to_check = [assigned]

        # Collect shift times for all assigned employees
        for employee in employees_to_check:
            if employee and employee in schedule_data:
                shift_time = schedule_data[employee].get(day_of_week)

                if shift_time:
                    try:
                        start_dt, end_dt = parse_shift_time(shift_time, base_date)
                        start_time = datetime.fromisoformat(start_dt)
                        end_time = datetime.fromisoformat(end_dt)
                        coverage_intervals.append((start_time, end_time))
                    except:
                        pass

        # Merge overlapping intervals
        merged_intervals = merge_overlapping_intervals(coverage_intervals)

        # Create data blocks for each merged interval
        data_blocks = []
        for start_time, end_time in merged_intervals:
            duration_hours = (end_time - start_time).total_seconds() / 3600

            data_blocks.append({
                "x": start_time.isoformat(),
                "x2": end_time.isoformat(),
                "y": task_map[task_type],
                "duration": f"{duration_hours:.1f}h"
            })

        # Add series for this task if there's coverage
        if data_blocks:
            gantt_config["series"].append({
                "name": task_type.upper(),
                "color": task_colors.get(task_type, '#95A5A6'),
                "data": data_blocks
            })

    return gantt_config

