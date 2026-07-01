import re

with open("backend/app.py", "r", encoding="utf-8") as f:
    text = f.read()

new_domain_taxonomy = """DOMAIN_TAXONOMY = {
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
}"""

new_spec_pool = """SPECIALIZATION_POOL = [
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
]"""

new_skill_pool = """SKILLS_POOL = [
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
]"""

new_aliases = """SKILL_ALIASES = {
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
}"""

# Replacements
text = re.sub(r'DOMAIN_TAXONOMY\s*=\s*\{.*?\}', new_domain_taxonomy, text, flags=re.DOTALL)
text = re.sub(r'SPECIALIZATION_POOL\s*=\s*\[.*?\]', new_spec_pool, text, flags=re.DOTALL)
text = re.sub(r'SKILLS_POOL\s*=\s*\[.*?\]', new_skill_pool, text, flags=re.DOTALL)

# Aliases
text = re.sub(r'SKILL_ALIASES\s*=\s*\{.*?\}.*?SPEC_ALIASES\s*=\s*\{.*?\}', new_aliases, text, flags=re.DOTALL)

with open("backend/app.py", "w", encoding="utf-8") as f:
    f.write(text)

print("Replacement script executed successfully.")
