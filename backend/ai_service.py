import os
import json
import time
import logging
from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def analyze_candidate_with_ai(cv_text: str, jd_text: str, target_domain: str, algorithmic_score: int) -> dict | None:
    """
    Performs precision ATS CV parsing and semantic screening using Google Gemini API if GEMINI_API_KEY is available.
    Executes name extraction, timeline experience tracking, contextual domain scoring, and structured intelligence extraction.
    If API key is missing or an error occurs, returns None for graceful algorithmic fallback.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key.strip() == "" or api_key.strip() == "YOUR_GEMINI_API_KEY_HERE":
        logger.info("No valid GEMINI_API_KEY found in environment. Using standard algorithmic screening.")
        return None

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key.strip())

        # Truncate texts if extremely long to avoid unnecessary token bloat
        cv_preview = cv_text[:14000] if cv_text else "No resume text available."
        jd_preview = jd_text[:5000] if jd_text else f"General role in {target_domain} domain."

        prompt = f"""You are an expert, production-grade ATS (Applicant Tracking System) CV parser and precision engineering recruiter. Your task is to ingest raw unstructured text from a candidate's resume, cleanly parse out profile parameters, and contextually score them against a provided target job domain and job description.

Execute this extraction and matching logic strictly according to the rules below:

### 1. NAME EXTRACTION RULES
- Locate the candidate's absolute legal full name from the top header lines of the document text.
- STRIP and IGNORE all trailing credentials, post-nominal titles, or certifications (e.g., "MBA", "PMP", "Ph.D", "P.E", "C.Eng").
- STRIP and IGNORE prefix labels such as "NAME :", "Name:", "Full Name:", "Candidate Name:", "Applicant Name:", "Resume of:", "Curriculum Vitae of:", "CV of:", or "Application of:".
- CRITICAL DELIMITER RULE: If a header or filename is formatted with a dash or pipe like "<Candidate Name> - <Job Title>" or "John Doe | Senior Pipeline Engineer", you MUST extract ONLY the person's name before the delimiter ("John Doe"). Never include job titles like "Engineer", "Manager", "Consultant", "Director", or "Specialist" in the full_name field.
- BLOCKLIST CRITICAL ERROR: Under no circumstances use standard resume structural section headers (such as "PERSONAL DETAILS", "PROFESSIONAL SUMMARY", "CAREER SUMMARY", "RESUME", or "EDUCATION") as the candidate's name. If no explicit person's name is identifiable, fallback to "Unknown Candidate".

### 2. EXPERIENCE TIMELINE TRACKING RULES
- Do not blindly latch onto isolated generic number strings like "3 years of military service" or "1 year of training" to populate total experience.
- You must mathematically compute the candidate's overall career span by evaluating the chronological sequence of their historical work timeline blocks from their first relevant role to the present year (2026).
- Deduce "relevant_experience_years" based strictly on how many of those active working years were spent performing functions aligned with the provided Job Description.

### 3. CONTEXTUAL SCORING RULES
- Evaluate a match_score dynamically from 0 to 100.
- Avoid naïve keyword counting flags. Understand deep technical semantics. For example: If a candidate mentions "Anode Furnaces" or "BMS strategies", recognize that contextually maps to Industrial Environments or Controls without needing a verbatim string match.
- Ensure that if a candidate is a phenomenal expert in an unrelated sub-domain (e.g., a pure High-Voltage Substation engineer being evaluated for an Industrial Automation/PLC software role), their match score drops significantly to accurately reflect the functional profile pivot required.

### 4. DYNAMIC MANDATORY REQUIREMENTS EXTRACTION & VERIFICATION (HARD STOP RULE)
- Read the provided Job Description to dynamically identify any requirements that are explicitly labeled as "MANDATORY", "REQUIRED", or similar absolute constraints (such as specific mandatory companies, required certifications, or mandatory geographic locations).
- Do NOT hardcode specific names (like "Aramco" or "SEC") in your parsing logic; instead, extract them dynamically from the active job description.
- For each identified mandatory/required rule, cross-reference the candidate's CV text to verify if they satisfy this requirement.
- Set the "eligible" output field to true if the candidate satisfies all identified mandatory/required rules, or if no mandatory/required rules are found in the Job Description.
- HARD STOP RULE: If the candidate completely lacks any of the identified mandatory/required requirements, you must set "eligible" to false, cap the "match_score" at a maximum of 40% (or less if the candidate naturally scores lower), and state exactly which mandatory requirement was missing in the "justification" field.
- If the candidate is eligible, set "justification" to null.

### 5. OUTPUT SCHEMA CONSTRAINTS
Your response must be returned strictly as a clean, single, valid JSON object with no markdown code blocks, no backticks, and no trailing prose. Match this exact JSON typography:

{{
  "full_name": "String (Proper Casing, cleared of certifications/post-nominals)",
  "email": "String",
  "phone": "String",
  "total_experience_years": Number (Float, mathematically calculated from history),
  "relevant_experience_years": Number (Float, functionally mapped to the JD),
  "match_score": Number (Integer from 0 to 100),
  "skills_matrix": ["String (Cleaned uppercase tool/tech names found)"],
  "specialization_tags": ["String (Protocol/Domain tags like 'IEC 61850', 'SCADA', 'Modbus')"],
  "industry_remarks": "String (A concise 2-3 sentence overview detailing structural alignment, tool proficiencies, or critical domain/timeline experience gaps)",
  "eligible": Boolean,
  "justification": "String or null (If eligible is false, explain exactly which mandatory requirement was missing)"
}}

### 6. INPUT PARAMETERS
Target Domain: {target_domain}
Job Description: {jd_preview}

Candidate Resume Raw Text:
{cv_preview}
"""

        models_to_try = [
            "gemini-2.5-flash",
            "gemini-2.5-flash-lite",
            "gemini-2.0-flash",
            "gemini-2.0-flash-lite",
            "gemini-flash-latest"
        ]
        for model_name in models_to_try:
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.1,
                    ),
                )

                if response.text:
                    result = json.loads(response.text)
                    logger.info(f"Precision ATS AI Analysis completed successfully via {model_name}. Name: {result.get('full_name')}, Score: {result.get('match_score', algorithmic_score)}%")
                    return result
            except Exception as e:
                err_str = str(e)
                logger.warning(f"Google Gemini model {model_name} error: {err_str[:80]}...")
                time.sleep(0.5)

        return None
    except Exception as e:
        logger.error(f"Error calling Google Gemini API during ATS screening: {str(e)}")
        return None


def ocr_image_with_gemini(image_bytes: bytes) -> str:
    """
    Performs OCR on a single page image using the Google Gemini model.
    Returns the extracted text, or an empty string on error.
    """
    results = ocr_batch_pages_with_gemini([image_bytes])
    return results[0] if results else ""


def ocr_batch_pages_with_gemini(pages_image_bytes: list[bytes]) -> list[str]:
    """
    Performs OCR on multiple page images in a SINGLE Gemini API call to avoid
    rate limits when processing fully-scanned multi-page PDF bundles.

    Each element in pages_image_bytes is a raw PNG byte string for one page.
    Returns a list of extracted text strings (one per page), in the same order.
    Pages that fail OCR return empty strings.

    Gemini supports up to ~20 inline image parts per request; we batch in
    groups of MAX_BATCH_SIZE to stay well within the limit.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key.strip() == "" or api_key.strip() == "YOUR_GEMINI_API_KEY_HERE":
        logger.warning("ocr_batch_pages_with_gemini: No valid GEMINI_API_KEY found.")
        return [""] * len(pages_image_bytes)

    MAX_BATCH_SIZE = 8   # pages per Gemini call — safe limit for inline images
    all_texts: list[str] = []

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key.strip())

        for batch_start in range(0, len(pages_image_bytes), MAX_BATCH_SIZE):
            batch = pages_image_bytes[batch_start: batch_start + MAX_BATCH_SIZE]
            n = len(batch)

            # Build a multi-image content payload
            image_parts = [
                types.Part.from_bytes(data=img, mime_type="image/png")
                for img in batch
            ]

            instructions = (
                f"You are receiving {n} scanned document page(s) from a single PDF. "
                f"Perform accurate OCR on each page. "
                f"Output the transcribed text for each page, separated by the marker '===PAGE_BREAK==='. "
                f"Maintain the original text structure. Return ONLY the transcribed text and page break markers, "
                f"with no introductory text, explanations, or comments."
            )

            contents = image_parts + [instructions]

            response_text = None
            models_to_try = [
                "gemini-2.5-flash",
                "gemini-2.5-flash-lite",
                "gemini-2.0-flash",
                "gemini-2.0-flash-lite",
                "gemini-flash-latest"
            ]
            for model_name in models_to_try:
                try:
                    logger.info(f"ocr_batch_pages_with_gemini: attempting OCR via {model_name}...")
                    response = client.models.generate_content(
                        model=model_name,
                        contents=contents
                    )
                    if response.text and response.text.strip():
                        response_text = response.text
                        logger.info(f"ocr_batch_pages_with_gemini: successfully OCR'd batch via {model_name}")
                        break
                    else:
                        logger.warning(f"ocr_batch_pages_with_gemini: model {model_name} returned empty text.")
                except Exception as model_err:
                    logger.warning(f"ocr_batch_pages_with_gemini: model {model_name} failed: {str(model_err)[:100]}")
                time.sleep(0.5)

            if response_text:
                # Split by our page break marker — one section per page
                sections = response_text.split("===PAGE_BREAK===")
                for i, section in enumerate(sections[:n]):
                    all_texts.append(section.strip())
                # If Gemini returned fewer sections than pages, pad with empty strings
                for _ in range(n - len(sections)):
                    all_texts.append("")
            else:
                all_texts.extend([""] * n)

            logger.info(
                f"ocr_batch_pages_with_gemini: processed batch starting at {batch_start+1} "
                f"({sum(len(t) for t in all_texts[-n:])} chars total)"
            )

            # Brief pause between batches to respect rate limits
            if batch_start + MAX_BATCH_SIZE < len(pages_image_bytes):
                time.sleep(0.5)

    except Exception as e:
        logger.error(f"ocr_batch_pages_with_gemini error: {str(e)}")
        # Return what we have so far, pad the rest with empty strings
        while len(all_texts) < len(pages_image_bytes):
            all_texts.append("")

    return all_texts


