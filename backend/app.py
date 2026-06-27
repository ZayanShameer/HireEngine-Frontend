from flask import Flask, request, jsonify
from flask_cors import CORS
import re

app = Flask(__name__)
# Enable CORS for frontend integration
CORS(app, resources={r"/api/*": {"origins": "*"}})

# 1. Domain Taxonomy Dictionary Specifications
DOMAIN_TAXONOMY = {
    'Oil & Gas': [
        'petroleum', 'drilling', 'refinery', 'offshore', 'pipeline', 'hydrocarbon',
        'gas reservoir', 'petrochemical', 'exploration', 'wellhead', 'downstream', 'upstream'
    ],
    'Railway': [
        'locomotive', 'rolling stock', 'signaling', 'track', 'rail', 'transit', 'metro',
        'cbtc', 'derailment', 'bogie', 'subway', 'carriage'
    ],
    'Electrical/Testing': [
        'transformer', 'relay', 'switchgear', 'gis', 'voltage', 'scada', 'ct', 'vt',
        'substation', 'high voltage', 'etap', 'relays'
    ],
    'Information Technology': [
        'react', 'typescript', 'javascript', 'python', 'flask', 'software', 'database',
        'sql', 'git', 'docker', 'aws', 'django', 'node', 'frontend', 'backend'
    ],
    'Healthcare': [
        'clinical', 'nursing', 'medical', 'hospital', 'patient', 'health', 'surgeon',
        'healthcare', 'diagnosis', 'clinic', 'pediatric'
    ]
}

# Supported Voltage Specialization Tags
SPECIALIZATION_POOL = [
    '13.8KV', '380KV', '765KV', 'HSE Certified', 'Deepwater Drilling', 
    'ETAP Certified', 'CBTC Systems', 'PLC/SCADA Developer'
]

# Supported skills pool for skills matrix extraction
SKILLS_POOL = [
    'REACT', 'TYPESCRIPT', 'JAVASCRIPT', 'PYTHON', 'SQL', 'GIT', 'DOCKER', 'AWS',
    'PETROLEUM PIPING', 'DRILLING SIMULATION', 'HSE RISK MANAGEMENT', 'ETAP SAFETY',
    'ROLLING STOCK MAINTENANCE', 'SIGNALING SYSTEMS', 'HIGH VOLTAGE RELAY', 'GIS MAINTENANCE',
    'SWITCHGEAR TESTING', 'SCADA CONTROL', 'NURSING CARE', 'CLINICAL TRIALS', 'FIGMA',
    'AUTOCAD', 'SOLIDWORKS', 'PROJECT MANAGEMENT', 'WELL LOGGING', 'SEISMIC ANALYSIS'
]

def extract_contacts(text):
    """Scan and parse candidate basic info using regular expressions"""
    email_regex = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    phone_regex = r'(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
    
    email_match = re.search(email_regex, text)
    phone_match = re.search(phone_regex, text)
    
    email = email_match.group(0) if email_match else "N/A"
    phone = phone_match.group(0) if phone_match else "N/A"
    
    # Try to parse candidate name from top lines
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    full_name = "Unknown Candidate"
    for line in lines[:3]:
        # Simple heuristic: line with 2-4 words, no numbers, no special symbols, no email
        if (2 <= len(line.split()) <= 4) and not re.search(r'\d', line) and '@' not in line:
            full_name = line
            break
            
    return full_name, email, phone

def parse_experience_years(text):
    """Estimate total experience years from textual descriptions"""
    # Look for patterns like "8+ years of experience" or "10 years experience"
    exp_patterns = [
        r'(\d+)\+?\s*years?\s+(?:of\s+)?experience',
        r'(\d+)\+?\s*yrs?\s+(?:of\s+)?experience',
        r'experience[:\s]+(\d+)\+?\s*years'
    ]
    for pattern in exp_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return float(match.group(1))
            
    # Heuristic fallback: count typical resume structure occurrences or return average
    return 5.0

@app.route('/api/v1/screen-candidate', methods=['POST'])
def screen_candidate():
    data = request.get_json()
    if not data or 'candidate_text' not in data or 'target_domain' not in data:
        return jsonify({"error": "Missing parameters 'candidate_text' or 'target_domain'"}), 400
        
    candidate_text = data['candidate_text']
    target_domain = data['target_domain']
    
    # Extract candidate metadata
    full_name, email, phone = extract_contacts(candidate_text)
    total_exp = parse_experience_years(candidate_text)
    
    # Identify skills present in resume
    skills_matrix = []
    text_upper = candidate_text.upper()
    for skill in SKILLS_POOL:
        if skill in text_upper:
            skills_matrix.append(skill)
            
    # Extract specialization tags
    specialization_tags = []
    for spec in SPECIALIZATION_POOL:
        if spec.lower() in candidate_text.lower():
            specialization_tags.append(spec)

    # Analyze keyword density per industry domain
    text_lower = candidate_text.lower()
    domain_scores = {}
    for domain, keywords in DOMAIN_TAXONOMY.items():
        count = 0
        for kw in keywords:
            # Match whole words or boundary combinations
            matches = re.findall(rf'\b{re.escape(kw)}\b', text_lower)
            count += len(matches)
        domain_scores[domain] = count

    # Determine candidate's main domain by frequency density
    candidate_domain = 'Information Technology'
    max_count = 0
    for domain, count in domain_scores.items():
        if count > max_count:
            max_count = count
            candidate_domain = domain

    # Determine Domain Match
    is_domain_match = (candidate_domain == target_domain)
    
    # Matching Logic & Mismatch Penalty execution
    relevant_exp = total_exp
    match_score = 50 # Base score

    if not is_domain_match and max_count >= 2:
        # Candidate's experience belongs to another industry (e.g. Railway)
        # Apply Mismatch Penalty: Cap match score to under 35%
        relevant_exp = float(round(total_exp * 0.15, 2))
        match_score = int(22 + (max_count % 10)) # Yields 22-31% capping under 35%
        
        remarks = (
            f"Domain Mismatch Penalty. Candidate has {total_exp:.1f} years of overall experience, "
            f"but their footprint is heavily concentrated in the {candidate_domain} industry (keyword density: {max_count}). "
            f"They lack the necessary specialized domain experience in {target_domain}."
        )
    else:
        # Match matches target domain or has no clear industry footprint, evaluate normally
        skill_factor = min(40, len(skills_matrix) * 8)
        exp_factor = min(40, total_exp * 6)
        spec_factor = min(20, len(specialization_tags) * 10)
        
        match_score = int(skill_factor + exp_factor + spec_factor)
        match_score = max(10, min(100, match_score)) # Clamp between 10 and 100
        
        remarks = (
            f"Strong Domain Match. Candidate possesses {relevant_exp:.1f} years of experience in {target_domain} "
            f"with matching industry-specific skills ({', '.join(skills_matrix[:4])})."
        )

    response_payload = {
        "full_name": full_name,
        "email": email,
        "phone": phone,
        "total_experience_years": total_exp,
        "relevant_experience_years": relevant_exp,
        "match_score": match_score,
        "skills_matrix": skills_matrix if skills_matrix else ["GENERAL TECHNICAL"],
        "specialization_tags": specialization_tags,
        "industry_remarks": remarks
    }

    return jsonify(response_payload)

if __name__ == '__main__':
    # Run server locally on standard port 5000
    app.run(host='0.0.0.0', port=5000, debug=True)
