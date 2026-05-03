"""Auto-generated code-distilled implementation for parse_schedules."""

import re
import json


def parse_schedules(text):
    try:
        # Extract the TASK section
        task_match = re.search(r'TASK:\s*You need to schedule a meeting for (.+?) for (half an hour|one hour|one and a half hours|two hours|(\d+) minutes?) between the work hours of (\d+:\d+) to (\d+:\d+) on (.*?)\.', text)
        if not task_match:
            return None

        # Parse participants
        participants_str = task_match.group(1)
        # Split by ", " and " and "
        participants_str = participants_str.replace(' and ', ', ')
        participants = [p.strip() for p in participants_str.split(',') if p.strip()]

        # Parse duration
        duration_str = task_match.group(2)
        if duration_str == 'half an hour':
            duration_minutes = 30
        elif duration_str == 'one hour':
            duration_minutes = 60
        elif duration_str == 'one and a half hours':
            duration_minutes = 90
        elif duration_str == 'two hours':
            duration_minutes = 120
        else:
            duration_minutes = int(task_match.group(3))

        # Working hours
        work_start = task_match.group(4)
        work_end = task_match.group(5)
        working_hours = [work_start, work_end]

        # Days
        days_str = task_match.group(6)
        days_str = days_str.replace('either ', '')
        days_str = days_str.replace(' or ', ', ')
        days_str = days_str.replace(' and ', ', ')
        days = [d.strip() for d in days_str.split(',') if d.strip()]

        # Preference
        preference = None
        if re.search(r'earliest\s+(possible\s+)?time', text, re.IGNORECASE):
            preference = "earliest"
        elif re.search(r'latest\s+(possible\s+)?time', text, re.IGNORECASE):
            preference = "latest"

        # Parse schedules for each participant
        schedules = {}
        for participant in participants:
            schedules[participant] = {}
            for day in days:
                schedules[participant][day] = []

        # Find each participant's schedule block
        # Pattern: "Name:\n  Monday: ... " or "Name has no meetings" etc.
        for participant in participants:
            # Look for the participant's schedule section
            # Pattern like: "Richard:\n  Monday: 9:00 - 9:30, 11:30 - 12:00"
            # or "Megan: No meetings"
            pat = re.escape(participant) + r'[:\s]*\n((?:[ \t]+.*\n?)*)'
            block_match = re.search(pat, text)
            if not block_match:
                # Try inline: "Name: No meetings" or single-line
                pat2 = re.escape(participant) + r':\s*No meetings'
                if re.search(pat2, text, re.IGNORECASE):
                    continue
                # Check for empty/no schedule
                continue

            block = block_match.group(1)
            for day in days:
                day_pat = day + r':\s*(.*?)(?:\n|$)'
                day_match = re.search(day_pat, block)
                if day_match:
                    day_content = day_match.group(1).strip()
                    if not day_content or day_content.lower() in ['no meetings', 'free', 'no meetings.']:
                        schedules[participant][day] = []
                    else:
                        # Extract time ranges: "9:00 - 9:30, 11:30 - 12:00"
                        time_ranges = re.findall(r'(\d{1,2}:\d{2})\s*[-–to]+\s*(\d{1,2}:\d{2})', day_content)
                        schedules[participant][day] = [list(tr) for tr in time_ranges]

        result = {
            "participants": participants,
            "duration_minutes": duration_minutes,
            "working_hours": working_hours,
            "days": days,
            "preference": preference,
            "schedules": schedules
        }

        return json.dumps(result)

    except Exception:
        return None
