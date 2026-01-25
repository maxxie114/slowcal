import os
import json
import random
from datetime import datetime, timedelta
from pathlib import Path
from supabase import create_client, Client

# Supabase Configuration
SUPABASE_URL = "https://lvlkgssnfmszujxtrasa.supabase.co"
SUPABASE_KEY = "sb_publishable_l8Cx8bsqkPZ-B_q3ka6MmQ_JspTcv30"

def generate_synthetic_evidence():
    """
    Fetches businesses from Supabase and generates RICH synthetic evidence for them.
    """
    print(f"Connecting to Supabase at {SUPABASE_URL}...")
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # 1. Fetch businesses from master_model_data
    print("Fetching businesses from 'master_model_data'...")
    try:
        response = supabase.table('master_model_data').select('*').limit(100).execute()
        businesses = response.data
    except Exception as e:
        print(f"Error fetching businesses: {e}")
        return

    if not businesses:
        print("No businesses found in Supabase.")
        return

    print(f"Found {len(businesses)} businesses. Generating comprehensive evidence...")

    all_evidence = {
        "businesses": [],
        "permits": [],
        "violations": [],
        "complaints_311": [],
        "sfpd_incidents": []
    }

    # Reference lists for realistic data
    permit_types = [
        "Building Permit", "Electrical Permit", "Plumbing Permit", "Fire Alarm", 
        "Signage", "Street Space", "Boiler Permit", "Mechanical Permit"
    ]
    
    violation_types = [
        "Health Code - High Risk", "Health Code - Moderate Risk", 
        "Building Code - Construction w/o Permit", "Fire Safety - Blocked Exit",
        "Signage Violation", "Noise Ordinance Exceeded", "Public Nuisance",
        "Americans with Disabilities Act (ADA)"
    ]
    
    complaint_311_categories = [
        "Street and Sidewalk Cleaning", "Graffiti", "Noise Report", 
        "Blocked Sidewalk", "Encampment", "Illegal Postings", 
        "Sewer Issues", "Tree Maintenance"
    ]
    
    sfpd_incident_categories = [
        "Larceny/Theft", "Vandalism", "Assault", "Burglary", 
        "Disorderly Conduct", "Motor Vehicle Theft", "Drug Offense",
        "Fraud"
    ]

    for biz in businesses:
        biz_id = biz.get('id')
        
        # Ensure it looks like an SF business for the agents
        biz['city'] = 'San Francisco'
        biz['uniqueid'] = str(biz_id)
        biz['ttxid'] = f"TTX-{biz_id}"
        
        # Assign fixed coordinates if missing
        if 'latitude' not in biz or not biz['latitude']:
            # Cluster around downtown/mission for realism
            lat_base = 37.7749
            lon_base = -122.4194
            lat_offset = random.uniform(-0.03, 0.03)
            lon_offset = random.uniform(-0.03, 0.03)
            
            biz['latitude'] = lat_base + lat_offset
            biz['longitude'] = lon_base + lon_offset
            
            # Update address if generic
            if not biz.get('full_business_address'):
                biz['full_business_address'] = f"{random.randint(100, 9999)} Mock St"
        
        biz_name = biz.get('dba_name') or biz.get('ownership_name') or "Unknown Business"
        biz_address = biz.get('full_business_address')
        neighborhood = biz.get('neighborhood') or "Unknown"
        
        # Assess risk profile for scaling
        risk_level = (biz.get('risk_level') or 'low').lower()
        risk_score = biz.get('risk_score') or 0.1
        
        # Base multipliers
        # High risk businesses get significantly more negative signals
        multiplier = 1.0
        if risk_level in ['high', 'critical'] or risk_score > 0.7:
            multiplier = 4.0
        elif risk_level in ['medium', 'moderate'] or risk_score > 0.4:
            multiplier = 2.0
            
        permit_multiplier = 1.0 # Permits can be good or bad (renovation vs correction)
        
        # --- Save Enhanced Business Record ---
        all_evidence["businesses"].append(biz)

        # --- Generate Permits (3-8 per business usually) ---
        num_permits = random.randint(3, 10)
        for _ in range(num_permits):
            filed_date = datetime.now() - timedelta(days=random.randint(30, 730))
            
            # Status distribution
            status_opts = ["Issued", "Approved", "Filed", "Expired", "Completed"]
            status_weights = [0.4, 0.2, 0.1, 0.1, 0.2]
            status = random.choices(status_opts, weights=status_weights)[0]
            
            permit = {
                "business_id": biz_id,
                "business_name": biz_name,
                "permit_number": f"P-{random.randint(10000, 99999)}",
                "permit_type": random.choice(permit_types),
                "status": status,
                "filed_date": filed_date.isoformat(),
                "issued_date": (filed_date + timedelta(days=random.randint(5, 60))).isoformat() if status in ["Issued", "Completed", "Expired"] else None,
                "address": biz_address,
                "neighborhood": neighborhood,
                "location": {"latitude": biz['latitude'], "longitude": biz['longitude']},
                "estimated_cost": random.randint(1000, 500000)
            }
            all_evidence["permits"].append(permit)

        # --- Generate Violations (Scaled by risk) ---
        if risk_level != 'low' or random.random() < 0.3:
            num_violations = int(random.randint(1, 5) * multiplier)
            if risk_level == 'low': num_violations = random.randint(0, 1)
            
            for _ in range(num_violations):
                date_filed = datetime.now() - timedelta(days=random.randint(30, 365))
                
                violation = {
                    "business_id": biz_id,
                    "business_name": biz_name,
                    "violation_type": random.choice(violation_types),
                    "status": random.choice(["Resolved", "Open", "Correction Pending", "Abated"]),
                    "date_filed": date_filed.isoformat(),
                    "address": biz_address,
                    "neighborhood": neighborhood,
                    "location": {"latitude": biz['latitude'], "longitude": biz['longitude']},
                    "description": f"Compliance issue related to {biz_name} operations."
                }
                all_evidence["violations"].append(violation)

        # --- Generate 311 Complaints (Scaled by risk + random noise) ---
        num_complaints = int(random.randint(2, 8) * multiplier)
        for _ in range(num_complaints):
            opened_date = datetime.now() - timedelta(days=random.randint(1, 365))
            
            complaint = {
                "business_id": biz_id,
                "business_name": biz_name,
                "category": random.choice(complaint_311_categories),
                "status": random.choice(["Closed", "Open", "In Progress"]),
                "opened_date": opened_date.isoformat(),
                "address": biz_address,
                "neighborhood": neighborhood,
                "location": {"latitude": biz['latitude'], "longitude": biz['longitude']},
                "source": "Voice In",
                "media_url": "http://placeholder.com/image.jpg"
            }
            all_evidence["complaints_311"].append(complaint)

        # --- Generate SFPD Incidents (Scaled by risk) ---
        # High risk businesses might have more incidents nearby
        num_incidents = int(random.randint(0, 4) * multiplier)
        for _ in range(num_incidents):
            incident_date = datetime.now() - timedelta(days=random.randint(1, 365))
            
            incident = {
                "business_id": biz_id,
                "business_name": biz_name,
                "category": random.choice(sfpd_incident_categories),
                "incident_date": incident_date.isoformat(),
                "address": biz_address,
                "neighborhood": neighborhood,
                "location": {"latitude": biz['latitude'], "longitude": biz['longitude']},
                "resolution": random.choice(["Open", "Arrest", "Cited", "Unfounded", "None"]),
                "incident_id": f"SFPD-{random.randint(100000, 999999)}"
            }
            all_evidence["sfpd_incidents"].append(incident)

    # Save to file
    output_path = Path("data/synthetic_evidence.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(all_evidence, f, indent=2)

    print(f"\nSynthetic evidence generated successfully!")
    print(f"File saved to: {output_path}")
    print(f"Summary:")
    print(f" - Businesses: {len(all_evidence['businesses'])}")
    print(f" - Permits: {len(all_evidence['permits'])}")
    print(f" - Violations: {len(all_evidence['violations'])}")
    print(f" - 311 Complaints: {len(all_evidence['complaints_311'])}")
    print(f" - SFPD Incidents: {len(all_evidence['sfpd_incidents'])}")

if __name__ == "__main__":
    generate_synthetic_evidence()
