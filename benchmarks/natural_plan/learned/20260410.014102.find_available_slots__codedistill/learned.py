"""Auto-generated code-distilled implementation for find_available_slots."""

import json
from datetime import datetime, timedelta

def find_available_slots(prompt: str, schedules_json: str) -> str:
    """
    Find available meeting slots for all participants.
    
    Args:
        prompt: The task description (not directly used for logic)
        schedules_json: JSON string containing participants, duration, working hours, days, and schedules
    
    Returns:
        JSON string with list of available slots, or None if cannot be handled
    """
    try:
        data = json.loads(schedules_json)
        
        participants = data.get("participants", [])
        duration_minutes = data.get("duration_minutes", 30)
        working_hours = data.get("working_hours", ["9:00", "17:00"])
        days = data.get("days", [])
        schedules = data.get("schedules", {})
        
        if not participants or not days or not working_hours:
            return None
        
        # Parse working hours
        work_start = time_to_minutes(working_hours[0])
        work_end = time_to_minutes(working_hours[1])
        
        available_slots = []
        
        for day in days:
            # Get free intervals for each participant on this day
            free_intervals_by_person = {}
            
            for participant in participants:
                busy_times = schedules.get(participant, {}).get(day, [])
                free_intervals = get_free_intervals(busy_times, work_start, work_end)
                free_intervals_by_person[participant] = free_intervals
            
            # Find intersection of all free intervals
            common_free = intersect_intervals(free_intervals_by_person, participants)
            
            # Split into slots of required duration
            for start, end in common_free:
                current = start
                while current + duration_minutes <= end:
                    end_time = current + duration_minutes
                    available_slots.append({
                        "day": day,
                        "start": minutes_to_time(current),
                        "end": minutes_to_time(end_time)
                    })
                    current += duration_minutes
        
        return json.dumps(available_slots)
    
    except (json.JSONDecodeError, KeyError, ValueError):
        return None


def time_to_minutes(time_str: str) -> int:
    """Convert time string like '9:00' to minutes since midnight."""
    parts = time_str.split(':')
    hours = int(parts[0])
    minutes = int(parts[1])
    return hours * 60 + minutes


def minutes_to_time(minutes: int) -> str:
    """Convert minutes since midnight to time string like '09:00'."""
    hours = minutes // 60
    mins = minutes % 60
    return f"{hours:02d}:{mins:02d}"


def get_free_intervals(busy_times: list, work_start: int, work_end: int) -> list:
    """
    Get free intervals by subtracting busy times from working hours.
    
    Args:
        busy_times: List of [start, end] time strings
        work_start: Working hour start in minutes
        work_end: Working hour end in minutes
    
    Returns:
        List of [start, end] free intervals in minutes
    """
    if not busy_times:
        return [[work_start, work_end]]
    
    # Convert busy times to minutes and sort
    busy_intervals = []
    for busy in busy_times:
        start = time_to_minutes(busy[0])
        end = time_to_minutes(busy[1])
        busy_intervals.append([start, end])
    
    busy_intervals.sort()
    
    # Merge overlapping busy intervals
    merged = []
    for start, end in busy_intervals:
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    
    # Find free intervals
    free = []
    current = work_start
    
    for start, end in merged:
        if current < start:
            free.append([current, start])
        current = max(current, end)
    
    if current < work_end:
        free.append([current, work_end])
    
    return free


def intersect_intervals(free_by_person: dict, participants: list) -> list:
    """
    Find intersection of free intervals across all participants.
    
    Args:
        free_by_person: Dict mapping participant name to list of free intervals
        participants: List of participant names
    
    Returns:
        List of common free intervals
    """
    if not participants:
        return []
    
    # Start with first participant's free intervals
    common = free_by_person.get(participants[0], [])
    
    # Intersect with each other participant
    for participant in participants[1:]:
        person_free = free_by_person.get(participant, [])
        common = intersect_two_interval_lists(common, person_free)
    
    return common


def intersect_two_interval_lists(intervals1: list, intervals2: list) -> list:
    """Find intersection of two lists of intervals."""
    result = []
    
    for start1, end1 in intervals1:
        for start2, end2 in intervals2:
            # Find overlap
            overlap_start = max(start1, start2)
            overlap_end = min(end1, end2)
            
            if overlap_start < overlap_end:
                result.append([overlap_start, overlap_end])
    
    return result
