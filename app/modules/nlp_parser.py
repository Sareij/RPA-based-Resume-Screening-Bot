"""
Module 2: Semantic NLP Resume Parser
Understands resume content contextually, not just keyword matching.
Extracts: skills, experience, education, projects, certifications
"""

import re
from datetime import datetime

# ── Skill taxonomy (semantic groups) ──────────────────────────────────────────
SKILL_TAXONOMY = {
    "Python":        ["python", "django", "flask", "fastapi", "pandas", "numpy",
                      "scikit-learn", "sklearn", "matplotlib", "seaborn", "pytest",
                      "pydantic", "celery", "sqlalchemy"],
    "JavaScript":    ["javascript", "js", "typescript", "ts", "node", "nodejs",
                      "react", "reactjs", "vue", "vuejs", "angular", "express",
                      "nextjs", "nuxt", "jquery", "webpack"],
    "Java":          ["java", "spring", "springboot", "hibernate", "maven",
                      "gradle", "junit", "struts", "j2ee", "jpa"],
    "C/C++":         ["c++", "cpp", "c language", "stl", "opengl", "embedded c"],
    "Machine Learning": ["machine learning", "ml", "deep learning", "dl",
                         "neural network", "cnn", "rnn", "lstm", "transformer",
                         "xgboost", "lightgbm", "random forest", "svm",
                         "tensorflow", "keras", "pytorch", "huggingface"],
    "NLP":           ["nlp", "natural language", "spacy", "nltk", "bert",
                      "gpt", "text mining", "sentiment analysis", "ner",
                      "word2vec", "tokenization"],
    "Data Science":  ["data science", "data analysis", "statistics", "r language",
                      "tableau", "power bi", "excel", "data visualization",
                      "hypothesis testing", "regression", "classification"],
    "SQL/Database":  ["sql", "mysql", "postgresql", "postgres", "sqlite",
                      "oracle", "mongodb", "redis", "cassandra", "elasticsearch",
                      "nosql", "database"],
    "Cloud/DevOps":  ["aws", "azure", "gcp", "google cloud", "docker",
                      "kubernetes", "k8s", "jenkins", "ci/cd", "terraform",
                      "ansible", "linux", "bash", "git", "github", "gitlab"],
    "Web Dev":       ["html", "css", "html5", "css3", "bootstrap", "tailwind",
                      "rest api", "graphql", "api", "mvc", "web development"],
    "Mobile":        ["android", "ios", "flutter", "react native", "kotlin",
                      "swift", "mobile development"],
    "RPA":           ["uipath", "automation anywhere", "blue prism", "rpa",
                      "robotic process automation", "workflow automation"],
    "Cybersecurity": ["cybersecurity", "security", "penetration testing",
                      "ethical hacking", "owasp", "firewall", "encryption"],
    "Soft Skills":   ["leadership", "communication", "teamwork", "problem solving",
                      "critical thinking", "agile", "scrum", "project management"],
}

# Contextual skill inference: if these phrases appear → infer these skills
CONTEXT_INFERENCE = [
    (["built ml model", "trained model", "deployed model"],                 ["Machine Learning", "Python"]),
    (["data pipeline", "etl pipeline", "built pipeline"],                   ["Data Science", "SQL/Database"]),
    (["rest api", "built api", "developed api", "api integration"],         ["Web Dev", "Python"]),
    (["automated", "automation script", "scripted"],                        ["Python"]),
    (["sentiment analysis", "text classification", "named entity"],         ["NLP", "Machine Learning"]),
    (["android app", "mobile app", "play store"],                           ["Mobile", "Java"]),
    (["cloud deployment", "deployed on aws", "hosted on azure"],            ["Cloud/DevOps"]),
    (["dockerized", "containerized", "docker container"],                   ["Cloud/DevOps"]),
]

# Education keywords
DEGREE_PATTERNS = {
    "B.E / B.Tech": r"\b(b\.?e|b\.?tech|bachelor of engineering|bachelor of technology)\b",
    "M.E / M.Tech": r"\b(m\.?e|m\.?tech|master of engineering|master of technology)\b",
    "MCA":          r"\b(mca|master of computer application)\b",
    "BCA":          r"\b(bca|bachelor of computer application)\b",
    "B.Sc":         r"\b(b\.?sc|bachelor of science)\b",
    "MBA":          r"\b(mba|master of business)\b",
    "PhD":          r"\b(ph\.?d|doctorate|doctor of)\b",
}

CGPA_PATTERN   = r"(?:cgpa|gpa|score|percentage|marks)[:\s]*(\d{1,2}(?:\.\d{1,2})?)"
EMAIL_PATTERN  = r"[\w\.\-]+@[\w\.\-]+\.\w{2,}"
PHONE_PATTERN  = r"(?:\+91[\s\-]?)?[6-9]\d{9}"
LINKEDIN_PAT   = r"linkedin\.com/in/[\w\-]+"
GITHUB_PAT     = r"github\.com/[\w\-]+"

YEAR_PATTERN   = r"\b(20\d{2})\b"


def parse_resume(text):
    """
    Full semantic parse of resume text.
    Returns structured dict with all extracted fields.
    """
    text_lower = text.lower()

    result = {
        "raw_text":      text,
        "name":          _extract_name(text),
        "email":         _extract_email(text),
        "phone":         _extract_phone(text),
        "linkedin":      _extract_pattern(text, LINKEDIN_PAT),
        "github":        _extract_pattern(text, GITHUB_PAT),
        "education":     _extract_education(text, text_lower),
        "skills":        _extract_skills_semantic(text_lower),
        "experience_years": _extract_experience_years(text, text_lower),
        "certifications":_extract_certifications(text_lower),
        "projects":      _extract_projects(text),
        "languages_known": _extract_languages(text_lower),
    }
    result["skill_count"] = len(result["skills"])
    result["has_github"]  = bool(result["github"])
    result["has_linkedin"] = bool(result["linkedin"])
    return result


# ── Private helpers ────────────────────────────────────────────────────────────

def _extract_name(text):
    """Heuristic: first non-empty line that looks like a name."""
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    for line in lines[:5]:
        # Name: 2-4 words, only letters and spaces, no digits
        words = line.split()
        if 2 <= len(words) <= 4 and all(w.replace('.','').isalpha() for w in words):
            if len(line) < 50:
                return line.title()
    return "Unknown"

def _extract_email(text):
    m = re.search(EMAIL_PATTERN, text)
    return m.group(0) if m else ""

def _extract_phone(text):
    m = re.search(PHONE_PATTERN, text)
    return m.group(0) if m else ""

def _extract_pattern(text, pattern):
    m = re.search(pattern, text, re.IGNORECASE)
    return m.group(0) if m else ""

def _extract_education(text, text_lower):
    edu = {"degree": "", "cgpa": "", "college": "", "year": ""}
    for degree, pattern in DEGREE_PATTERNS.items():
        if re.search(pattern, text_lower):
            edu["degree"] = degree
            break
    m = re.search(CGPA_PATTERN, text_lower)
    if m:
        edu["cgpa"] = m.group(1)
    years = re.findall(YEAR_PATTERN, text)
    if years:
        edu["year"] = max(years)  # Graduation year = latest year mentioned
    # College: line containing "college", "university", "institute"
    for line in text.split('\n'):
        ll = line.lower()
        if any(k in ll for k in ["college", "university", "institute", "iit", "nit", "anna"]):
            edu["college"] = line.strip()[:80]
            break
    return edu

def _extract_skills_semantic(text_lower):
    """
    Two-pass skill extraction:
    Pass 1: Direct keyword match from taxonomy
    Pass 2: Contextual inference from phrases
    """
    found_skills = set()

    # Pass 1: keyword match
    for skill_name, keywords in SKILL_TAXONOMY.items():
        for kw in keywords:
            if kw in text_lower:
                found_skills.add(skill_name)
                break

    # Pass 2: context inference
    for context_phrases, inferred_skills in CONTEXT_INFERENCE:
        if any(phrase in text_lower for phrase in context_phrases):
            for sk in inferred_skills:
                found_skills.add(sk)

    return sorted(list(found_skills))

def _extract_experience_years(text, text_lower):
    """Estimate total years of experience from date ranges and explicit mentions."""
    # Explicit mention: "X years of experience"
    m = re.search(r"(\d+\.?\d*)\s*\+?\s*years?\s+(?:of\s+)?(?:experience|exp)", text_lower)
    if m:
        return float(m.group(1))

    # Count date ranges like "Jan 2020 – Dec 2022" or "2019 - 2022"
    years = list(map(int, re.findall(YEAR_PATTERN, text)))
    if len(years) >= 2:
        span = max(years) - min(years)
        # Freshers: span 0-1, Early: 1-3, Mid: 3-6
        return min(span, 10)  # cap at 10
    return 0

def _extract_certifications(text_lower):
    """Look for certifications and online courses."""
    cert_keywords = [
        "aws certified", "azure certified", "google certified",
        "coursera", "udemy", "nptel", "coursera", "edx",
        "certification", "certified", "course completed",
        "google analytics", "hackerrank", "leetcode",
        "microsoft certified", "oracle certified",
    ]
    found = []
    for kw in cert_keywords:
        if kw in text_lower:
            found.append(kw.title())
    return list(set(found))

def _extract_projects(text):
    """Extract project names and descriptions."""
    projects = []
    lines = text.split('\n')
    in_projects = False
    for i, line in enumerate(lines):
        ll = line.lower().strip()
        if re.search(r'\b(projects?|works?|portfolio)\b', ll) and len(ll) < 30:
            in_projects = True
            continue
        if in_projects:
            if re.search(r'\b(education|skills|experience|certif|contact)\b', ll) and len(ll) < 30:
                in_projects = False
                continue
            if line.strip() and len(line.strip()) > 10:
                projects.append(line.strip())
        if len(projects) >= 6:
            break
    return projects[:6]

def _extract_languages(text_lower):
    """Extract spoken/programming languages."""
    spoken = []
    for lang in ["english", "tamil", "hindi", "telugu", "kannada", "malayalam",
                 "french", "german", "arabic", "chinese"]:
        if lang in text_lower:
            spoken.append(lang.title())
    return spoken
