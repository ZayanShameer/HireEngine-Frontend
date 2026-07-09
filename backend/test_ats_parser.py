import os
import sys
import glob
import json
import logging
from app import extract_text_from_file, score_candidate_data

# Disable overly verbose flask/werkzeug logging during test run
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("ATS_TEST_SUITE")

automationTestCaseSuite = [
    {
        "testId": "TC-001-HIGH",
        "candidateName": "K MUZZAMIL HUQ",
        "filePattern": "*K MUZZAMIL HUQ*.pdf",
        "expectedDomain": "Testing & Commissioning Engineering",
        "expectedMinScore": 55,
        "expectedEligibility": True
    },
    {
        "testId": "TC-002-EDGE",
        "candidateName": "Mahmoud Mohanad Mahmoud",
        "filePattern": "*MAHMOUD MOHANAD MAHMOUD*.pdf",
        "expectedMinYearsExp": 5.0,
        "expectedMinScore": 45,
        "expectedEligibility": True
    },
    {
        "testId": "TC-003-LOW",
        "candidateName": "YOUNAS ASADULLAH",
        "filePattern": "*YOUNAS ASADULLAH*.pdf",
        "expectedMaxScore": 40,
        "expectedEligibility": False,
        "customJd": "We are seeking a Senior Testing & Commissioning Electrical Engineer. MANDATORY REQUIREMENT: Candidate MUST have a PMP Certification. Any candidate without a PMP certification is strictly not eligible."
    }
]

def run_test_suite():
    if hasattr(sys.stdout, 'reconfigure'):
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass

    print("=" * 80)
    print("[START] HIRING ENGINE PRECISION ATS PARSER - AUTOMATION TEST SUITE")
    print("=" * 80)

    uploads_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")
    if not os.path.exists(uploads_dir):
        logger.error(f"Uploads directory not found at: {uploads_dir}")
        return

    passed_count = 0
    total_count = len(automationTestCaseSuite)

    for tc in automationTestCaseSuite:
        test_id = tc["testId"]
        candidate_name = tc["candidateName"]
        pattern = tc["filePattern"]
        
        print(f"\n[RUNNING] {test_id} | Target Candidate: {candidate_name}")
        
        # Locate candidate CV in uploads directory
        matched_files = glob.glob(os.path.join(uploads_dir, pattern))
        if not matched_files:
            print(f"[FAIL] [{test_id}]: No CV file matching pattern '{pattern}' found in {uploads_dir}")
            continue
            
        file_path = matched_files[0]
        file_name = os.path.basename(file_path)
        print(f"   [FILE] Ingesting file: {file_name}")
        
        # Extract text
        raw_text = extract_text_from_file(file_path)
        if not raw_text:
            print(f"[FAIL] [{test_id}]: Failed to extract text from {file_name}")
            continue

        # Set up realistic Job Description for Testing & Commissioning / Substation Engineering
        target_domain = tc.get("expectedDomain", "Testing & Commissioning Engineering")
        jd_text = tc.get("customJd") or (
            "We are seeking a Senior Testing & Commissioning Electrical Engineer with extensive experience "
            "in switchgear, GIS substations, high-voltage equipment testing, protection schemes, and SCADA systems. "
            "Candidates must have proven site commissioning leadership and strong electrical engineering credentials."
        )

        # Execute Precision ATS Parsing & Scoring
        print("   [AI] Running Semantic Evaluation & Parsing...")
        result = score_candidate_data(raw_text, target_domain, file_hint=file_name, jd_text=jd_text)

        actual_name = result.get("full_name", "")
        actual_score = result.get("match_score", 0)
        actual_total_exp = result.get("total_experience_years", 0.0)
        actual_rel_exp = result.get("relevant_experience_years", 0.0)
        remarks = result.get("industry_remarks", "")
        is_eligible = result.get("eligible", True)

        # Assertions & Verification
        failures = []
        
        if "expectedMinScore" in tc and actual_score < tc["expectedMinScore"]:
            failures.append(f"Score {actual_score}% is lower than expected min {tc['expectedMinScore']}%")
            
        if "expectedMaxScore" in tc and actual_score > tc["expectedMaxScore"]:
            failures.append(f"Score {actual_score}% is higher than expected max {tc['expectedMaxScore']}%")
            
        if "expectedMinYearsExp" in tc and actual_total_exp < tc["expectedMinYearsExp"]:
            failures.append(f"Total Experience {actual_total_exp:.1f}y is less than expected min {tc['expectedMinYearsExp']}y (3y military bug check)")
            
        if "expectedEligibility" in tc and is_eligible != tc["expectedEligibility"]:
            failures.append(f"Eligibility {is_eligible} did not match expected {tc['expectedEligibility']}")

        # Output Test Result
        if not failures:
            passed_count += 1
            print(f"   [PASS] [{test_id}]")
            print(f"      - Extracted Name: '{actual_name}'")
            print(f"      - Career Span / Exp: {actual_total_exp:.1f}y Total ({actual_rel_exp:.1f}y Relevant)")
            print(f"      - Semantic Match Score: {actual_score}% (Eligibility: {'Eligible' if is_eligible else 'Not Eligible'})")
            print(f"      - AI Remarks Summary: {remarks[:140]}...")
        else:
            print(f"   [FAIL] [{test_id}]")
            print(f"      - Extracted Name: '{actual_name}'")
            print(f"      - Career Span / Exp: {actual_total_exp:.1f}y Total ({actual_rel_exp:.1f}y Relevant)")
            print(f"      - Semantic Match Score: {actual_score}%")
            for f in failures:
                print(f"      [WARNING] Assertion Failure: {f}")

    print("\n" + "=" * 80)
    print(f"[SUMMARY] TEST SUITE: {passed_count}/{total_count} PASSED ({int(passed_count/total_count*100)}%)")
    print("=" * 80)

    if passed_count == total_count:
        print("[SUCCESS] ALL PRODUCTION ATS PARSING & SCORING RULES VERIFIED SUCCESSFULLY!")
        sys.exit(0)
    else:
        print("[WARNING] SOME TEST CASES FAILED. PLEASE REVIEW LOGS.")
        sys.exit(1)

if __name__ == '__main__':
    run_test_suite()
