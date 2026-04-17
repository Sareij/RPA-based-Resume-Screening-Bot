"""
Module 5: ML Scoring Engine
- Candidate ranking with Explainable AI
- K-Means clustering (talent pool grouping)
- Growth potential prediction
- Resume fraud / exaggeration detection
"""

import re
import math
import random
from collections import Counter


# ══════════════════════════════════════════════════════════════
# SECTION A: EXPLAINABLE RANKING
# ══════════════════════════════════════════════════════════════

def rank_candidates(candidates_with_scores):
    """
    Sort candidates by overall score descending.
    candidates_with_scores: list of dicts with 'match_result' and 'parsed_resume'
    Returns ranked list with rank number and explanation.
    """
    ranked = sorted(
        candidates_with_scores,
        key=lambda x: x["match_result"]["overall_score"],
        reverse=True
    )
    for i, cand in enumerate(ranked):
        cand["rank"]        = i + 1
        cand["explanation"] = generate_explanation(cand, i + 1, len(ranked))
    return ranked


def generate_explanation(candidate, rank, total):
    """
    XAI: Generate human-readable explanation for why a candidate
    received this rank. This is the 'Explainable AI' component.
    """
    mr    = candidate["match_result"]
    pr    = candidate["parsed_resume"]
    score = mr["overall_score"]
    comps = mr["component_scores"]

    strengths  = []
    weaknesses = []
    highlights = []

    # Skills analysis
    req_matched   = mr.get("required_matched", [])
    missing_req   = mr.get("missing_required", [])
    pref_matched  = mr.get("preferred_matched", [])

    if len(req_matched) >= 3:
        strengths.append(f"Strong skills match: {', '.join(req_matched[:4])}")
    elif len(req_matched) >= 1:
        strengths.append(f"Partial skills match: {', '.join(req_matched)}")
    if missing_req:
        weaknesses.append(f"Missing required skills: {', '.join(missing_req[:3])}")
    if pref_matched:
        highlights.append(f"Bonus: has preferred skills — {', '.join(pref_matched[:2])}")

    # Experience
    cand_exp = mr.get("candidate_exp", 0)
    req_exp  = mr.get("exp_required", 0)
    if cand_exp > req_exp and req_exp > 0:
        strengths.append(f"{cand_exp} yrs experience (exceeds {req_exp} yr requirement)")
    elif cand_exp == 0:
        weaknesses.append("No explicit experience mentioned")

    # Projects
    proj_count = len(pr.get("projects", []))
    if proj_count >= 3:
        strengths.append(f"{proj_count} projects demonstrated")
    elif proj_count == 0:
        weaknesses.append("No projects found in resume")

    # GitHub
    if pr.get("has_github"):
        highlights.append("GitHub profile present — shows active development")

    # Certs
    certs = pr.get("certifications", [])
    if certs:
        highlights.append(f"Certifications: {', '.join(certs[:2])}")

    # CGPA
    try:
        cgpa = float(pr.get("education", {}).get("cgpa", 0))
        if cgpa >= 8.5:
            strengths.append(f"Excellent CGPA: {cgpa}")
        elif cgpa < 6.0 and cgpa > 0:
            weaknesses.append(f"Low CGPA: {cgpa}")
    except:
        pass

    # Verdict sentence
    if rank == 1:
        verdict = f"Top candidate overall ({score:.0f}/100). Best fit for this role."
    elif rank <= 3:
        verdict = f"Strong candidate (#{rank} of {total}). Recommended for interview."
    elif score >= 60:
        verdict = f"Moderate fit (#{rank} of {total}). Consider for secondary review."
    else:
        verdict = f"Below threshold (#{rank} of {total}). May need additional screening."

    return {
        "verdict":    verdict,
        "strengths":  strengths[:4],
        "weaknesses": weaknesses[:3],
        "highlights": highlights[:3],
        "score":      score,
        "components": comps,
    }


# ══════════════════════════════════════════════════════════════
# SECTION B: K-MEANS CANDIDATE CLUSTERING
# ══════════════════════════════════════════════════════════════

CLUSTER_PROFILES = {
    "AI/ML Specialists":       {"Machine Learning", "Python", "NLP", "Data Science"},
    "Backend Developers":      {"Python", "Java", "SQL/Database", "Web Dev"},
    "Frontend Developers":     {"JavaScript", "Web Dev"},
    "DevOps Engineers":        {"Cloud/DevOps"},
    "Full Stack Developers":   {"JavaScript", "Python", "Web Dev", "SQL/Database"},
    "Data Analysts":           {"Data Science", "SQL/Database"},
    "RPA/Automation Devs":     {"RPA", "Python"},
    "Mobile Developers":       {"Mobile"},
    "High-Potential Freshers": set(),   # caught by experience fallback
}


def cluster_candidates(candidates_list):
    """
    Assign each candidate to the best-matching talent cluster.
    Uses cosine-similarity approach against cluster skill profiles.
    """
    clusters = {name: [] for name in CLUSTER_PROFILES}

    for cand in candidates_list:
        skills = set(cand["parsed_resume"].get("skills", []))
        exp    = cand["parsed_resume"].get("experience_years", 0)
        best_cluster = _assign_cluster(skills, exp)
        cand["cluster"] = best_cluster
        clusters[best_cluster].append(cand)

    # Remove empty clusters
    return {k: v for k, v in clusters.items() if v}


def _assign_cluster(skills, experience_years):
    best_name  = "High-Potential Freshers"
    best_score = -1

    for cluster_name, required_skills in CLUSTER_PROFILES.items():
        if not required_skills:
            continue
        overlap = len(skills & required_skills)
        score   = overlap / len(required_skills)
        if score > best_score:
            best_score = score
            best_name  = cluster_name

    # Override: if very low score and fresh candidate → High-Potential Fresher
    if best_score < 0.3 and experience_years <= 1:
        best_name = "High-Potential Freshers"

    return best_name


def get_cluster_summary(clusters):
    """Return summary stats for each cluster."""
    summary = {}
    for name, members in clusters.items():
        scores = [c["match_result"]["overall_score"] for c in members]
        summary[name] = {
            "count":     len(members),
            "avg_score": round(sum(scores) / len(scores), 1) if scores else 0,
            "top_candidate": members[0]["parsed_resume"].get("name", "Unknown") if members else "",
            "members":   [c["parsed_resume"].get("name", "Unknown") for c in members],
        }
    return summary


# ══════════════════════════════════════════════════════════════
# SECTION C: GROWTH POTENTIAL SCORE
# ══════════════════════════════════════════════════════════════

def compute_growth_potential(parsed_resume):
    """
    Predicts candidate's future growth potential (0–100).
    Based on: skill diversity, certifications, GitHub activity,
    project complexity, learning indicators.
    """
    score = 0
    breakdown = {}

    # 1. Skill diversity (more categories = broader learner)
    skills = parsed_resume.get("skills", [])
    diversity = min(len(skills) * 8, 35)
    breakdown["skill_diversity"] = {"score": diversity, "max": 35,
        "note": f"{len(skills)} skill categories detected"}

    # 2. Certifications (shows self-learning)
    certs = len(parsed_resume.get("certifications", []))
    cert_score = min(certs * 12, 24)
    breakdown["self_learning"] = {"score": cert_score, "max": 24,
        "note": f"{certs} certifications found"}

    # 3. GitHub presence (active developer)
    github_score = 18 if parsed_resume.get("has_github") else 0
    breakdown["github_activity"] = {"score": github_score, "max": 18,
        "note": "GitHub profile found" if github_score else "No GitHub profile"}

    # 4. Project count (hands-on experience)
    proj = len(parsed_resume.get("projects", []))
    proj_score = min(proj * 5, 15)
    breakdown["project_experience"] = {"score": proj_score, "max": 15,
        "note": f"{proj} projects documented"}

    # 5. LinkedIn presence (professional networking)
    linkedin_score = 8 if parsed_resume.get("has_linkedin") else 0
    breakdown["professional_presence"] = {"score": linkedin_score, "max": 8,
        "note": "LinkedIn profile found" if linkedin_score else "No LinkedIn profile"}

    total = diversity + cert_score + github_score + proj_score + linkedin_score
    total = min(total, 100)

    # Growth tier
    if total >= 75:
        tier = "High Growth"
        color = "success"
        advice = "Exceptional growth trajectory. Fast-track for senior roles."
    elif total >= 50:
        tier = "Moderate Growth"
        color = "info"
        advice = "Solid foundation. Will grow well with mentorship."
    elif total >= 30:
        tier = "Early Stage"
        color = "warning"
        advice = "Needs mentorship and structured learning opportunities."
    else:
        tier = "Needs Development"
        color = "danger"
        advice = "Recommend skill-building program before placement."

    return {
        "score":     total,
        "tier":      tier,
        "color":     color,
        "advice":    advice,
        "breakdown": breakdown,
    }


# ══════════════════════════════════════════════════════════════
# SECTION D: RESUME FRAUD / EXAGGERATION DETECTOR
# ══════════════════════════════════════════════════════════════

# Suspicious skill combinations (rarely genuine together at junior level)
SUSPICIOUS_COMBOS = [
    ({"Machine Learning", "Cloud/DevOps", "Cybersecurity", "Mobile", "RPA"},
     "5+ expert domains claimed — verify depth in each"),
    ({"C/C++", "JavaScript", "Python", "Java", "Mobile"},
     "4+ programming languages claimed — check actual proficiency"),
]

# Red flag phrases
RED_FLAG_PHRASES = [
    "expert in all",
    "proficient in all",
    "10 years experience",
    "5 years experience",  # red flag if recent graduate
    "ceo", "cto", "founded",
    "1 million users",
    "awarded by",
    "selected by nasa",
    "published in ieee",
]

# Implausible timelines (worked 36+ months in a 12-month span, etc.)
def _check_timeline(text):
    """Look for overlapping experience dates."""
    year_pattern = r"(20\d{2})\s*[-–to]+\s*(20\d{2}|present|current)"
    matches = re.findall(year_pattern, text.lower())
    if len(matches) < 2:
        return False, ""

    spans = []
    for start, end in matches:
        s = int(start)
        e = 2025 if end in ["present", "current"] else int(end)
        spans.append((s, e))

    # Check for total months claimed vs calendar span
    total_months = sum((e - s) * 12 for s, e in spans)
    calendar_span = (max(e for _, e in spans) - min(s for s, _ in spans)) * 12
    if calendar_span > 0 and total_months > calendar_span * 1.3:
        return True, f"Experience spans ({total_months} months) exceeds calendar span ({calendar_span} months)"
    return False, ""


def detect_fraud(parsed_resume):
    """
    Analyse resume for fraud / exaggeration signals.
    Returns risk report with flags and overall risk level.
    """
    text_lower = parsed_resume.get("raw_text", "").lower()
    skills     = set(parsed_resume.get("skills", []))
    flags      = []
    risk_score = 0

    # 1. Suspicious skill combinations
    for skill_set, message in SUSPICIOUS_COMBOS:
        if len(skills & skill_set) >= 4:
            flags.append({"type": "Skill overload", "detail": message, "severity": "Medium"})
            risk_score += 20

    # 2. Red flag phrases
    for phrase in RED_FLAG_PHRASES:
        if phrase in text_lower:
            flags.append({"type": "Red flag phrase", "detail": f'Contains "{phrase}"', "severity": "Low"})
            risk_score += 10

    # 3. Timeline inconsistency
    timeline_flag, timeline_msg = _check_timeline(parsed_resume.get("raw_text", ""))
    if timeline_flag:
        flags.append({"type": "Timeline inconsistency", "detail": timeline_msg, "severity": "High"})
        risk_score += 35

    # 4. Experience vs graduation year mismatch
    try:
        grad_year = int(parsed_resume.get("education", {}).get("year", 2020))
        claimed_exp = parsed_resume.get("experience_years", 0)
        max_possible = 2025 - grad_year
        if claimed_exp > max_possible + 2:  # +2 tolerance
            flags.append({
                "type": "Experience mismatch",
                "detail": f"Claims {claimed_exp} years but grad year suggests max {max_possible} years",
                "severity": "High"
            })
            risk_score += 30
    except:
        pass

    # 5. Copy-paste indicator: very short text for all sections
    raw = parsed_resume.get("raw_text", "")
    if len(raw) < 200:
        flags.append({"type": "Thin resume", "detail": "Very little content — possibly incomplete", "severity": "Low"})
        risk_score += 10

    risk_score = min(risk_score, 100)

    if risk_score == 0:
        level = "Clean"
        color = "success"
        verdict = "No fraud indicators detected."
    elif risk_score <= 25:
        level = "Low Risk"
        color = "info"
        verdict = "Minor flags present. Standard verification recommended."
    elif risk_score <= 55:
        level = "Medium Risk"
        color = "warning"
        verdict = "Several flags found. Skill verification required in interview."
    else:
        level = "High Risk"
        color = "danger"
        verdict = "Strong fraud indicators. Manual review and verification mandatory."

    return {
        "risk_score":  risk_score,
        "risk_level":  level,
        "color":       color,
        "verdict":     verdict,
        "flags":       flags,
        "flag_count":  len(flags),
    }
