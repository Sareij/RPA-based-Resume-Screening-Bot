"""
Module 3: Bias Detection & Blind Screening Engine
Detects and masks potential bias indicators from resumes.
Makes hiring fair by evaluating skills, not identity.
"""

import re

# ── Bias indicator patterns ────────────────────────────────────────────────────

# Name patterns (common Indian + international names)
NAME_TITLE_PATTERN = r"\b(mr\.?|mrs\.?|ms\.?|dr\.?|prof\.?)\b"

# Gender signal words
GENDER_SIGNALS = [
    r"\b(he|him|his|himself)\b",
    r"\b(she|her|hers|herself)\b",
    r"\b(father|mother|husband|wife|son|daughter)\b",
    r"\b(male|female|gender)\b",
    r"\b(mr\.|mrs\.|ms\.)\b",
]

# Religion / caste signals
RELIGION_CASTE_SIGNALS = [
    "hindu", "muslim", "christian", "sikh", "jain", "buddhist",
    "brahmin", "yadav", "nadar", "gounder", "mudaliar", "pillai",
    "caste", "religion", "community",
]

# Location bias indicators
LOCATION_BIAS_WORDS = [
    "village", "district", "taluk", "panchayat",
]

# College tier keywords (to detect potential prestige bias)
TIER1_COLLEGES  = ["iit", "iim", "nit", "bits pilani", "delhi university", "anna university"]
TIER2_COLLEGES  = ["vit", "srm", "manipal", "amrita", "psg", "coimbatore institute"]

# Age indicators
AGE_PATTERN = r"\b(age|dob|date of birth|born in|born on)[:\s]*(\d{1,2}[\s\/\-\.]\d{1,2}[\s\/\-\.]\d{2,4}|\d{4})\b"
AGE_DIRECT  = r"\b(age|aged)\s*:?\s*(\d{2})\b"

# Photo mention
PHOTO_PATTERN = r"\b(photograph|photo|passport size|attached photo)\b"

# Marital status
MARITAL_PATTERN = r"\b(married|single|unmarried|marital status|divorced)\b"


def detect_bias_indicators(parsed_resume):
    """
    Analyse a parsed resume for bias indicators.
    Returns a dict of detected biases with severity scores.
    """
    text = parsed_resume.get("raw_text", "")
    text_lower = text.lower()
    bias_report = {
        "flags":         [],
        "severity":      0,
        "bias_score":    0,      # 0 = no bias, 100 = heavily biased
        "college_tier":  "Unknown",
        "has_photo_mention": False,
    }

    # 1. Gender signals
    gender_found = []
    for pat in GENDER_SIGNALS:
        m = re.search(pat, text_lower)
        if m:
            gender_found.append(m.group(0))
    if gender_found:
        bias_report["flags"].append({
            "type": "Gender signal",
            "detail": f"Found: {', '.join(set(gender_found))}",
            "severity": "Medium",
        })
        bias_report["severity"] += 15

    # 2. Age indicators
    if re.search(AGE_PATTERN, text_lower) or re.search(AGE_DIRECT, text_lower):
        bias_report["flags"].append({
            "type": "Age disclosure",
            "detail": "Explicit age or date of birth found",
            "severity": "Medium",
        })
        bias_report["severity"] += 15

    # 3. Religion/caste signals
    rel_found = [w for w in RELIGION_CASTE_SIGNALS if w in text_lower]
    if rel_found:
        bias_report["flags"].append({
            "type": "Religion/Caste signal",
            "detail": f"Found: {', '.join(rel_found[:3])}",
            "severity": "High",
        })
        bias_report["severity"] += 25

    # 4. Marital status
    if re.search(MARITAL_PATTERN, text_lower):
        bias_report["flags"].append({
            "type": "Marital status",
            "detail": "Marital status mentioned — not relevant for hiring",
            "severity": "Low",
        })
        bias_report["severity"] += 10

    # 5. Photo mention
    if re.search(PHOTO_PATTERN, text_lower):
        bias_report["flags"].append({
            "type": "Photo attached",
            "detail": "Photograph mentioned — not relevant for skill evaluation",
            "severity": "Low",
        })
        bias_report["severity"] += 10
        bias_report["has_photo_mention"] = True

    # 6. College tier
    college = parsed_resume.get("education", {}).get("college", "").lower()
    if any(t in college for t in TIER1_COLLEGES):
        bias_report["college_tier"] = "Tier 1 (Premium)"
        bias_report["flags"].append({
            "type": "College prestige",
            "detail": "Tier 1 institution — could trigger prestige bias",
            "severity": "Info",
        })
    elif any(t in college for t in TIER2_COLLEGES):
        bias_report["college_tier"] = "Tier 2"
    else:
        bias_report["college_tier"] = "Other / Not detected"

    # Calculate bias score (0–100)
    bias_report["bias_score"] = min(bias_report["severity"], 100)
    bias_report["flag_count"] = len(bias_report["flags"])

    return bias_report


def create_blind_resume(parsed_resume, bias_report):
    """
    Create a blinded version of the parsed resume.
    Removes all bias indicators — only skills, experience, education metrics remain.
    """
    blind = {
        "candidate_id":    f"CAND-{abs(hash(parsed_resume.get('email','x')))%10000:04d}",
        "skills":          parsed_resume.get("skills", []),
        "skill_count":     parsed_resume.get("skill_count", 0),
        "experience_years": parsed_resume.get("experience_years", 0),
        "certifications":  parsed_resume.get("certifications", []),
        "projects_count":  len(parsed_resume.get("projects", [])),
        "has_github":      parsed_resume.get("has_github", False),
        "education": {
            "degree": parsed_resume.get("education", {}).get("degree", ""),
            "cgpa":   parsed_resume.get("education", {}).get("cgpa", ""),
            # college name MASKED
            "college": "[ MASKED FOR BLIND REVIEW ]",
        },
        # All identity info removed
        "name":    "[ MASKED ]",
        "email":   "[ MASKED ]",
        "phone":   "[ MASKED ]",
        "linkedin": "[ MASKED ]",
    }
    return blind


def get_bias_summary(bias_report):
    """Human-readable bias summary for the dashboard."""
    score = bias_report["bias_score"]
    if score == 0:
        level = "Clean"
        color = "success"
        msg   = "No bias indicators detected. Resume is evaluation-ready."
    elif score <= 20:
        level = "Low"
        color = "info"
        msg   = "Minor bias signals present. Consider enabling blind mode."
    elif score <= 50:
        level = "Moderate"
        color = "warning"
        msg   = "Moderate bias indicators found. Blind mode recommended."
    else:
        level = "High"
        color = "danger"
        msg   = "Strong bias signals present. Blind mode strongly recommended."

    return {"level": level, "color": color, "message": msg, "score": score}
