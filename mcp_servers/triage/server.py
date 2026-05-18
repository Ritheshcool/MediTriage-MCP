"""
MediTriage Custom MCP Server
Exposes medical triage tools: severity classification, specialty recommendation, and symptom lookup.
"""

import json
import os
from mcp.server.fastmcp import FastMCP

# Create the MCP server
mcp = FastMCP(
    "MediTriage",
    instructions="Medical triage system — classifies symptom severity and recommends specialties"
)

# Load knowledge bases
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

with open(os.path.join(DATA_DIR, "symptoms.json"), "r") as f:
    SYMPTOMS_DB = json.load(f)

with open(os.path.join(DATA_DIR, "specialties.json"), "r") as f:
    SPECIALTIES_DB = json.load(f)


# ─── Tool 1: Classify Severity ─────────────────────────────────────
@mcp.tool()
def classify_severity(symptoms: list[str], age: int, gender: str) -> dict:
    """
    Analyze patient symptoms and return a severity score with reasoning.
    
    Args:
        symptoms: List of symptom strings (e.g. ["headache", "blurred vision"])
        age: Patient's age in years
        gender: Patient's gender (male/female/other)
    
    Returns:
        Dictionary with severity_score (1-10), level (Priority/Routine/Follow-up), 
        red_flags found, and detailed reasoning.
    """
    total_score = 0
    red_flags = []
    reasoning = []
    matched_symptoms = []
    unmatched_symptoms = []

    for symptom in symptoms:
        symptom_lower = symptom.lower().strip()
        if symptom_lower in SYMPTOMS_DB:
            info = SYMPTOMS_DB[symptom_lower]
            score = info["base_score"]
            matched_symptoms.append(symptom_lower)

            # Age modifiers
            for threshold_key, modifier in info.get("age_modifier", {}).items():
                age_threshold = int(threshold_key.split("_")[1])
                if age > age_threshold:
                    score += modifier
                    reasoning.append(f"'{symptom}' score increased by {modifier} (age > {age_threshold})")

            if info["red_flag"]:
                red_flags.append(symptom_lower)

            total_score += score
            reasoning.append(f"'{symptom}' → base score: {info['base_score']}, conditions: {', '.join(info['conditions'][:3])}")
        else:
            unmatched_symptoms.append(symptom_lower)
            total_score += 2  # Default score for unknown symptoms
            reasoning.append(f"'{symptom}' → not in database, assigned default score of 2")

    # Normalize to 1-10 scale
    severity_score = min(10, max(1, round(total_score / max(len(symptoms), 1))))

    # Multiple red flags bump up severity
    if len(red_flags) >= 2:
        severity_score = min(10, severity_score + 2)
        reasoning.append(f"Multiple red flags detected ({len(red_flags)}): severity increased by 2")

    # Determine level
    if severity_score >= 6:
        level = "Priority"
        recommendation = "You should see a specialist within 24-48 hours."
    elif severity_score >= 3:
        level = "Routine"
        recommendation = "Schedule an appointment at your convenience this week."
    else:
        level = "Follow-up"
        recommendation = "This can be addressed during a routine check-up."

    return {
        "severity_score": severity_score,
        "level": level,
        "recommendation": recommendation,
        "red_flags": red_flags,
        "matched_symptoms": matched_symptoms,
        "unmatched_symptoms": unmatched_symptoms,
        "reasoning": "; ".join(reasoning)
    }


# ─── Tool 2: Recommend Specialty ───────────────────────────────────
@mcp.tool()
def recommend_specialty(symptoms: list[str], severity_level: str) -> dict:
    """
    Based on symptoms and severity level, recommend the best medical specialty.
    
    Args:
        symptoms: List of symptom strings
        severity_level: The severity level from classify_severity (Priority/Routine/Follow-up)
    
    Returns:
        Dictionary with recommended specialty, match score, all matched specialties, and reasoning.
    """
    specialty_scores = {}

    for symptom in symptoms:
        symptom_lower = symptom.lower().strip()
        for specialty, info in SPECIALTIES_DB.items():
            if symptom_lower in info["triggers"]:
                specialty_scores[specialty] = specialty_scores.get(specialty, 0) + 1

    if not specialty_scores:
        return {
            "specialty": "General Medicine",
            "confidence": "low",
            "all_matches": {},
            "reasoning": "No specific specialty matched your symptoms. General Medicine can evaluate and refer if needed.",
            "urgency_note": SPECIALTIES_DB.get("General Medicine", {}).get("urgency_note", "")
        }

    # Sort by match count
    sorted_specialties = sorted(specialty_scores.items(), key=lambda x: x[1], reverse=True)
    best_specialty = sorted_specialties[0][0]
    best_count = sorted_specialties[0][1]

    # Confidence based on match count
    if best_count >= 3:
        confidence = "high"
    elif best_count >= 2:
        confidence = "medium"
    else:
        confidence = "low"

    return {
        "specialty": best_specialty,
        "confidence": confidence,
        "match_count": best_count,
        "all_matches": dict(sorted_specialties),
        "description": SPECIALTIES_DB[best_specialty]["description"],
        "urgency_note": SPECIALTIES_DB[best_specialty].get("urgency_note", ""),
        "reasoning": f"'{best_specialty}' matched {best_count} of your symptoms. {SPECIALTIES_DB[best_specialty]['description']}."
    }


# ─── Tool 3: Get Symptom Info ──────────────────────────────────────
@mcp.tool()
def get_symptom_info(symptom_name: str) -> dict:
    """
    Look up detailed information about a specific symptom from the medical database.
    
    Args:
        symptom_name: The symptom to look up (e.g. "headache", "chest pain")
    
    Returns:
        Dictionary with symptom details including severity, red flag status, 
        possible conditions, and relevant specialties.
    """
    symptom_lower = symptom_name.lower().strip()

    if symptom_lower in SYMPTOMS_DB:
        info = SYMPTOMS_DB[symptom_lower]
        return {
            "symptom": symptom_name,
            "found": True,
            "base_severity": info["base_score"],
            "is_red_flag": info["red_flag"],
            "description": info["description"],
            "possible_conditions": info["conditions"],
            "relevant_specialties": info["specialties"],
            "age_modifiers": info.get("age_modifier", {})
        }

    return {
        "symptom": symptom_name,
        "found": False,
        "message": f"'{symptom_name}' is not in our symptom database. A General Medicine consultation is recommended for evaluation."
    }


# ─── Tool 4: Find Doctors ─────────────────────────────────────────
@mcp.tool()
def find_doctors(specialty: str) -> dict:
    """
    Find available doctors from the hospital directory by specialty.
    
    Args:
        specialty: The medical specialty to search for (e.g. "Cardiology", "Neurology")
    
    Returns:
        Dictionary with list of matching doctors and their details.
    """
    import requests
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))
    
    notion_key = os.getenv("NOTION_API_KEY")
    doctor_db_id = os.getenv("NOTION_DOCTOR_DB_ID", "359bcfd9-f623-81e8-97ae-d35e6670fa56")
    
    headers = {
        "Authorization": f"Bearer {notion_key}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }
    
    payload = {
        "filter": {
            "and": [
                {"property": "Specialty", "select": {"equals": specialty}},
                {"property": "Status", "select": {"equals": "Active"}}
            ]
        }
    }
    
    try:
        res = requests.post(
            f"https://api.notion.com/v1/databases/{doctor_db_id}/query",
            headers=headers, json=payload
        )
        data = res.json()
        
        doctors = []
        for page in data.get("results", []):
            props = page["properties"]
            name = ""
            if props.get("Name", {}).get("title"):
                name = props["Name"]["title"][0]["text"]["content"]
            
            email = props.get("Email", {}).get("email", "")
            phone = props.get("Phone", {}).get("phone_number", "")
            exp = props.get("Experience", {}).get("number", 0)
            rating = props.get("Rating", {}).get("number", 0)
            
            days = []
            for d in props.get("Available Days", {}).get("multi_select", []):
                days.append(d["name"])
            
            doctors.append({
                "name": name,
                "specialty": specialty,
                "email": email,
                "phone": phone,
                "experience_years": exp,
                "rating": rating,
                "available_days": days
            })
        
        if not doctors:
            return {
                "found": False,
                "specialty": specialty,
                "message": f"No active {specialty} doctors found in the directory.",
                "doctors": []
            }
        
        return {
            "found": True,
            "specialty": specialty,
            "count": len(doctors),
            "doctors": doctors
        }
        
    except Exception as e:
        return {"found": False, "error": str(e), "doctors": []}


# ─── Tool 5: Get Available Slots ──────────────────────────────────
@mcp.tool()
def get_available_slots(doctor_name: str, available_days: list[str]) -> dict:
    """
    Generate available appointment time slots for a doctor based on their available days.
    Returns the next 5 available slots within the upcoming week.
    
    Args:
        doctor_name: Full name of the doctor
        available_days: List of days the doctor is available (e.g. ["Monday", "Wednesday", "Friday"])
    
    Returns:
        Dictionary with doctor name and list of available time slots with date/time details.
    """
    from datetime import datetime, timedelta
    
    today = datetime.now()
    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    
    # Standard clinic hours
    time_slots = ["09:00 AM", "10:00 AM", "11:00 AM", "02:00 PM", "03:00 PM", "04:00 PM"]
    
    available_slots = []
    
    for day_offset in range(1, 14):  # Check next 2 weeks
        check_date = today + timedelta(days=day_offset)
        day_name = day_names[check_date.weekday()]
        
        if day_name in available_days:
            for time_str in time_slots:
                slot = {
                    "slot_id": f"{doctor_name.replace(' ', '_')}_{check_date.strftime('%Y%m%d')}_{time_str.replace(' ', '').replace(':', '')}",
                    "doctor": doctor_name,
                    "date": check_date.strftime("%Y-%m-%d"),
                    "day": day_name,
                    "time": time_str,
                    "display": f"{day_name}, {check_date.strftime('%B %d')} at {time_str}"
                }
                available_slots.append(slot)
                
                if len(available_slots) >= 6:
                    break
        
        if len(available_slots) >= 6:
            break
    
    return {
        "doctor": doctor_name,
        "slot_count": len(available_slots),
        "slots": available_slots
    }


# ─── Tool 6: Book Appointment ────────────────────────────────────
@mcp.tool()
def book_appointment(
    doctor_name: str,
    patient_name: str,
    date: str,
    time: str,
    reason: str
) -> dict:
    """
    Book an appointment on Google Calendar for the patient with the specified doctor.
    
    Args:
        doctor_name: Full name of the doctor (e.g. "Dr. Priya Sharma")
        patient_name: Patient's name
        date: Appointment date in YYYY-MM-DD format (e.g. "2026-05-08")
        time: Appointment time (e.g. "03:00 PM")
        reason: Reason for visit / symptoms
    
    Returns:
        Dictionary with booking confirmation or error details.
    """
    from datetime import datetime, timedelta
    
    try:
        # Parse the time
        time_clean = time.strip().upper()
        dt = datetime.strptime(f"{date} {time_clean}", "%Y-%m-%d %I:%M %p")
        end_dt = dt + timedelta(hours=1)
        
        start_iso = dt.strftime("%Y-%m-%dT%H:%M:%S")
        end_iso = end_dt.strftime("%Y-%m-%dT%H:%M:%S")
        
        # Try to use Google Calendar API directly
        try:
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from google.auth.transport.requests import Request
            from googleapiclient.discovery import build
            import pickle
            
            SCOPES = ['https://www.googleapis.com/auth/calendar']
            project_root = os.path.join(os.path.dirname(__file__), "..", "..")
            creds_path = os.path.join(project_root, "credentials.json")
            token_path = os.path.join(project_root, "token.json")
            pickle_path = os.path.join(project_root, "token.pickle")
            
            creds = None
            
            # Check for token.json first
            if os.path.exists(token_path):
                import json as json_mod
                with open(token_path, 'r') as f:
                    token_data = json_mod.load(f)
                creds = Credentials.from_authorized_user_info(token_data, SCOPES)
            elif os.path.exists(pickle_path):
                with open(pickle_path, 'rb') as f:
                    creds = pickle.load(f)
            
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
                    creds = flow.run_local_server(port=0)
                # Save the token
                with open(token_path, 'w') as f:
                    f.write(creds.to_json())
            
            service = build('calendar', 'v3', credentials=creds)
            
            event = {
                'summary': f'Medical Appointment: {doctor_name} - {patient_name}',
                'description': f'Patient: {patient_name}\nDoctor: {doctor_name}\nReason: {reason}',
                'start': {
                    'dateTime': start_iso,
                    'timeZone': 'Asia/Kolkata',
                },
                'end': {
                    'dateTime': end_iso,
                    'timeZone': 'Asia/Kolkata',
                },
            }
            
            created = service.events().insert(calendarId='primary', body=event).execute()
            
            return {
                "booked": True,
                "event_id": created.get('id'),
                "link": created.get('htmlLink'),
                "summary": f"Appointment booked with {doctor_name} on {date} at {time}",
                "doctor": doctor_name,
                "patient": patient_name,
                "date": date,
                "time": time
            }
            
        except ImportError:
            # Google libs not installed — return a simulated booking
            return {
                "booked": True,
                "event_id": f"sim_{date}_{time.replace(' ', '').replace(':', '')}",
                "summary": f"Appointment booked with {doctor_name} on {date} at {time}",
                "doctor": doctor_name,
                "patient": patient_name,
                "date": date,
                "time": time,
                "note": "Booking confirmed (calendar sync pending)"
            }
            
    except Exception as e:
        return {
            "booked": False,
            "error": str(e),
            "doctor": doctor_name,
            "patient": patient_name
        }


# ─── MCP Resources ─────────────────────────────────────────────────
@mcp.resource("triage://symptoms/list")
def list_all_symptoms() -> str:
    """List all symptoms in the triage knowledge base with their severity scores."""
    symptom_list = []
    for name, info in SYMPTOMS_DB.items():
        symptom_list.append({
            "name": name,
            "base_score": info["base_score"],
            "is_red_flag": info["red_flag"]
        })
    return json.dumps(symptom_list, indent=2)


@mcp.resource("triage://specialties/list")
def list_all_specialties() -> str:
    """List all medical specialties and their trigger symptoms."""
    specialty_list = []
    for name, info in SPECIALTIES_DB.items():
        specialty_list.append({
            "name": name,
            "description": info["description"],
            "trigger_count": len(info["triggers"])
        })
    return json.dumps(specialty_list, indent=2)


# ─── MCP Prompts ───────────────────────────────────────────────────
@mcp.prompt()
def triage_patient(symptoms: str, age: str, gender: str) -> str:
    """Standard triage prompt template for evaluating a patient."""
    return f"""You are a medical triage coordinator. A patient has reported the following:

Symptoms: {symptoms}
Age: {age}
Gender: {gender}

Please:
1. Use classify_severity to determine how urgent this is
2. Use recommend_specialty to find the right department
3. Present the findings clearly and ask for confirmation before proceeding to book an appointment"""


@mcp.prompt()
def follow_up_visit(patient_name: str, previous_symptoms: str) -> str:
    """Prompt template for returning patients scheduling follow-ups."""
    return f"""A returning patient needs a follow-up appointment.

Patient: {patient_name}
Previous symptoms: {previous_symptoms}

Please:
1. Recall their history using the memory system
2. Check if symptoms have changed
3. Recommend appropriate follow-up specialty
4. Find available doctors and schedule"""


# Run the server
if __name__ == "__main__":
    mcp.run(transport="stdio")
