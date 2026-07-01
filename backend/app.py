from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import re
import os
import tempfile
import shutil
import uuid

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

# Directory where uploaded CV files are permanently stored
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
SUPPORTED_EXTENSIONS = {'.pdf', '.docx', '.doc', '.txt'}

# 1. Domain Taxonomy — 7 Business Verticals
DOMAIN_TAXONOMY = {
    'Oil & Gas': [
        'mechanical engineering', 'chemical engineering', 'petroleum engineering',
        'instrumentation engineering', 'electrical engineering', 'civil engineering',
        'process engineering', 'industrial engineering', 'production engineering',
        'diploma mechanical', 'diploma electrical', 'diploma instrumentation',
        'diploma civil', 'process technology', 'commissioning engineer',
        'qa/qc engineer', 'pipeline engineer', 'welding inspector',
        'ndt inspector', 'safety officer', 'hse engineer', 'instrument engineer',
        'rotating equipment engineer', 'static equipment engineer',
        'maintenance engineer', 'shutdown engineer', 'oil', 'gas', 'petroleum'
    ],
    'Petrochemical': [
        'chemical engineering', 'mechanical engineering', 'instrumentation',
        'electrical', 'polymer engineering', 'process engineer', 'production engineer',
        'plant engineer', 'maintenance engineer', 'operations engineer',
        'process safety engineer', 'petrochemical', 'chemical plant',
        'distillation', 'cracking', 'feedstock'
    ],
    'Construction & Infrastructure': [
        'civil engineering', 'structural engineering', 'architecture',
        'mechanical', 'electrical', 'quantity surveying', 'rics', 'site engineer',
        'planning engineer', 'quantity surveyor', 'project engineer', 'project manager',
        'qa/qc engineer', 'construction manager', 'civil', 'mep', 'construction',
        'structural'
    ],
    'Energy': [
        'electrical engineering', 'mechanical engineering', 'renewable energy engineering',
        'power systems', 'electronics engineering', 'iec standards', 'solar pv design',
        'wind turbine maintenance', 'electrical engineer', 'grid engineer',
        'power systems engineer', 'protection engineer', 'solar engineer', 'wind engineer',
        'renewable', 'solar', 'wind', 'grid', 'energy'
    ],
    'Hospitality': [
        'hotel management', 'hospitality management', 'culinary arts', 'tourism',
        'business administration', 'ahlei', 'wset', 'barista certification',
        'hotel manager', 'front office manager', 'executive chef', 'sous chef',
        'housekeeping manager', 'restaurant manager', 'guest relations', 'hotel',
        'resort', 'barista', 'f&b', 'housekeeping', 'restaurant'
    ],
    'Facilities Management': [
        'mechanical engineering', 'electrical engineering', 'hvac', 'facility management',
        'civil engineering', 'ifma cfm', 'fmp', 'leed', 'bms', 'hvac certification',
        'facility manager', 'maintenance manager', 'hvac engineer', 'mep engineer',
        'building engineer', 'facilities', 'building maintenance', 'property management',
        'fm'
    ],
    'Maritime & Shipping': [
        'marine engineering', 'naval architecture', 'nautical science',
        'mechanical engineering', 'stcw', 'coc class i-iv', 'gmdss', 'dp operator',
        'ism', 'isps', 'marpol', 'tanker endorsement', 'marine engineer',
        'chief engineer', 'second engineer', 'deck officer', 'captain', 'port engineer',
        'technical superintendent', 'maritime', 'shipping', 'vessel', 'marine', 'port',
        'seafarer'
    ],
    'Power Plants': [
        'mechanical', 'electrical', 'instrumentation', 'chemical', 'power engineering',
        'boiler operator', 'turbine maintenance', 'shift engineer', 'operations engineer',
        'turbine engineer', 'boiler engineer', 'maintenance engineer', 'plant manager',
        'power plant', 'turbine', 'boiler', 'generator', 'dcs', 'commissioning'
    ],
    'Engineering Services': [
        'any engineering discipline', 'industrial engineering', 'mechatronics',
        'electronics', 'design engineer', 'project engineer', 'application engineer',
        'sales engineer', 'service engineer'
    ],
    'Manufacturing': [
        'mechanical', 'industrial', 'production', 'mechatronics', 'manufacturing engineering',
        'tpm', 'kaizen', 'cqe', 'cqa', 'production engineer', 'manufacturing engineer',
        'process engineer', 'quality engineer', 'plant manager', 'manufacturing',
        'six sigma', 'lean'
    ],
    'EPC': [
        'mechanical', 'civil', 'electrical', 'instrumentation', 'chemical',
        'epc engineer', 'project engineer', 'procurement engineer', 'construction engineer',
        'planning engineer', 'commissioning engineer', 'qa/qc engineer', 'epc',
        'procurement', 'engineering procurement'
    ]
}

# Specialization Tags
SPECIALIZATION_POOL = [
    'NEBOSH', 'IOSH', 'OSHA 10', 'OSHA 30', 'H2S Alive', 'BOSIET', 'HUET', 'OPITO',
    'CSWIP 3.1', 'CSWIP 3.2', 'AWS CWI', 'API 510', 'API 570', 'API 653',
    'ASNT Level II', 'NACE CIP', 'BGAS', 'PMP', 'Primavera P6', 'AutoCAD', 'PDMS',
    'SP3D', 'SmartPlant', 'ISO 9001 Lead Auditor', 'ISO 45001 Lead Auditor',
    'Six Sigma', 'Lean Manufacturing', 'HAZOP', 'SIL', 'Functional Safety',
    'STAAD Pro', 'ETABS', 'Revit', 'BIM', 'OSHA', 'Quantity Surveying', 'RICS',
    'ISO 9001', 'ETAP', 'SCADA', 'PLC', 'AutoCAD Electrical', 'IEC Standards',
    'Solar PV Design', 'Wind Turbine Maintenance', 'HACCP', 'Food Safety', 'ServSafe',
    'AHLEI', 'WSET', 'Barista Certification', 'IFMA CFM', 'FMP', 'LEED', 'BMS',
    'HVAC Certification', 'STCW', 'COC Class I-IV', 'GMDSS', 'DP Operator', 'ISM',
    'ISPS', 'MARPOL', 'Tanker Endorsement', 'Boiler Operator', 'Turbine Maintenance',
    'DCS', 'SolidWorks', 'CATIA', 'ANSYS', 'MATLAB', 'Six Sigma Green Belt',
    'Six Sigma Black Belt', 'TPM', 'Kaizen', 'CQE', 'CQA', 'AWS'
]

# Skills pool for CV extraction
SKILLS_POOL = [
    'PETROLEUM PIPING', 'DRILLING SIMULATION', 'HSE RISK MANAGEMENT',
    'WELL LOGGING', 'SEISMIC ANALYSIS', 'WELLHEAD OPERATIONS', 'PIPELINE INTEGRITY',
    'PROCESS ENGINEERING', 'CHEMICAL ANALYSIS', 'DISTILLATION OPERATIONS',
    'PLANT OPERATIONS', 'CATALYST MANAGEMENT', 'PROCESS SAFETY',
    'CIVIL ENGINEERING', 'MEP SYSTEMS', 'QUANTITY SURVEYING',
    'STRUCTURAL DESIGN', 'AUTOCAD', 'SITE MANAGEMENT', 'PRIMAVERA P6',
    'HVAC SYSTEMS', 'FACILITIES MANAGEMENT', 'BUILDING MAINTENANCE',
    'ENERGY AUDITING', 'PROPERTY MANAGEMENT', 'PREVENTIVE MAINTENANCE',
    'SHIP OPERATIONS', 'MARINE ENGINEERING', 'PORT LOGISTICS',
    'CARGO HANDLING', 'VESSEL MAINTENANCE', 'MARITIME SAFETY',
    'POWER GENERATION', 'TURBINE MAINTENANCE', 'DCS CONTROL',
    'INSTRUMENTATION', 'BOILER OPERATIONS', 'ELECTRICAL SYSTEMS',
    'CUSTOMER SERVICE', 'F&B OPERATIONS', 'BARISTA SKILLS',
    'HOTEL MANAGEMENT', 'HOUSEKEEPING', 'FOOD SAFETY', 'GUEST RELATIONS',
    'QUALITY ASSURANCE', 'QUALITY CONTROL', 'PROJECT MANAGEMENT', 'LNG OPERATIONS'
]

# Section-header words that are NOT candidate names — blocklist for name parser
NAME_BLOCKLIST = {
    'CONTACT ME', 'CONTACT', 'CONTACTS', 'RESUME', 'CV', 'CURRICULUM VITAE',
    'CURRICULUM', 'VITAE', 'PROFILE', 'PERSONAL DETAILS', 'PERSONAL INFORMATION',
    'PERSONAL PROFILE', 'ABOUT ME', 'OBJECTIVE', 'SUMMARY', 'CAREER SUMMARY',
    'CAREER OBJECTIVE', 'PROFESSIONAL SUMMARY', 'INTRODUCTION', 'BIO', 'BIOGRAPHY',
    'NAME', 'FULL NAME', 'CANDIDATE', 'APPLICANT'
}

# Job titles and placeholder template words that should never be extracted as a candidate's name
TITLE_GENERIC_KEYWORDS = {
    'ENGINEER', 'DEVELOPER', 'MANAGER', 'ANALYST', 'DESIGNER', 'OFFICER', 
    'TECHNICIAN', 'OPERATOR', 'DIRECTOR', 'SUPERVISOR', 'FOREMAN', 'INSPECTOR', 
    'SPECIALIST', 'CONSULTANT', 'CHIEF', 'ADMINISTRATOR', 'LEAD', 'COORDINATOR', 
    'ARCHITECT', 'SURNAME', 'FORENAME', 'FIRSTNAME', 'LASTNAME', 'MIDDLE',
    'RESUME', 'CV', 'CURRICULUM', 'VITAE', 'CONTACT', 'PROFILE', 'OBJECTIVE',
    'SUMMARY', 'EDUCATION', 'EXPERIENCE', 'SKILLS', 'PROJECTS', 'CERTIFICATIONS',
    'ADDITIONAL', 'INFORMATION', 'DETAILS', 'LANGUAGES', 'HOBBIES', 'INTERESTS',
    'PERSONAL', 'WORK', 'HISTORY', 'EMPLOYMENT', 'CAREER', 'QUALIFICATIONS'
}

def extract_contacts(text, file_hint=''):
    """Scan and parse candidate basic info using regular expressions.
    
    file_hint: the original uploaded filename (without extension) used as a
               last-resort name fallback when the CV text does not yield a
               clean candidate name.
    """
    email_regex = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    phone_regex = r'(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
    
    email_match = re.search(email_regex, text)
    phone_match = re.search(phone_regex, text)
    
    email = email_match.group(0) if email_match else "N/A"
    phone = phone_match.group(0) if phone_match else "N/A"
    
    # Try to parse candidate name from the first 8 non-empty lines.
    # Rules:
    #   - 2 to 5 words (allow titles like "Dr. John Smith")
    #   - No digits
    #   - No email @
    #   - Not a known section-header word (blocklist)
    #   - Does not contain common job titles or placeholder keywords
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    full_name = None
    for line in lines[:8]:
        words = line.split()
        if not (2 <= len(words) <= 5):
            continue
        if re.search(r'\d', line):
            continue
        if '@' in line:
            continue
        # Reject lines that are entirely punctuation / symbols
        if re.fullmatch(r'[^\w\s]+', line):
            continue
        # Reject known section headers (case-insensitive exact match)
        if line.upper().strip() in NAME_BLOCKLIST:
            continue
        # Reject lines containing any forbidden job title or generic placeholder keywords
        words_cleaned = [re.sub(r'[^\w]', '', w.upper()) for w in words]
        if any(w in TITLE_GENERIC_KEYWORDS for w in words_cleaned):
            continue
        # Accept: looks like a proper name
        full_name = line
        break

    # Fallback 1: derive name from the uploaded filename
    # e.g. "John_Smith_CV.pdf" -> "John Smith"
    if full_name is None and file_hint:
        stem = os.path.splitext(file_hint)[0]          # strip extension if present
        stem = re.sub(r'(?i)(_cv|_resume|_application|\d{4,}).*$', '', stem)
        stem = re.sub(r'[_\-]+', ' ', stem).strip()
        stem_words = stem.split()
        # Clean any generic/title words from the filename as well
        stem_words_cleaned = [re.sub(r'[^\w]', '', w.upper()) for w in stem_words]
        if 2 <= len(stem_words) <= 5 and not re.search(r'\d', stem) and not any(w in TITLE_GENERIC_KEYWORDS for w in stem_words_cleaned):
            full_name = stem.title()

    # Fallback 2: generic placeholder
    if full_name is None:
        full_name = "Unknown Candidate"
            
    return full_name, email, phone

def parse_experience_years(text):
    """Estimate total experience years from textual descriptions"""
    text_lower = text.lower()
    
    # 1. Search for explicit "total", "overall", or "work" experience patterns
    explicit_patterns = [
        r'(?:total|overall|work|professional|industry)\s+experience\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*(?:years?|yrs?)',
        r'(\d+(?:\.\d+)?)\s*(?:years?|yrs?)\s+(?:of\s+)?(?:total|overall|work|professional|industry)?\s*experience',
        r'experience\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*(?:years?|yrs?)',
    ]
    for pattern in explicit_patterns:
        match = re.search(pattern, text_lower)
        if match:
            try:
                val = float(match.group(1))
                if 0 < val < 50:
                    return val
            except ValueError:
                pass

    # 2. Search for any pattern of "N years" or "N yrs"
    all_yr_matches = re.findall(r'\b(\d{1,2})\+?\s*(?:years?|yrs?)\b', text_lower)
    if all_yr_matches:
        try:
            vals = [float(x) for x in all_yr_matches]
            valid_vals = [v for v in vals if 0 < v < 50]
            if valid_vals:
                # The maximum years value usually represents total experience
                return max(valid_vals)
        except ValueError:
            pass

    # 3. Date-range heuristic (e.g. 2018 - present)
    years = re.findall(r'\b(20[0-2][0-9]|19[8-9][0-9])\b', text_lower)
    if years:
        try:
            year_vals = [int(y) for y in years]
            min_year = min(year_vals)
            max_year = max(year_vals)
            if "present" in text_lower or "current" in text_lower:
                max_year = max(max_year, 2026)
            diff = max_year - min_year
            if 0 < diff < 45:
                return float(diff)
        except Exception:
            pass
            
    # Default fallback
    return 7.0

# Domains considered "adjacent heavy industry" — these share significant
# skillset overlap with engineering-heavy targets (e.g. commissioning, testing,
# instrumentation) and should receive a PARTIAL match rather than a full penalty.
ADJACENT_DOMAIN_MAP = {
    # target_domain -> set of candidate domains treated as partial match
    'Oil & Gas':                  {'Power Plants', 'EPC', 'Petrochemical', 'Manufacturing', 'Energy', 'Engineering Services'},
    'Petrochemical':              {'Oil & Gas', 'Power Plants', 'EPC', 'Manufacturing', 'Energy'},
    'Power Plants':               {'Oil & Gas', 'EPC', 'Energy', 'Petrochemical', 'Manufacturing', 'Engineering Services'},
    'EPC':                        {'Oil & Gas', 'Power Plants', 'Petrochemical', 'Construction & Infrastructure', 'Manufacturing'},
    'Energy':                     {'Power Plants', 'Oil & Gas', 'EPC', 'Petrochemical', 'Facilities Management'},
    'Construction & Infrastructure': {'EPC', 'Facilities Management', 'Engineering Services', 'Manufacturing'},
    'Facilities Management':      {'Construction & Infrastructure', 'Energy', 'Engineering Services', 'Manufacturing'},
    'Manufacturing':              {'EPC', 'Engineering Services', 'Power Plants', 'Oil & Gas'},
    'Engineering Services':       {'Manufacturing', 'EPC', 'Power Plants', 'Construction & Infrastructure'},
    'Maritime & Shipping':        {'Engineering Services', 'Oil & Gas'},
}

def score_candidate_data(candidate_text, target_domain, file_hint=''):
    """Screen a candidate CV against a target domain.
    
    Parameters
    ----------
    candidate_text : str   Raw text extracted from the CV file.
    target_domain  : str   The hiring domain selected by the recruiter.
    file_hint      : str   Original uploaded filename used as name-parsing fallback.
    """
    # Extract candidate metadata
    full_name, email, phone = extract_contacts(candidate_text, file_hint=file_hint)
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
            matches = re.findall(rf'\b{re.escape(kw)}\b', text_lower)
            count += len(matches)
        domain_scores[domain] = count

    # Determine candidate's primary domain by keyword frequency
    candidate_domain = max(domain_scores, key=domain_scores.get)
    max_count = domain_scores[candidate_domain]

    # Determine match tier
    is_exact_match   = (candidate_domain == target_domain)
    adjacent_domains = ADJACENT_DOMAIN_MAP.get(target_domain, set())
    is_adjacent_match = (not is_exact_match) and (candidate_domain in adjacent_domains)

    # ── Matching Logic ────────────────────────────────────────────────────────
    relevant_exp = total_exp
    match_score  = 50  # default base

    if is_exact_match or max_count < 2:
        # ── TIER 1: Exact domain match (or too few keywords to penalise) ──
        skill_factor = min(40, len(skills_matrix) * 8)
        exp_factor   = min(40, total_exp * 5)        # 5 pts/yr, caps at 40
        spec_factor  = min(20, len(specialization_tags) * 10)
        match_score  = int(skill_factor + exp_factor + spec_factor)
        match_score  = max(10, min(100, match_score))

        if skills_matrix:
            remarks = (
                f"Strong Domain Match. Candidate possesses {relevant_exp:.1f} years of experience "
                f"in {target_domain} with matching industry-specific skills "
                f"({', '.join(skills_matrix[:4])})."
            )
        else:
            remarks = (
                f"Domain Match. Candidate has {relevant_exp:.1f} years of experience in "
                f"{target_domain}. No specific skills detected from CV text."
            )

    elif is_adjacent_match:
        # ── TIER 2: Adjacent / closely related heavy-industry domain ──
        # These candidates bring transferable technical skills (commissioning,
        # instrumentation, maintenance) that are highly relevant even though
        # the sector label differs.
        skill_factor   = min(35, len(skills_matrix) * 7)
        exp_factor     = min(30, total_exp * 4)      # still rewards experience
        spec_factor    = min(15, len(specialization_tags) * 8)
        adjacency_base = 20                           # partial-match base credit
        match_score    = int(adjacency_base + skill_factor + exp_factor + spec_factor)
        match_score    = max(42, min(80, match_score))  # floor 42%, ceiling 80%

        # Relevant exp: credit 60% of total for adjacent domain
        relevant_exp   = round(total_exp * 0.60, 1)

        remarks = (
            f"Adjacent Domain Match. Candidate has {total_exp:.1f} years of experience in "
            f"{candidate_domain}, which shares substantial technical overlap with {target_domain} "
            f"(commissioning, instrumentation, maintenance engineering). "
            f"Estimated {relevant_exp:.1f} years of transferable relevant experience. "
            f"Matched skills: {', '.join(skills_matrix[:4]) if skills_matrix else 'General Technical'}."
        )

    else:
        # ── TIER 3: True domain mismatch (e.g. Hospitality vs Oil & Gas) ──
        # Apply a meaningful penalty, but still credit strong total experience
        # with a floor so scores don't irrationally plunge below ~38%.
        exp_floor     = min(18, total_exp * 2.0)    # up to 18 pts from raw exp
        skill_bonus   = min(10, len(skills_matrix) * 2)  # small transferable bonus
        mismatch_base = 20
        match_score   = int(mismatch_base + exp_floor + skill_bonus)
        match_score   = max(20, min(48, match_score))  # hard cap 20–48%

        relevant_exp  = round(total_exp * 0.15, 1)

        remarks = (
            f"Domain Mismatch. Candidate has {total_exp:.1f} years of experience, but their "
            f"background is concentrated in {candidate_domain} (keyword density: {max_count}). "
            f"This does not align well with the required {target_domain} domain expertise."
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
    target_domain  = data['target_domain']
    file_hint      = data.get('file_hint', '')   # optional filename fallback for name parsing
    
    response_payload = score_candidate_data(candidate_text, target_domain, file_hint=file_hint)
    return jsonify(response_payload)


# -- Aliases for Magic Search query parsing --
SKILL_ALIASES = {
    'hse': 'HSE RISK MANAGEMENT', 'safety': 'HSE RISK MANAGEMENT', 'ehs': 'HSE RISK MANAGEMENT',
    'qaqc': 'QUALITY ASSURANCE', 'qa/qc': 'QUALITY ASSURANCE', 'qa': 'QUALITY ASSURANCE', 'qc': 'QUALITY CONTROL',
    'ndt': 'WELL LOGGING', 'non destructive testing': 'WELL LOGGING',
    'p6': 'PRIMAVERA P6', 'primavera': 'PRIMAVERA P6',
    'plc': 'DCS CONTROL', 'dcs': 'DCS CONTROL', 'programmable logic controller': 'DCS CONTROL', 'distributed control system': 'DCS CONTROL',
    'mep': 'MEP SYSTEMS', 'mechanical electrical plumbing': 'MEP SYSTEMS',
    'hvac': 'HVAC SYSTEMS', 'heating ventilation air conditioning': 'HVAC SYSTEMS',
    'pm': 'PROJECT MANAGEMENT', 'pmo': 'PROJECT MANAGEMENT', 'project management office': 'PROJECT MANAGEMENT',
    'epc': 'CIVIL ENGINEERING', 'engineering procurement construction': 'CIVIL ENGINEERING',
    'lng': 'LNG OPERATIONS', 'liquefied natural gas': 'LNG OPERATIONS', 'lpg': 'LNG OPERATIONS', 'cng': 'LNG OPERATIONS',
    'b.tech': 'CIVIL ENGINEERING', 'bachelor of technology': 'CIVIL ENGINEERING',
    'b.e.': 'CIVIL ENGINEERING', 'bachelor of engineering': 'CIVIL ENGINEERING',
    'diploma': 'CIVIL ENGINEERING', 'polytechnic diploma': 'CIVIL ENGINEERING',
    
    # Original aliases that are still useful
    'petroleum': 'PETROLEUM PIPING', 'pipeline': 'PETROLEUM PIPING', 'piping': 'PETROLEUM PIPING',
    'drilling': 'DRILLING SIMULATION',
    'wellhead': 'WELLHEAD OPERATIONS', 'pipeline integrity': 'PIPELINE INTEGRITY',
    'process engineering': 'PROCESS ENGINEERING', 'process engineer': 'PROCESS ENGINEERING',
    'chemical analysis': 'CHEMICAL ANALYSIS',
    'distillation': 'DISTILLATION OPERATIONS',
    'plant operations': 'PLANT OPERATIONS',
    'catalyst': 'CATALYST MANAGEMENT',
    'process safety': 'PROCESS SAFETY',
    'civil engineering': 'CIVIL ENGINEERING', 'structural': 'STRUCTURAL DESIGN',
    'quantity surveying': 'QUANTITY SURVEYING', 'qs': 'QUANTITY SURVEYING',
    'autocad': 'AUTOCAD', 'cad': 'AUTOCAD',
    'site management': 'SITE MANAGEMENT',
    'chiller': 'HVAC SYSTEMS',
    'facilities management': 'FACILITIES MANAGEMENT', 'fm': 'FACILITIES MANAGEMENT',
    'building maintenance': 'BUILDING MAINTENANCE',
    'energy auditing': 'ENERGY AUDITING',
    'property management': 'PROPERTY MANAGEMENT',
    'preventive maintenance': 'PREVENTIVE MAINTENANCE', 'ppm': 'PREVENTIVE MAINTENANCE',
    'ship operations': 'SHIP OPERATIONS',
    'marine engineering': 'MARINE ENGINEERING',
    'port logistics': 'PORT LOGISTICS',
    'cargo handling': 'CARGO HANDLING',
    'maritime safety': 'MARITIME SAFETY', 'stcw': 'MARITIME SAFETY',
    'power generation': 'POWER GENERATION', 'power plant': 'POWER GENERATION',
    'turbine': 'TURBINE MAINTENANCE', 'gas turbine': 'TURBINE MAINTENANCE',
    'scada': 'DCS CONTROL',
    'instrumentation': 'INSTRUMENTATION',
    'boiler': 'BOILER OPERATIONS',
    'customer service': 'CUSTOMER SERVICE',
    'food and beverage': 'F&B OPERATIONS', 'f&b': 'F&B OPERATIONS',
    'barista': 'BARISTA SKILLS', 'coffee': 'BARISTA SKILLS',
    'hotel management': 'HOTEL MANAGEMENT',
    'housekeeping': 'HOUSEKEEPING',
    'food safety': 'FOOD SAFETY',
    'guest relations': 'GUEST RELATIONS',
}

DOMAIN_ALIASES = {
    'oil': 'Oil & Gas', 'gas': 'Oil & Gas', 'petroleum': 'Oil & Gas',
    'offshore': 'Oil & Gas', 'refinery': 'Oil & Gas', 'hydrocarbon': 'Oil & Gas',
    'upstream': 'Oil & Gas', 'downstream': 'Oil & Gas', 'lng': 'Oil & Gas',
    'petrochemical': 'Petrochemical', 'chemical plant': 'Petrochemical',
    'cracking': 'Petrochemical', 'feedstock': 'Petrochemical',
    'construction': 'Construction & Infrastructure', 'civil': 'Construction & Infrastructure',
    'infrastructure': 'Construction & Infrastructure', 'mep': 'Construction & Infrastructure',
    'energy': 'Energy', 'renewable': 'Energy', 'solar': 'Energy', 'wind': 'Energy',
    'facilities': 'Facilities Management', 'hvac': 'Facilities Management',
    'building services': 'Facilities Management', 'fm': 'Facilities Management',
    'maritime': 'Maritime & Shipping', 'shipping': 'Maritime & Shipping',
    'marine': 'Maritime & Shipping', 'vessel': 'Maritime & Shipping',
    'port': 'Maritime & Shipping', 'seafarer': 'Maritime & Shipping',
    'power plant': 'Power Plants', 'turbine': 'Power Plants',
    'boiler': 'Power Plants', 'generator': 'Power Plants',
    'engineering services': 'Engineering Services', 'mechatronics': 'Engineering Services',
    'manufacturing': 'Manufacturing', 'production': 'Manufacturing', 'six sigma': 'Manufacturing',
    'epc': 'EPC', 'procurement': 'EPC',
    'hotel': 'Hospitality', 'resort': 'Hospitality', 'barista': 'Hospitality',
    'restaurant': 'Hospitality', 'catering': 'Hospitality', 'hospitality': 'Hospitality',
}

SPEC_ALIASES = {
    'hse certified': 'HSE Certified', 'hse': 'HSE Certified', 'ehs': 'HSE Certified',
    'nebosh': 'NEBOSH', 'opito': 'OPITO', 'osha': 'OSHA 30', 'osha 10': 'OSHA 10', 'osha 30': 'OSHA 30',
    'deepwater': 'Deepwater Drilling', 'deepwater drilling': 'Deepwater Drilling',
    'well logging': 'Well Logging',
    'process safety management': 'Process Safety Management', 'hazop': 'HAZOP',
    'mep engineer': 'MEP Engineer',
    'quantity surveyor': 'Quantity Surveying', 'qs': 'Quantity Surveying',
    'stcw': 'STCW', 'class 1 marine': 'COC Class I-IV',
    'deck officer': 'Deck Officer',
    'gas turbine': 'Turbine Maintenance',
    'dcs/scada': 'DCS', 'scada operator': 'SCADA',
    'power plant commissioning': 'Power Plant Commissioning',
    'hvac specialist': 'HVAC Certification',
    'facilities manager': 'IFMA CFM',
    'food safety certified': 'Food Safety',
    'hospitality management': 'Hospitality Management',
    'qaqc': 'CQE', 'qa/qc': 'CQE', 'qa': 'CQE', 'qc': 'CQA',
    'p6': 'Primavera P6', 'primavera': 'Primavera P6',
    'plc': 'PLC', 'dcs': 'DCS', 'mep': 'MEP Engineer',
    'hvac': 'HVAC Certification', 'pm': 'PMP', 'pmo': 'PMP',
    'iso 9001': 'ISO 9001', 'iso 45001': 'ISO 45001 Lead Auditor',
    'api 510': 'API 510', 'api 570': 'API 570', 'api 653': 'API 653',
    'six sigma': 'Six Sigma', 'lean': 'Lean Manufacturing',
    'bim': 'BIM', 'revit': 'Revit',
}


def parse_magic_query(query):
    """Extract intent signals from a natural-language recruiter query."""
    q = query.lower().strip()

    # Experience years
    exp_years = None
    exp_match = re.search(r'(\d+)\+?\s*(?:years?|yrs?)', q)
    if exp_match:
        exp_years = float(exp_match.group(1))

    # Skill signals (check multi-word aliases first, then single-word)
    matched_skills = set()
    sorted_aliases = sorted(SKILL_ALIASES.keys(), key=len, reverse=True)
    for alias in sorted_aliases:
        if alias in q:
            matched_skills.add(SKILL_ALIASES[alias])
    for skill in SKILLS_POOL:
        if skill.lower() in q:
            matched_skills.add(skill)

    # Domain signals
    matched_domains = set()
    for alias, canonical in DOMAIN_ALIASES.items():
        if re.search(rf'\b{re.escape(alias)}\b', q):
            matched_domains.add(canonical)

    # Specialization signals
    matched_specs = set()
    for alias, canonical in SPEC_ALIASES.items():
        if alias in q:
            matched_specs.add(canonical)

    return {'exp_years': exp_years, 'skills': list(matched_skills),
            'domains': list(matched_domains), 'specs': list(matched_specs)}


def score_relevance(candidate, signals):
    """Score a candidate against parsed query signals. Returns (score, matched_signals)."""
    score = 0
    matched = []

    # Skill matches — 30 pts each
    cand_skills = [s.upper() for s in candidate.get('skills_matrix', [])]
    for skill in signals['skills']:
        if skill.upper() in cand_skills:
            score += 30
            matched.append(skill)

    # Domain match — 25 pts (once)
    remarks = candidate.get('industry_remarks', '').lower()
    for domain in signals['domains']:
        domain_kws = DOMAIN_TAXONOMY.get(domain, [])
        if any(kw in remarks for kw in domain_kws):
            score += 25
            matched.append(domain)
            break

    # Specialization tags — 20 pts each
    cand_specs = [s.lower() for s in candidate.get('specialization_tags', [])]
    for spec in signals['specs']:
        if spec.lower() in cand_specs:
            score += 20
            matched.append(spec)

    # Experience proximity — up to 15 pts
    if signals['exp_years'] is not None:
        cand_exp = float(candidate.get('total_experience_years', 0))
        diff = abs(cand_exp - signals['exp_years'])
        exp_label = f'~{cand_exp:.0f} yrs exp'
        if diff <= 1:
            score += 15
            matched.append(exp_label)
        elif diff <= 3:
            score += 8
            matched.append(exp_label)
        elif diff <= 5:
            score += 3

    # Tiebreaker: existing match_score (0–10 pts)
    score += int(candidate.get('match_score', 0) * 0.1)

    return score, matched


@app.route('/api/v1/semantic-search', methods=['POST'])
def semantic_search():
    """Magic Search: rank candidate list by natural-language query relevance."""
    data = request.get_json()
    if not data or 'query' not in data or 'candidates' not in data:
        return jsonify({'error': "Missing 'query' or 'candidates'"}), 400

    query = data['query'].strip()
    candidates_list = data['candidates']

    if not query:
        return jsonify({'results': candidates_list, 'signals': {}}), 200

    signals = parse_magic_query(query)

    scored = []
    for cand in candidates_list:
        rel_score, matched_signals = score_relevance(cand, signals)
        scored.append({**cand, 'relevance_score': rel_score, 'matched_signals': matched_signals})

    scored.sort(key=lambda c: (c['relevance_score'], c.get('match_score', 0)), reverse=True)

    return jsonify({'results': scored, 'signals': signals, 'total': len(scored)})


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
            scored_data = score_candidate_data(raw_text, target_domain, file_hint=file_name)
            
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


@app.route('/api/v1/upload-cv', methods=['POST'])
def upload_cv():
    """Accept a CV file upload, save it permanently, extract text, screen it, and return results."""
    if 'file' not in request.files:
        return jsonify({"error": "No file part in request"}), 400

    file = request.files['file']
    target_domain = request.form.get('target_domain', 'Information Technology')

    if not file or file.filename == '':
        return jsonify({"error": "No file selected"}), 400

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in SUPPORTED_EXTENSIONS:
        return jsonify({"error": f"Unsupported file type '{ext}'. Accepted: .pdf, .docx, .doc, .txt"}), 400

    # Save with a unique name to avoid collisions
    safe_original = re.sub(r'[^\w\-. ]', '_', file.filename)
    unique_name = f"{uuid.uuid4().hex[:8]}_{safe_original}"
    save_path = os.path.join(UPLOAD_FOLDER, unique_name)
    file.save(save_path)

    # Extract text from the saved file
    raw_text = extract_text_from_file(save_path)

    # Run AI screening, passing the original filename as a name-parsing hint
    scored = score_candidate_data(raw_text, target_domain, file_hint=file.filename)
    scored['cv_file_name'] = unique_name

    return jsonify(scored)


@app.route('/api/v1/cv/<path:filename>', methods=['GET'])
def serve_cv(filename):
    """Serve a stored CV file for download."""
    return send_from_directory(UPLOAD_FOLDER, filename, as_attachment=True)


if __name__ == '__main__':
    # Run server locally on standard port 5000
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)

