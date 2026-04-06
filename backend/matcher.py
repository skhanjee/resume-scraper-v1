import json
import os
import re

import requests

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
MODEL = "claude-sonnet-4-6"


def _call_claude(prompt: str, max_tokens: int = 1024) -> str:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    body = {
        "model": MODEL,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }
    resp = requests.post(ANTHROPIC_API_URL, headers=headers, json=body, timeout=60)
    resp.raise_for_status()
    return resp.json()["content"][0]["text"]


def parse_resume(resume_text: str) -> dict:
    prompt = f"""Extract structured info from this resume. Return ONLY valid JSON, no other text.

{{
  "name": "...",
  "current_role": "...",
  "experience_years": <number>,
  "education": "...",
  "skills": ["skill1", "skill2"],
  "industries": ["industry1"],
  "summary": "2-3 sentence professional summary focused on strategy/business skills"
}}

RESUME:
{resume_text[:5000]}"""

    text = _call_claude(prompt)
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return {"name": "Unknown", "summary": text[:200], "skills": [], "experience_years": 0}


def analyze_job_match(resume_text: str, job: dict, prefs: dict = None) -> dict:
    prefs = prefs or {}
    locations = prefs.get("locations", [])
    location_note = ""
    if locations or prefs.get("remote"):
        loc_str = ", ".join(locations) if locations else "flexible"
        location_note = f"Candidate prefers: {loc_str} location, {prefs.get('remote', 'any')} work style."

    prompt = f"""You are an expert career advisor evaluating a candidate for a role at a top tech company.

CANDIDATE RESUME:
{resume_text[:3500]}

{location_note}

JOB:
Company: {job['company']}
Title: {job['title']}
Location: {job['location']}
Description: {job['description'][:2000]}

Evaluate this match honestly. Return ONLY valid JSON, no other text:

{{
  "match_score": <0-100>,
  "interview_likelihood": "<Low|Medium|High|Very High>",
  "interview_likelihood_pct": <0-100>,
  "matched_skills": ["up to 5 specific matched skills/experiences"],
  "gaps": ["up to 3 key gaps"],
  "reasoning": "2-3 sentences on fit, being specific to this role and company",
  "recommendation": "<Skip|Maybe|Apply|Strong Apply>",
  "wfh_compatible": <true|false>
}}

Scoring guide:
- 80-100: Exceptional fit, strong apply
- 60-79: Good fit, apply
- 40-59: Partial fit, maybe
- 0-39: Weak fit, skip

Be realistic. Consider years of experience, industry background, and role requirements.
For wfh_compatible, assess if the role appears to support remote or hybrid work based on the job description."""

    try:
        text = _call_claude(prompt, max_tokens=1024)
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
    except Exception as e:
        print(f"[matcher] Claude error: {e}")

    return {
        "match_score": 0,
        "interview_likelihood": "Unknown",
        "interview_likelihood_pct": 0,
        "matched_skills": [],
        "gaps": [],
        "reasoning": "Analysis failed.",
        "recommendation": "Maybe",
        "wfh_compatible": False,
    }
