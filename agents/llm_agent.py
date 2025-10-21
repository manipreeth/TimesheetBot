from langchain_ollama import OllamaLLM
from langgraph.graph import StateGraph
from datetime import datetime
import json

llm = OllamaLLM(model="llama3", base_url="http://localhost:11434");

def extract_timesheet_data(state):
    print("\n[STEP 1] Extracting timesheet data from user input...")
    print("-------------------------------------------------")
    
    text = state["user_text"]

    # Get current datetime
    now = datetime.now()
    current_day = now.strftime("%A")        # e.g., "Sunday"
    current_date = now.strftime("%m/%d/%Y") # e.g., "08/24/2025"
    current_time = now.strftime("%H:%M")    # e.g., "13:45"

    prompt = f"""
    You are an assistant for timesheet submission.

    Current system context:
    - Today is {current_day}, {current_date}.
    - Current time is {current_time}.

    Task:
    - Interpret the following user instruction as a timesheet submission.
    - Working days are always Monday to Friday (unless the user specifies a different range).
    - If the user says "Monday to Friday", expand it to include each day with correct dates for the intended week (relative to today).
    - If the user provides a date range (e.g., "08/12 to 08/16"), use that exact range instead of assuming current week.
    - Extract project names, activities, and hours worked per day.
    - If multiple projects are logged on the same day, represent them as multiple entries in an array.
    - If the user mentions "leave", record the entry as {{ "date": "MM/DD", "day": "Day", "hours": int }} (no "activity" field) under "NAW - VDSI Absence".
    - Always include the application code if the user provides it.
    - If the user specifyes hashtag it is # not the text "hashtag".
    - Example: If user say XY hash tag 1234 ABC DEF, interpret it as "XY#1234 ABC DEF".
    - Match activities to the closest valid option from the list below. If no close match or unwanted text match, use "Training Conference"  .
    - Do not include any explanations, notes, or extra text outside the JSON.
    - Need only the JSON as output.

    Activity Options (must map to one of these, or closest match):
    - {{"key":"Planning, Tracking & Mgmt","value":"1"}}
    - {{"key":"Requirements Definition & General Design","value":"2"}}
    - {{"key":"Detailed Design","value":"3"}}
    - {{"key":"Build","value":"4"}}
    - {{"key":"Functionality Testing & Install - Excludes UAT","value":"5"}}
    - {{"key":"Data Conversion, Data Migration & Table Entry","value":"6"}}
    - {{"key":"Application Maintenance Support","value":"7"}}
    - {{"key":"Infrastructure Maintenance Support","value":"8"}}
    - {{"key":"End User Maintenance Support","value":"9"}}
    - {{"key":"Implementation - Purchased Hardware","value":"10"}}
    - {{"key":"Application Production Support","value":"11"}}
    - {{"key":"Infrastructure Production Support","value":"12"}}
    - {{"key":"End User Production Support","value":"13"}}
    - {{"key":"Administration","value":"14"}}
    - {{"key":"Training Conference","value":"15"}}
    - {{"key":"Travel","value":"16"}}
    - {{"key":"Employee Down Time","value":"17"}}


    Output JSON strictly in this format:

    {{
        "application_code": "string",
        "monday": [
            {{ "date": "MM/DD", "day": "Mon", "project": "Project Name", "hours": int, "activity": "int", "activityLabel":"string" }}
        ],
        "tuesday": [],
        "wednesday": [],
        "thursday": [],
        "friday": [],
        "NAW - VDSI Absence": [
            {{ "date": "MM/DD", "day": "Day", "hours": int }}
        ]
    }}

    Example Output:
    {{
        "application_code": "19572",
        "monday": [
            {{
                "date": "09/01",
                "day": "Mon",
                "project": "BC#452 Data Synchronisation",
                "hours": 8,
                "activity": "4",
                "activityLabel":"Build"
            }}
        ],
        "tuesday": [
            {{
                "date": "09/02",
                "day": "Tue",
                "project": "BC#736 Edge Automation",
                "hours": 8,
                "activity": "5",
                "activityLabel":"Functionality Testing & Install - Excludes UAT"
            }}
        ],
        "wednesday": [
                {{
                    "date": "09/03",
                    "day": "Wed",
                    "project": "AZ#0912 Site Builder",
                    "hours": 8,
                    "activity": "1"
                    "activityLabel":"Planning, Tracking & Mgmt"
                }}
            ],
        "thursday": [
            {{
                "date": "09/04",
                "day": "Thu",
                "project": "CR#76311 Circuit Screen",
                "hours": 8,
                "activity": "9",
                "activityLabel":"End User Maintenance Support"
            }}
        ],
        "friday": [
            {{
                "date": "09/05",
                "day": "Fri",
                "project": "BC#8922 Equipment Built",
                "hours": 4,
                "activity": "11",
                "activityLabel":"Application Production Support"
            }}
        ],
        "NAW - VDSI Absence": [{{ "date": "09/05", "day": "Fri", "hours": 4 }}]
    }}



    Rules:
    - Each weekday key (monday to friday) must be included, even if no work is reported (use [] for that day).
    - Dates must always match the user’s specified range, or default to current week if unspecified.
    - If multiple projects are logged on a single day, keep them in the same day’s array.
    - "activity" must always be included for working project entries, but omitted for leave entries.
    - "NAW - VDSI Absence" must only list leave days (full or partial)(4 or 8 hours per day).
    - Hours must always be integers.
    - Do not invent projects, activities, or codes; only use what the user provides. If user specifies a custom activity, match it to the closest valid activity option.
    - If user gives relative terms like "today", "yesterday", "last week", or "next week", resolve them into exact dates using the system context.


    User input: {text}
    """
    
    print("Sending request to LLM... Please wait.")
    response = llm.invoke(prompt)

    print("LLM Response:", response)

    # Try parsing JSON safely
    try:
        parsed = json.loads(response)
        print("[SUCCESS] JSON parsed successfully!")
        state["timesheet_data"] = parsed
    except Exception as e:
        print("[WARNING] Failed to parse JSON. Using raw response instead.")
        print("Error:", e)
        state["timesheet_data"] = response

    print("[STEP 1 COMPLETE] Timesheet data extracted.\n")
    return state

def normalize_timesheet(state):
    """ Normalize and group raw timesheet data into rows structure for UI filling. Groups by (application, project, activity). """
    data = state.get("timesheet_data", {})
    app_code = data.get("application_code", "").strip()

    # Map weekday keys -> base ID names used in your HTML inputs
    day_map = {
        "monday": "MonHours",
        "tuesday": "TueHours",
        "wednesday": "WedHours",
        "thursday": "ThuHours",
        "friday": "FriHours",
        # if you care about weekend you can add SunHours / SatHours
    }

    # Keep insertion order: rows list will be used to create rows in UI (row 1, row 2, ...)
    rows = []
    key_map = {}  # (app, project, activity) -> row dict

    for day_key, base_id in day_map.items():
        for item in data.get(day_key, []):
            proj = item.get("project", "").strip()
            activity = str(item.get("activity", "")).strip()

            # --- normalize hours inline ---
            hours_val = item.get("hours", 0)
            if isinstance(hours_val, (int, float)):
                hours_str = f"{int(hours_val)}:00"
            else:
                s = str(hours_val).strip()
                hours_str = f"{s}:00" if s.isdigit() else s

            key = (app_code, proj, activity)
            if key not in key_map:
                row = {"application": app_code, "project": proj, "activity": activity, "hours": {}}
                key_map[key] = row
                rows.append(row)

            # merge into same row
            key_map[key]["hours"][base_id] = hours_str

    # Attach normalized rows back into state for downstream steps
    state["normalized_timesheet"] = rows
    return state

def modify_timesheet_with_llm(original_json: dict, user_text: str):
    """Uses Llama3 to intelligently update the previous timesheet JSON based on user's voice command."""
    condensed_prompt = f"""
    You are an AI assistant that updates employee timesheet data.

    Maintain the following structure and logic (same as used for initial extraction):

    1️⃣ Output JSON format:
    {{
        "application_code": "string",
        "monday": [{{"date": "MM/DD", "day": "Mon", "project": "string", "hours": int, "activity": "int", "activityLabel":"string"}}],
        "tuesday": [...],
        "wednesday": [...],
        "thursday": [...],
        "friday": [...],
        "NAW - VDSI Absence": [{{"date": "MM/DD", "day": "Day", "hours": int}}]
    }}

    2️⃣ Rules:
    - Monday–Friday only (no weekends unless explicitly mentioned).
    - "activity" field must always exist for work entries.
    - If a day has no entry, use [].
    - "NAW - VDSI Absence" only includes leave days (4 or 8 hours).
    - Hours must be integers.
    - Projects and activities retain same structure as before.

    3️⃣ Activity Options (for matching when new activity mentioned):
    - {{"1": "Planning, Tracking & Mgmt"}}
    - {{"2": "Requirements Definition & General Design"}}
    - {{"3": "Detailed Design"}}
    - {{"4": "Build"}}
    - {{"5": "Functionality Testing & Install - Excludes UAT"}}
    - {{"6": "Data Conversion, Data Migration & Table Entry"}}
    - {{"7": "Application Maintenance Support"}}
    - {{"8": "Infrastructure Maintenance Support"}}
    - {{"9": "End User Maintenance Support"}}
    - {{"10": "Implementation - Purchased Hardware"}}
    - {{"11": "Application Production Support"}}
    - {{"12": "Infrastructure Production Support"}}
    - {{"13": "End User Production Support"}}
    - {{"14": "Administration"}}
    - {{"15": "Training Conference"}}
    - {{"16": "Travel"}}
    - {{"17": "Employee Down Time"}}

    The user has requested some modifications to their existing timesheet.
    Apply only those modifications while preserving the rest exactly.

    Example:
    User says "Change Monday to 6 hours, make Tuesday leave"
    → You update the relevant fields and keep all others same.

    User modification text:
    "{user_text}"

    Previous JSON:
    {json.dumps(original_json, indent=2)}

    Now produce the UPDATED JSON (no commentary, only valid JSON).
    """

    response = llm.invoke(condensed_prompt)
    try:
        return json.loads(response)
    except Exception as e:
        print("⚠️ Failed to parse LLM JSON response:", e)
        return {"error": "Invalid LLM output", "raw_response": response}



graph = StateGraph(dict)
graph.add_node("extract", extract_timesheet_data)
graph.add_node("preview", normalize_timesheet)

# Add START entrypoint
graph.add_edge("__start__", "extract")
graph.add_edge("extract", "preview")
graph.add_edge("preview", "__end__")

workflow = graph.compile()
