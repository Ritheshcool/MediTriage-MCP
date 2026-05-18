"""
Seed Notion with Doctor Directory and Patient Records databases.
Run once to populate the hospital data.
"""

import os
import sys
import json
import requests
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

NOTION_API_KEY = os.getenv("NOTION_API_KEY")
NOTION_BASE = "https://api.notion.com/v1"
HEADERS = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

# ── Step 1: Find the MediTriage Hospital page ──
def find_parent_page():
    """Search for the MediTriage Hospital page."""
    res = requests.post(f"{NOTION_BASE}/search", headers=HEADERS, json={
        "query": "MediTriage Hospital",
        "filter": {"value": "page", "property": "object"}
    })
    results = res.json().get("results", [])
    if results:
        page_id = results[0]["id"]
        print(f"✅ Found parent page: {page_id}")
        return page_id
    else:
        print("❌ Could not find 'MediTriage Hospital' page. Create it in Notion first.")
        sys.exit(1)


# ── Step 2: Create Doctor Directory database ──
def create_doctor_directory(parent_id):
    """Create the Doctor Directory database."""
    payload = {
        "parent": {"type": "page_id", "page_id": parent_id},
        "title": [{"type": "text", "text": {"content": "Doctor Directory"}}],
        "is_inline": True,
        "properties": {
            "Name": {"title": {}},
            "Specialty": {"select": {
                "options": [
                    {"name": "Cardiology", "color": "red"},
                    {"name": "Neurology", "color": "purple"},
                    {"name": "Pulmonology", "color": "blue"},
                    {"name": "Orthopedics", "color": "green"},
                    {"name": "Dermatology", "color": "pink"},
                    {"name": "Gastroenterology", "color": "orange"},
                    {"name": "ENT", "color": "yellow"},
                    {"name": "Ophthalmology", "color": "blue"},
                    {"name": "Psychiatry", "color": "purple"},
                    {"name": "General Medicine", "color": "gray"},
                    {"name": "Internal Medicine", "color": "brown"},
                    {"name": "Urology", "color": "green"},
                    {"name": "Endocrinology", "color": "orange"},
                    {"name": "Rheumatology", "color": "red"},
                    {"name": "Pediatrics", "color": "pink"},
                ]
            }},
            "Email": {"email": {}},
            "Phone": {"phone_number": {}},
            "Experience": {"number": {"format": "number"}},
            "Rating": {"number": {"format": "number"}},
            "Available Days": {"multi_select": {
                "options": [
                    {"name": "Monday", "color": "blue"},
                    {"name": "Tuesday", "color": "green"},
                    {"name": "Wednesday", "color": "orange"},
                    {"name": "Thursday", "color": "purple"},
                    {"name": "Friday", "color": "red"},
                    {"name": "Saturday", "color": "yellow"},
                ]
            }},
            "Status": {"select": {
                "options": [
                    {"name": "Active", "color": "green"},
                    {"name": "On Leave", "color": "orange"},
                ]
            }},
        }
    }
    res = requests.post(f"{NOTION_BASE}/databases", headers=HEADERS, json=payload)
    if res.status_code == 200:
        db_id = res.json()["id"]
        print(f"✅ Created Doctor Directory: {db_id}")
        return db_id
    else:
        print(f"❌ Failed to create Doctor Directory: {res.text}")
        sys.exit(1)


# ── Step 3: Create Patient Records database ──
def create_patient_records(parent_id):
    """Create the Patient Records database."""
    payload = {
        "parent": {"type": "page_id", "page_id": parent_id},
        "title": [{"type": "text", "text": {"content": "Patient Records"}}],
        "is_inline": True,
        "properties": {
            "Name": {"title": {}},
            "Age": {"number": {"format": "number"}},
            "Gender": {"select": {
                "options": [
                    {"name": "Male", "color": "blue"},
                    {"name": "Female", "color": "pink"},
                    {"name": "Other", "color": "gray"},
                ]
            }},
            "Symptoms": {"rich_text": {}},
            "Severity": {"number": {"format": "number"}},
            "Specialty Referred": {"select": {}},
            "Doctor Assigned": {"rich_text": {}},
            "Appointment Date": {"date": {}},
            "Status": {"select": {
                "options": [
                    {"name": "Triaged", "color": "yellow"},
                    {"name": "Scheduled", "color": "blue"},
                    {"name": "Completed", "color": "green"},
                    {"name": "Cancelled", "color": "red"},
                ]
            }},
            "Notes": {"rich_text": {}},
        }
    }
    res = requests.post(f"{NOTION_BASE}/databases", headers=HEADERS, json=payload)
    if res.status_code == 200:
        db_id = res.json()["id"]
        print(f"✅ Created Patient Records: {db_id}")
        return db_id
    else:
        print(f"❌ Failed to create Patient Records: {res.text}")
        sys.exit(1)


# ── Step 4: Seed doctors ──
DOCTORS = [
    {"name": "Dr. Priya Sharma", "specialty": "Cardiology", "email": "priya.sharma@meditriage.com", "phone": "+91-9876543210", "exp": 15, "rating": 4.8, "days": ["Monday", "Wednesday", "Friday"]},
    {"name": "Dr. Rajesh Patel", "specialty": "Cardiology", "email": "rajesh.patel@meditriage.com", "phone": "+91-9876543211", "exp": 12, "rating": 4.6, "days": ["Tuesday", "Thursday", "Saturday"]},
    {"name": "Dr. Ananya Iyer", "specialty": "Neurology", "email": "ananya.iyer@meditriage.com", "phone": "+91-9876543212", "exp": 10, "rating": 4.9, "days": ["Monday", "Tuesday", "Thursday"]},
    {"name": "Dr. Vikram Singh", "specialty": "Neurology", "email": "vikram.singh@meditriage.com", "phone": "+91-9876543213", "exp": 18, "rating": 4.7, "days": ["Wednesday", "Friday", "Saturday"]},
    {"name": "Dr. Sneha Reddy", "specialty": "Pulmonology", "email": "sneha.reddy@meditriage.com", "phone": "+91-9876543214", "exp": 8, "rating": 4.5, "days": ["Monday", "Wednesday", "Friday"]},
    {"name": "Dr. Arjun Nair", "specialty": "Orthopedics", "email": "arjun.nair@meditriage.com", "phone": "+91-9876543215", "exp": 14, "rating": 4.8, "days": ["Tuesday", "Thursday", "Saturday"]},
    {"name": "Dr. Meera Joshi", "specialty": "Dermatology", "email": "meera.joshi@meditriage.com", "phone": "+91-9876543216", "exp": 7, "rating": 4.6, "days": ["Monday", "Wednesday", "Friday"]},
    {"name": "Dr. Karthik Menon", "specialty": "Gastroenterology", "email": "karthik.menon@meditriage.com", "phone": "+91-9876543217", "exp": 11, "rating": 4.7, "days": ["Tuesday", "Thursday"]},
    {"name": "Dr. Divya Krishnan", "specialty": "ENT", "email": "divya.krishnan@meditriage.com", "phone": "+91-9876543218", "exp": 9, "rating": 4.5, "days": ["Monday", "Wednesday", "Saturday"]},
    {"name": "Dr. Sanjay Gupta", "specialty": "Ophthalmology", "email": "sanjay.gupta@meditriage.com", "phone": "+91-9876543219", "exp": 16, "rating": 4.9, "days": ["Tuesday", "Thursday", "Friday"]},
    {"name": "Dr. Lakshmi Venkat", "specialty": "Psychiatry", "email": "lakshmi.venkat@meditriage.com", "phone": "+91-9876543220", "exp": 13, "rating": 4.8, "days": ["Monday", "Wednesday", "Friday"]},
    {"name": "Dr. Amit Kumar", "specialty": "General Medicine", "email": "amit.kumar@meditriage.com", "phone": "+91-9876543221", "exp": 20, "rating": 4.7, "days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]},
    {"name": "Dr. Ritu Agarwal", "specialty": "General Medicine", "email": "ritu.agarwal@meditriage.com", "phone": "+91-9876543222", "exp": 10, "rating": 4.5, "days": ["Monday", "Wednesday", "Friday", "Saturday"]},
    {"name": "Dr. Suresh Pillai", "specialty": "Internal Medicine", "email": "suresh.pillai@meditriage.com", "phone": "+91-9876543223", "exp": 17, "rating": 4.8, "days": ["Tuesday", "Thursday", "Saturday"]},
    {"name": "Dr. Pooja Deshmukh", "specialty": "Urology", "email": "pooja.deshmukh@meditriage.com", "phone": "+91-9876543224", "exp": 9, "rating": 4.6, "days": ["Monday", "Wednesday", "Friday"]},
    {"name": "Dr. Rahul Mehta", "specialty": "Endocrinology", "email": "rahul.mehta@meditriage.com", "phone": "+91-9876543225", "exp": 11, "rating": 4.7, "days": ["Tuesday", "Thursday"]},
    {"name": "Dr. Kavitha Rao", "specialty": "Rheumatology", "email": "kavitha.rao@meditriage.com", "phone": "+91-9876543226", "exp": 8, "rating": 4.5, "days": ["Monday", "Wednesday", "Saturday"]},
    {"name": "Dr. Nikhil Bhatia", "specialty": "Pediatrics", "email": "nikhil.bhatia@meditriage.com", "phone": "+91-9876543227", "exp": 12, "rating": 4.9, "days": ["Monday", "Tuesday", "Thursday", "Friday"]},
]

def seed_doctors(db_id):
    """Add all doctors to the database."""
    for doc in DOCTORS:
        payload = {
            "parent": {"database_id": db_id},
            "properties": {
                "Name": {"title": [{"text": {"content": doc["name"]}}]},
                "Specialty": {"select": {"name": doc["specialty"]}},
                "Email": {"email": doc["email"]},
                "Phone": {"phone_number": doc["phone"]},
                "Experience": {"number": doc["exp"]},
                "Rating": {"number": doc["rating"]},
                "Available Days": {"multi_select": [{"name": d} for d in doc["days"]]},
                "Status": {"select": {"name": "Active"}},
            }
        }
        res = requests.post(f"{NOTION_BASE}/pages", headers=HEADERS, json=payload)
        if res.status_code == 200:
            print(f"  ✅ Added {doc['name']} ({doc['specialty']})")
        else:
            print(f"  ❌ Failed to add {doc['name']}: {res.status_code}")


# ── Main ──
if __name__ == "__main__":
    print("🏥 Seeding MediTriage Notion Database...\n")

    parent_id = find_parent_page()
    print()

    print("📋 Creating Doctor Directory...")
    doctor_db_id = create_doctor_directory(parent_id)
    print()

    print("📝 Creating Patient Records...")
    patient_db_id = create_patient_records(parent_id)
    print()

    print(f"👨‍⚕️ Adding {len(DOCTORS)} doctors...")
    seed_doctors(doctor_db_id)
    print()

    print("=" * 50)
    print("✅ Seeding complete!")
    print(f"   Doctor Directory ID: {doctor_db_id}")
    print(f"   Patient Records ID: {patient_db_id}")
    print(f"   Total Doctors: {len(DOCTORS)}")
    print("=" * 50)
