import json
import os
import re
from datetime import datetime, timedelta, timezone
import yaml
from bs4 import BeautifulSoup
from adapters.base import JobPosting

profile = yaml.safe_load(open("profile.yaml"))

PROFILE_SUMMARY = f"""
Role: {profile['role']}
Experience: {profile['experience_years']} years
Skills: {', '.join(profile['skills'])}
Preferences: {profile.get('summary', '')}
Not interested in: {', '.join(profile.get('not_interested_in', []))}
"""


def _contains_word(text: str, phrase: str) -> bool:
    """Whole-word/phrase match so 'intern' doesn't hit 'internal'/'international'."""
    return re.search(rf"\b{re.escape(phrase.lower())}\b", text) is not None


def _job_full_text(job: JobPosting) -> str:
    """Full scraped job post as plain text: title + HTML description, tags stripped."""
    description_text = BeautifulSoup(job.description or "", "html.parser").get_text(" ")
    return f"{job.title} {description_text}".lower()


def content_filter(job: JobPosting) -> bool:
    """Gate applied against the FULL scraped job post (title + description HTML), not just the title."""
    text = _job_full_text(job)

    must_include = profile.get("content_must_include", [])
    if must_include and not any(_contains_word(text, kw) for kw in must_include):
        return False

    must_include_any = profile.get("content_must_include_any_of", [])
    if must_include_any and not any(_contains_word(text, kw) for kw in must_include_any):
        return False

    must_not_include = profile.get("content_must_not_include", [])
    if any(_contains_word(text, kw) for kw in must_not_include):
        return False

    return True


# Matches "N years" / "N+ years" regardless of what follows, e.g.
# "8+ years of backend engineering", "2+ years building products",
# "5+ years in a similar role", "2 years of experience".
_EXPERIENCE_RE = re.compile(
    r"(\d+)\+?\s*years?\b",
    re.IGNORECASE,
)


def _min_required_experience_years(text: str):
    """Smallest 'N years ... experience' figure found in text, or None if unstated."""
    years = [int(m.group(1)) for m in _EXPERIENCE_RE.finditer(text)]
    return min(years) if years else None


def experience_filter(job: JobPosting) -> bool:
    """Reject jobs whose stated minimum experience requirement exceeds the profile cap.

    Jobs that don't mention a number of years at all are allowed through, since
    intern/new-grad postings frequently omit an explicit figure.
    """
    max_years = profile.get("max_experience_years")
    if max_years is None:
        return True

    text = _job_full_text(job)
    required = _min_required_experience_years(text)
    if required is None:
        return True

    return required <= max_years


def recency_filter(job: JobPosting) -> bool:
    """Keep jobs posted within the last N hours. Jobs with no known post date
    (e.g. generic career pages that don't expose one) are let through."""
    max_hours = profile.get("max_hours_since_posted")
    if max_hours is None or job.date_posted is None:
        return True

    date_posted = job.date_posted
    if date_posted.tzinfo is None:
        date_posted = date_posted.replace(tzinfo=timezone.utc)

    age = datetime.now(timezone.utc) - date_posted
    return age <= timedelta(hours=max_hours)


def location_filter(job: JobPosting) -> bool:
    """Keep jobs whose location text matches one of the allowed locations.
    Jobs with no location text at all (e.g. some generic career pages) are
    let through, since there's nothing to check against."""
    allowed = profile.get("allowed_locations")
    if not allowed:
        return True

    location = (job.location or "").strip().lower()
    if not location:
        return True

    return any(_contains_word(location, loc) for loc in allowed)


def keyword_match(job: JobPosting) -> float:
    """Fast pre-filter using keyword presence. Returns 0.0-1.0."""
    keywords = profile.get("keywords", [])
    if not keywords:
        return 1.0
    text = _job_full_text(job)
    hits = sum(1 for kw in keywords if kw.lower() in text)
    return hits / len(keywords)


def llm_match(job: JobPosting) -> tuple[float, str]:
    """LLM-powered match score. Returns (score, reason)."""
    try:
        from google import genai
        client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

        prompt = f"""Rate how well this job matches my profile. Reply with valid JSON only, no markdown.
Format: {{"score": 0.85, "reason": "one short sentence"}}

Score guide:
- 0.9+ = near-perfect match
- 0.7-0.9 = good match, apply
- 0.5-0.7 = partial match, worth reviewing
- below 0.5 = not a match

MY PROFILE:
{PROFILE_SUMMARY}

JOB TITLE: {job.title}
COMPANY: {job.company}
LOCATION: {job.location}
DESCRIPTION (first 600 chars):
{BeautifulSoup(job.description or "", "html.parser").get_text(" ")[:600]}
"""
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        text = response.text.strip()
        if text.startswith("```"):
            text = text.strip("`")
            if text.startswith("json"):
                text = text[4:]
        result = json.loads(text.strip())
        return float(result["score"]), result.get("reason", "")

    except Exception as e:
        print(f"[Matcher] LLM error: {e}")
        return 0.0, "LLM error"
