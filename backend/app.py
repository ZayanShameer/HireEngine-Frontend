from flask import Flask, request, jsonify
from flask_cors import CORS
import re
import os
import tempfile
import shutil

# Optional libraries for PDF and DOCX parsing
try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

try:
    import pypdf
except ImportError:
    pypdf = None

try:
    import docx
except ImportError:
    docx = None

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

def score_candidate_data(candidate_text, target_domain):
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

    return {
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

@app.route('/api/v1/screen-candidate', methods=['POST'])
def screen_candidate():
    data = request.get_json()
    if not data or 'candidate_text' not in data or 'target_domain' not in data:
        return jsonify({"error": "Missing parameters 'candidate_text' or 'target_domain'"}), 400
        
    candidate_text = data['candidate_text']
    target_domain = data['target_domain']
    
    response_payload = score_candidate_data(candidate_text, target_domain)
    return jsonify(response_payload)

def extract_text_from_file(file_path):
    ext = os.path.splitext(file_path)[1].lower()
    text = ""
    
    if ext == '.pdf':
        if fitz:
            try:
                doc = fitz.open(file_path)
                text = "\n".join([page.get_text() for page in doc])
            except Exception as e:
                text = f"[Error reading PDF with PyMuPDF: {str(e)}]"
        elif pypdf:
            try:
                reader = pypdf.PdfReader(file_path)
                text = "\n".join([page.extract_text() or "" for page in reader.pages])
            except Exception as e:
                text = f"[Error reading PDF with pypdf: {str(e)}]"
        else:
            text = "[PDF parser library (PyMuPDF or pypdf) not installed on server]"
            
    elif ext in ['.docx', '.doc']:
        if docx:
            try:
                doc = docx.Document(file_path)
                text = "\n".join([p.text for p in doc.paragraphs])
            except Exception as e:
                text = f"[Error reading Word document: {str(e)}]"
        else:
            text = "[Word document parser library python-docx not installed on server]"
            
    elif ext in ['.txt', '.rtf']:
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                text = f.read()
        except Exception as e:
            text = f"[Error reading text file: {str(e)}]"
            
    return text

def get_mock_candidates_for_domain(target_domain):
    if target_domain == 'Oil & Gas':
        return [
            {
                "fileName": "Sarah_Jenkins_CV.pdf",
                "fileSize": 142300,
                "parsedData": {
                    "full_name": "Sarah Jenkins",
                    "email": "sarah.jenkins@petroleum-eng.com",
                    "phone": "+1 (555) 014-8821",
                    "total_experience_years": 10.0,
                    "relevant_experience_years": 10.0,
                    "match_score": 88,
                    "skills_matrix": ["PETROLEUM PIPING", "DRILLING SIMULATION", "HSE RISK MANAGEMENT", "PROJECT MANAGEMENT"],
                    "specialization_tags": ["Deepwater Drilling", "HSE Certified"],
                    "industry_remarks": "Strong Domain Match. Candidate possesses 10.0 years of experience in Oil & Gas with matching industry-specific skills (PETROLEUM PIPING, DRILLING SIMULATION)."
                }
            },
            {
                "fileName": "Michael_Chang_Resume.docx",
                "fileSize": 88400,
                "parsedData": {
                    "full_name": "Michael Chang",
                    "email": "m.chang@refineryops.org",
                    "phone": "+1 (555) 982-1430",
                    "total_experience_years": 4.0,
                    "relevant_experience_years": 4.0,
                    "match_score": 58,
                    "skills_matrix": ["PETROLEUM PIPING", "HSE RISK MANAGEMENT", "GIS MAINTENANCE"],
                    "specialization_tags": ["HSE Certified"],
                    "industry_remarks": "Strong Domain Match. Candidate possesses 4.0 years of experience in Oil & Gas with matching industry-specific skills (PETROLEUM PIPING)."
                }
            },
            {
                "fileName": "David_Miller_IT_CV.pdf",
                "fileSize": 105600,
                "parsedData": {
                    "full_name": "David Miller",
                    "email": "david.miller.dev@gmail.com",
                    "phone": "+1 (555) 321-4567",
                    "total_experience_years": 6.0,
                    "relevant_experience_years": 0.9,
                    "match_score": 26,
                    "skills_matrix": ["REACT", "TYPESCRIPT", "JAVASCRIPT", "PYTHON", "SQL", "GIT"],
                    "specialization_tags": [],
                    "industry_remarks": "Domain Mismatch Penalty. Candidate has 6.0 years of overall experience, but their footprint is heavily concentrated in the Information Technology industry (keyword density: 12). They lack the necessary specialized domain experience in Oil & Gas."
                }
            }
        ]
    elif target_domain == 'Railway':
        return [
            {
                "fileName": "Alistair_Vance_Resume.pdf",
                "fileSize": 151200,
                "parsedData": {
                    "full_name": "Alistair Vance",
                    "email": "a.vance@transitsystems.net",
                    "phone": "+44 20 7946 0192",
                    "total_experience_years": 9.0,
                    "relevant_experience_years": 9.0,
                    "match_score": 92,
                    "skills_matrix": ["SIGNALING SYSTEMS", "ROLLING STOCK MAINTENANCE", "SCADA CONTROL", "PROJECT MANAGEMENT"],
                    "specialization_tags": ["CBTC Systems", "PLC/SCADA Developer"],
                    "industry_remarks": "Strong Domain Match. Candidate possesses 9.0 years of experience in Railway with matching industry-specific skills (SIGNALING SYSTEMS, ROLLING STOCK MAINTENANCE)."
                }
            },
            {
                "fileName": "Elena_Rostova_CV.docx",
                "fileSize": 91200,
                "parsedData": {
                    "full_name": "Elena Rostova",
                    "email": "e.rostova@railwayinfra.com",
                    "phone": "+7 912 345 6789",
                    "total_experience_years": 3.0,
                    "relevant_experience_years": 3.0,
                    "match_score": 52,
                    "skills_matrix": ["ROLLING STOCK MAINTENANCE", "AUTOCAD", "PROJECT MANAGEMENT"],
                    "specialization_tags": [],
                    "industry_remarks": "Strong Domain Match. Candidate possesses 3.0 years of experience in Railway with matching industry-specific skills (ROLLING STOCK MAINTENANCE)."
                }
            },
            {
                "fileName": "David_Miller_IT_CV.pdf",
                "fileSize": 105600,
                "parsedData": {
                    "full_name": "David Miller",
                    "email": "david.miller.dev@gmail.com",
                    "phone": "+1 (555) 321-4567",
                    "total_experience_years": 6.0,
                    "relevant_experience_years": 0.9,
                    "match_score": 28,
                    "skills_matrix": ["REACT", "TYPESCRIPT", "JAVASCRIPT", "PYTHON", "SQL", "GIT"],
                    "specialization_tags": [],
                    "industry_remarks": "Domain Mismatch Penalty. Candidate has 6.0 years of overall experience, but their footprint is heavily concentrated in the Information Technology industry (keyword density: 12). They lack the necessary specialized domain experience in Railway."
                }
            }
        ]
    elif target_domain == 'Electrical/Testing':
        return [
            {
                "fileName": "Marcus_Vance_CV.pdf",
                "fileSize": 164000,
                "parsedData": {
                    "full_name": "Marcus Vance",
                    "email": "marcus.vance@powergrid.com",
                    "phone": "+1 (555) 234-5678",
                    "total_experience_years": 12.0,
                    "relevant_experience_years": 12.0,
                    "match_score": 95,
                    "skills_matrix": ["HIGH VOLTAGE RELAY", "GIS MAINTENANCE", "SWITCHGEAR TESTING", "SCADA CONTROL"],
                    "specialization_tags": ["380KV", "765KV", "ETAP Certified", "PLC/SCADA Developer"],
                    "industry_remarks": "Strong Domain Match. Candidate possesses 12.0 years of experience in Electrical/Testing with matching industry-specific skills (HIGH VOLTAGE RELAY, GIS MAINTENANCE)."
                }
            },
            {
                "fileName": "Ravi_Kumar_Resume.docx",
                "fileSize": 95000,
                "parsedData": {
                    "full_name": "Ravi Kumar",
                    "email": "ravi.kumar@testlabs.in",
                    "phone": "+91 98765 43210",
                    "total_experience_years": 4.0,
                    "relevant_experience_years": 4.0,
                    "match_score": 62,
                    "skills_matrix": ["SWITCHGEAR TESTING", "SCADA CONTROL", "AUTOCAD"],
                    "specialization_tags": ["ETAP Certified"],
                    "industry_remarks": "Strong Domain Match. Candidate possesses 4.0 years of experience in Electrical/Testing with matching industry-specific skills (SWITCHGEAR TESTING)."
                }
            },
            {
                "fileName": "David_Miller_IT_CV.pdf",
                "fileSize": 105600,
                "parsedData": {
                    "full_name": "David Miller",
                    "email": "david.miller.dev@gmail.com",
                    "phone": "+1 (555) 321-4567",
                    "total_experience_years": 6.0,
                    "relevant_experience_years": 0.9,
                    "match_score": 27,
                    "skills_matrix": ["REACT", "TYPESCRIPT", "JAVASCRIPT", "PYTHON", "SQL", "GIT"],
                    "specialization_tags": [],
                    "industry_remarks": "Domain Mismatch Penalty. Candidate has 6.0 years of overall experience, but their footprint is heavily concentrated in the Information Technology industry (keyword density: 12). They lack the necessary specialized domain experience in Electrical/Testing."
                }
            }
        ]
    elif target_domain == 'Healthcare':
        return [
            {
                "fileName": "Emily_Taylor_CV.pdf",
                "fileSize": 139000,
                "parsedData": {
                    "full_name": "Dr. Emily Taylor",
                    "email": "emily.taylor@clinicalresearch.org",
                    "phone": "+1 (555) 345-6789",
                    "total_experience_years": 11.0,
                    "relevant_experience_years": 11.0,
                    "match_score": 90,
                    "skills_matrix": ["CLINICAL TRIALS", "NURSING CARE", "PROJECT MANAGEMENT"],
                    "specialization_tags": ["HSE Certified"],
                    "industry_remarks": "Strong Domain Match. Candidate possesses 11.0 years of experience in Healthcare with matching industry-specific skills (CLINICAL TRIALS, NURSING CARE)."
                }
            },
            {
                "fileName": "James_Wilson_Resume.docx",
                "fileSize": 82000,
                "parsedData": {
                    "full_name": "James Wilson",
                    "email": "j.wilson@healthcare.net",
                    "phone": "+1 (555) 456-7890",
                    "total_experience_years": 5.0,
                    "relevant_experience_years": 5.0,
                    "match_score": 60,
                    "skills_matrix": ["NURSING CARE", "PROJECT MANAGEMENT"],
                    "specialization_tags": [],
                    "industry_remarks": "Strong Domain Match. Candidate possesses 5.0 years of experience in Healthcare with matching industry-specific skills (NURSING CARE)."
                }
            },
            {
                "fileName": "David_Miller_IT_CV.pdf",
                "fileSize": 105600,
                "parsedData": {
                    "full_name": "David Miller",
                    "email": "david.miller.dev@gmail.com",
                    "phone": "+1 (555) 321-4567",
                    "total_experience_years": 6.0,
                    "relevant_experience_years": 0.9,
                    "match_score": 25,
                    "skills_matrix": ["REACT", "TYPESCRIPT", "JAVASCRIPT", "PYTHON", "SQL", "GIT"],
                    "specialization_tags": [],
                    "industry_remarks": "Domain Mismatch Penalty. Candidate has 6.0 years of overall experience, but their footprint is heavily concentrated in the Information Technology industry (keyword density: 12). They lack the necessary specialized domain experience in Healthcare."
                }
            }
        ]
    else: # Information Technology
        return [
            {
                "fileName": "Alex_Rivera_CV.pdf",
                "fileSize": 112000,
                "parsedData": {
                    "full_name": "Alex Rivera",
                    "email": "alex.rivera@devopsmail.com",
                    "phone": "+1 (555) 789-0123",
                    "total_experience_years": 8.0,
                    "relevant_experience_years": 8.0,
                    "match_score": 94,
                    "skills_matrix": ["REACT", "TYPESCRIPT", "JAVASCRIPT", "PYTHON", "GIT", "DOCKER", "AWS"],
                    "specialization_tags": ["PLC/SCADA Developer"],
                    "industry_remarks": "Strong Domain Match. Candidate possesses 8.0 years of experience in Information Technology with matching industry-specific skills (REACT, TYPESCRIPT, JAVASCRIPT, PYTHON)."
                }
            },
            {
                "fileName": "Priyanka_Patel_Resume.docx",
                "fileSize": 85000,
                "parsedData": {
                    "full_name": "Priyanka Patel",
                    "email": "priyanka.p@codesolution.in",
                    "phone": "+91 99887 76655",
                    "total_experience_years": 4.0,
                    "relevant_experience_years": 4.0,
                    "match_score": 68,
                    "skills_matrix": ["PYTHON", "SQL", "GIT", "REACT"],
                    "specialization_tags": [],
                    "industry_remarks": "Strong Domain Match. Candidate possesses 4.0 years of experience in Information Technology with matching industry-specific skills (PYTHON, SQL)."
                }
            },
            {
                "fileName": "David_Miller_Oil_Gas_CV.pdf",
                "fileSize": 121000,
                "parsedData": {
                    "full_name": "David Miller",
                    "email": "david.miller.eng@gmail.com",
                    "phone": "+1 (555) 321-4567",
                    "total_experience_years": 10.0,
                    "relevant_experience_years": 1.5,
                    "match_score": 31,
                    "skills_matrix": ["PETROLEUM PIPING", "DRILLING SIMULATION", "HSE RISK MANAGEMENT", "PROJECT MANAGEMENT"],
                    "specialization_tags": ["Deepwater Drilling", "HSE Certified"],
                    "industry_remarks": "Domain Mismatch Penalty. Candidate has 10.0 years of overall experience, but their footprint is heavily concentrated in the Oil & Gas industry (keyword density: 10). They lack the necessary specialized domain experience in Information Technology."
                }
            }
        ]

@app.route('/api/v1/gdrive-import', methods=['POST'])
def gdrive_import():
    data = request.get_json()
    if not data or 'folder_url' not in data or 'target_domain' not in data or 'requisition_id' not in data:
        return jsonify({"error": "Missing parameters 'folder_url', 'target_domain', or 'requisition_id'"}), 400
        
    folder_url = data['folder_url'].strip()
    target_domain = data['target_domain']
    requisition_id = data['requisition_id']
    
    # Check for dummy or test folder URLs/IDs
    is_dummy = (
        folder_url == "test" or 
        folder_url == "mock" or 
        "1_A2B3C4D5" in folder_url or 
        "1_A2B3C4D5E6F7G8H9I0J" in folder_url
    )
    if is_dummy:
        print(f"Intercepted dummy Google Drive folder URL. Returning high-fidelity mock candidates for domain: {target_domain}")
        mock_candidates = get_mock_candidates_for_domain(target_domain)
        return jsonify({
            "success": True,
            "count": len(mock_candidates),
            "candidates": mock_candidates
        })
        
    try:
        import gdown
    except ImportError:
        return jsonify({"error": "Google Drive download utility 'gdown' is not installed on the server. Please run: pip install gdown"}), 500
        
    temp_dir = tempfile.mkdtemp()
    try:
        print(f"Downloading Google Drive folder URL: {folder_url}")
        
        # Download public folder contents
        downloaded_paths = gdown.download_folder(url=folder_url, output=temp_dir, quiet=True, use_cookies=False)
        
        if not downloaded_paths:
            downloaded_paths = []
            for root, dirs, files in os.walk(temp_dir):
                for f in files:
                    downloaded_paths.append(os.path.join(root, f))
        
        supported_extensions = ['.pdf', '.docx', '.doc', '.txt']
        candidates = []
        
        files_found = []
        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in supported_extensions:
                    files_found.append(os.path.join(root, file))
                    
        if not files_found:
            return jsonify({
                "error": "No supported files (.pdf, .docx, .doc, .txt) found in the Google Drive folder. Ensure the folder is public and contains resumes.",
                "details": f"Checked temp directory. Total files found: {len(downloaded_paths)}"
            }), 400
            
        for file_path in files_found:
            file_name = os.path.basename(file_path)
            file_size = os.path.getsize(file_path)
            
            raw_text = extract_text_from_file(file_path)
            scored_data = score_candidate_data(raw_text, target_domain)
            
            candidates.append({
                "fileName": file_name,
                "fileSize": file_size,
                "parsedData": scored_data
            })
            
        return jsonify({
            "success": True,
            "count": len(candidates),
            "candidates": candidates
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Failed to download or parse Google Drive folder: {str(e)}"}), 500
        
    finally:
        try:
            shutil.rmtree(temp_dir, ignore_errors=True)
        except Exception:
            pass


if __name__ == '__main__':
    # Run server locally on standard port 5000
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)
