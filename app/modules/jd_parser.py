"""
Module 4: Job Description Auto-Parser
Upload any JD text → automatically extracts required skills,
preferred skills, experience level, and role category.
"""

import re
from .nlp_parser import SKILL_TAXONOMY

# Experience level patterns
EXP_PATTERNS = [
    (r"(\d+)\+?\s*years?\s+(?:of\s+)?(?:experience|exp)", "exact"),
    (r"(\d+)\s*[-–to]+\s*(\d+)\s*years?",                  "range"),
    (r"\b(fresher|entry.?level|0.?1 year)\b",               "fresher"),
    (r"\b(junior|1.?3 years?)\b",                           "junior"),
    (r"\b(mid.?level|3.?5 years?|3.?6 years?)\b",           "mid"),
    (r"\b(senior|5\+|5.?8 years?)\b",                       "senior"),
    (r"\b(lead|principal|8\+|10\+)\b",                      "lead"),
]

# Role category keywords
ROLE_CATEGORIES = {
    "Data Scientist":       ["data scientist", "ml engineer", "machine learning engineer", "ai engineer"],
    "Backend Developer":    ["backend", "back-end", "server side", "api developer", "java developer", "python developer"],
    "Frontend Developer":   ["frontend", "front-end", "ui developer", "react developer", "angular developer"],
    "Full Stack Developer": ["full stack", "fullstack", "mern", "mean"],
    "DevOps Engineer":      ["devops", "site reliability", "sre", "cloud engineer", "infrastructure"],
    "Data Analyst":         ["data analyst", "business analyst", "bi analyst", "reporting analyst"],
    "Mobile Developer":     ["android developer", "ios developer", "mobile developer", "flutter developer"],
    "RPA Developer":        ["rpa developer", "uipath", "automation developer", "rpa"],
    "Cybersecurity":        ["security engineer", "cybersecurity", "penetration tester", "infosec"],
    "Software Engineer":    ["software engineer", "software developer", "sde", "swe"],
}

# Responsibility section triggers
RESP_TRIGGERS   = ["responsibilities", "roles and responsibilities", "job duties", "what you'll do", "key duties"]
REQUIRED_TRIGGERS = ["required", "requirements", "must have", "mandatory", "essential", "qualifications"]
PREFERRED_TRIGGERS = ["preferred", "nice to have", "good to have", "bonus", "plus", "desirable", "advantage"]


def parse_job_description(jd_text):
    """
    Full parse of a job description.
    Returns structured dict with all extracted info.
    """
    jd_lower = jd_text.lower()

    result = {
        "title":              _extract_job_title(jd_text, jd_lower),
        "role_category":      _detect_role_category(jd_lower),
        "experience_level":   _extract_experience_level(jd_lower),
        "required_skills":    _extract_required_skills(jd_text, jd_lower),
        "preferred_skills":   _extract_preferred_skills(jd_text, jd_lower),
        "all_skills":         [],
        "responsibilities":   _extract_responsibilities(jd_text, jd_lower),
        "raw_text":           jd_text,
    }

    # Merge skills: required + preferred (no duplicates)
    all_skills = list(set(result["required_skills"] + result["preferred_skills"]))
    result["all_skills"] = all_skills

    return result


def _extract_job_title(text, text_lower):
    """Extract job title from first few lines."""
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    for line in lines[:5]:
        if 2 <= len(line.split()) <= 8 and len(line) < 60:
            if not any(c.isdigit() for c in line):
                return line
    return "Software Engineer"


def _detect_role_category(text_lower):
    for category, keywords in ROLE_CATEGORIES.items():
        for kw in keywords:
            if kw in text_lower:
                return category
    return "Software Engineer"


def _extract_experience_level(text_lower):
    for pattern, level_type in EXP_PATTERNS:
        m = re.search(pattern, text_lower)
        if m:
            if level_type == "exact":
                yrs = int(m.group(1))
                if yrs == 0:   return "Fresher (0 years)"
                elif yrs <= 2: return f"Junior ({yrs}+ years)"
                elif yrs <= 5: return f"Mid-level ({yrs}+ years)"
                else:          return f"Senior ({yrs}+ years)"
            elif level_type == "range":
                return f"{m.group(1)}–{m.group(2)} years"
            else:
                labels = {
                    "fresher": "Fresher (0–1 years)",
                    "junior":  "Junior (1–3 years)",
                    "mid":     "Mid-level (3–5 years)",
                    "senior":  "Senior (5+ years)",
                    "lead":    "Lead / Principal (8+ years)",
                }
                return labels.get(level_type, "Not specified")
    return "Not specified"


def _extract_required_skills(text, text_lower):
    """Extract skills from 'required' sections and general JD body."""
    required_section = _extract_section(text, REQUIRED_TRIGGERS, PREFERRED_TRIGGERS + RESP_TRIGGERS)
    if not required_section:
        required_section = text  # fallback: scan whole JD

    required_lower = required_section.lower()
    found = set()
    for skill_name, keywords in SKILL_TAXONOMY.items():
        for kw in keywords:
            if kw in required_lower:
                found.add(skill_name)
                break
    return sorted(list(found))


def _extract_preferred_skills(text, text_lower):
    """Extract skills from 'preferred / nice to have' sections."""
    preferred_section = _extract_section(text, PREFERRED_TRIGGERS, RESP_TRIGGERS + REQUIRED_TRIGGERS)
    if not preferred_section:
        return []

    preferred_lower = preferred_section.lower()
    found = set()
    for skill_name, keywords in SKILL_TAXONOMY.items():
        for kw in keywords:
            if kw in preferred_lower:
                found.add(skill_name)
                break
    return sorted(list(found))


def _extract_responsibilities(text, text_lower):
    """Extract bullet points from responsibilities section."""
    section = _extract_section(text, RESP_TRIGGERS, REQUIRED_TRIGGERS + PREFERRED_TRIGGERS)
    if not section:
        return []

    bullets = []
    for line in section.split('\n'):
        line = line.strip()
        line = re.sub(r'^[\•\-\*\→\►\d\.\)]+\s*', '', line)
        if len(line) > 15 and len(line) < 200:
            bullets.append(line)
    return bullets[:8]


def _extract_section(text, start_triggers, stop_triggers):
    """Extract text between section headers."""
    lines = text.split('\n')
    capturing = False
    section_lines = []

    for line in lines:
        ll = line.lower().strip()
        is_start = any(t in ll for t in start_triggers) and len(ll) < 60
        is_stop  = any(t in ll for t in stop_triggers)  and len(ll) < 60 and capturing

        if is_start:
            capturing = True
            continue
        if is_stop:
            break
        if capturing:
            section_lines.append(line)

    return '\n'.join(section_lines).strip()


def compute_jd_match(parsed_resume, parsed_jd, blind_mode=False):
    """
    Compute how well a resume matches a job description.
    Returns match scores and breakdown for Explainable AI.
    """
    resume = parsed_resume
    required = set(parsed_jd.get("required_skills", []))
    preferred = set(parsed_jd.get("preferred_skills", []))
    candidate_skills = set(resume.get("skills", []))

    # Skills match
    required_matched  = candidate_skills & required
    preferred_matched = candidate_skills & preferred
    missing_required  = required - candidate_skills
    missing_preferred = preferred - candidate_skills

    skills_score = 0
    if required:
        skills_score = (len(required_matched) / len(required)) * 100
    elif candidate_skills:
        skills_score = min(len(candidate_skills) * 8, 100)

    # Experience score
    jd_exp_text = parsed_jd.get("experience_level", "")
    exp_required = _parse_exp_years(jd_exp_text)
    candidate_exp = resume.get("experience_years", 0)
    if exp_required == 0:
        exp_score = 85  # fresher role — anyone qualifies
    elif candidate_exp >= exp_required:
        exp_score = 100
    else:
        exp_score = max(0, (candidate_exp / exp_required) * 100)

    # Project score
    projects_count = len(resume.get("projects", []))
    project_score  = min(projects_count * 18, 100)

    # Certification bonus
    certs = len(resume.get("certifications", []))
    cert_score = min(certs * 20, 100)

    # GitHub presence bonus
    github_score = 85 if resume.get("has_github") else 40

    # CGPA score
    try:
        cgpa = float(resume.get("education", {}).get("cgpa", 0))
        cgpa_score = (cgpa / 10) * 100 if cgpa <= 10 else (cgpa / 100) * 100
    except:
        cgpa_score = 60  # default if not found

    # Weighted overall score
    weights = {
        "skills_match":   0.40,
        "experience":     0.25,
        "projects":       0.15,
        "certifications": 0.08,
        "github":         0.07,
        "cgpa":           0.05,
    }
    component_scores = {
        "skills_match":   round(skills_score, 1),
        "experience":     round(exp_score, 1),
        "projects":       round(project_score, 1),
        "certifications": round(cert_score, 1),
        "github":         round(github_score, 1),
        "cgpa":           round(cgpa_score, 1),
    }
    overall = sum(component_scores[k] * weights[k] for k in weights)

    return {
        "overall_score":       round(overall, 1),
        "component_scores":    component_scores,
        "weights":             weights,
        "required_matched":    sorted(list(required_matched)),
        "preferred_matched":   sorted(list(preferred_matched)),
        "missing_required":    sorted(list(missing_required)),
        "missing_preferred":   sorted(list(missing_preferred)),
        "exp_required":        exp_required,
        "candidate_exp":       candidate_exp,
        "blind_mode":          blind_mode,
    }


def _parse_exp_years(exp_text):
    m = re.search(r"(\d+)", exp_text)
    return int(m.group(1)) if m else 0
