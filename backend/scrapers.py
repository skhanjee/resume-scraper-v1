import requests
import time
from typing import List, Dict

DEFAULT_KEYWORDS = [
    "strategy", "strategic", "business development", "partnerships",
    "operations", "chief of staff", "go-to-market", "gtm",
    "business operations", "corporate development", "corp dev",
    "market strategy", "product strategy", "growth", "bizdev",
]

GREENHOUSE_COMPANIES = {
    "anthropic": "Anthropic",
    "openai": "OpenAI",
    "stripe": "Stripe",
    "figma": "Figma",
    "databricks": "Databricks",
    "scaleai": "Scale AI",
    "notion": "Notion",
    "airtable": "Airtable",
    "brex": "Brex",
}

LEVER_COMPANIES = {
    "netflix": "Netflix",
    "reddit": "Reddit",
    "coinbase": "Coinbase",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
}


_active_keywords = DEFAULT_KEYWORDS


def is_strategy_role(title: str, description: str = "") -> bool:
    return any(kw in title.lower() for kw in _active_keywords)


def scrape_greenhouse(company_token: str, company_name: str) -> List[Dict]:
    try:
        url = f"https://boards-api.greenhouse.io/v1/boards/{company_token}/jobs?content=true"
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        jobs = []
        for job in data.get("jobs", []):
            title = job.get("title", "")
            content = job.get("content", "")
            if is_strategy_role(title, content):
                offices = job.get("offices", [])
                location = ", ".join(o.get("name", "") for o in offices) if offices else "Remote"
                jobs.append({
                    "id": str(job.get("id")),
                    "title": title,
                    "company": company_name,
                    "location": location,
                    "url": job.get("absolute_url", ""),
                    "description": content[:3000],
                    "source": "greenhouse",
                })
        return jobs
    except Exception as e:
        print(f"[scrapers] Greenhouse {company_name} error: {e}")
        return []


def scrape_lever(company_token: str, company_name: str) -> List[Dict]:
    try:
        url = f"https://api.lever.co/v0/postings/{company_token}?mode=json"
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        jobs = []
        for job in data:
            title = job.get("text", "")
            description = job.get("descriptionPlain", "") or ""
            if is_strategy_role(title, description):
                location = job.get("categories", {}).get("location", "Remote") or "Remote"
                jobs.append({
                    "id": job.get("id", ""),
                    "title": title,
                    "company": company_name,
                    "location": location,
                    "url": job.get("hostedUrl", ""),
                    "description": description[:3000],
                    "source": "lever",
                })
        return jobs
    except Exception as e:
        print(f"[scrapers] Lever {company_name} error: {e}")
        return []


def scrape_apple() -> List[Dict]:
    try:
        url = "https://jobs.apple.com/api/role/search"
        payload = {"query": "strategy", "locale": "en-us", "page": 1}
        resp = requests.post(url, json=payload, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        jobs = []
        for job in data.get("searchResults", []):
            title = job.get("postingTitle", "")
            if is_strategy_role(title, job.get("jobSummary", "")):
                locations = job.get("locations", [])
                location = locations[0].get("name", "Unknown") if locations else "Unknown"
                job_id = job.get("positionId", "")
                jobs.append({
                    "id": job_id,
                    "title": title,
                    "company": "Apple",
                    "location": location,
                    "url": f"https://jobs.apple.com/en-us/details/{job_id}",
                    "description": job.get("jobSummary", ""),
                    "source": "apple",
                })
        return jobs
    except Exception as e:
        print(f"[scrapers] Apple error: {e}")
        return []


def scrape_google() -> List[Dict]:
    try:
        url = "https://careers.google.com/api/v3/search/?query=strategy&page_size=20&sort_by=relevance"
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        jobs = []
        for job in data.get("jobs", []):
            title = job.get("title", "")
            description = job.get("description", "")
            if is_strategy_role(title, description):
                locations = job.get("locations", [])
                location = locations[0].get("display", "Unknown") if locations else "Unknown"
                job_id = job.get("job_id", "")
                jobs.append({
                    "id": job_id,
                    "title": title,
                    "company": "Google",
                    "location": location,
                    "url": f"https://careers.google.com/jobs/results/{job_id}",
                    "description": description[:3000],
                    "source": "google",
                })
        return jobs
    except Exception as e:
        print(f"[scrapers] Google error: {e}")
        return []


def scrape_microsoft() -> List[Dict]:
    try:
        url = "https://jobs.careers.microsoft.com/global/en/search"
        params = {"q": "strategy", "l": "en_us", "pg": 1, "pgSz": 20, "o": "Relevance", "flt": "true"}
        resp = requests.get(url, params=params, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        jobs = []
        for job in data.get("operationResult", {}).get("result", {}).get("jobs", []):
            title = job.get("title", "")
            description = job.get("description", "")
            if is_strategy_role(title, description):
                job_id = job.get("jobId", "")
                jobs.append({
                    "id": str(job_id),
                    "title": title,
                    "company": "Microsoft",
                    "location": job.get("primaryLocation", "Unknown"),
                    "url": f"https://jobs.careers.microsoft.com/global/en/job/{job_id}",
                    "description": description[:3000],
                    "source": "microsoft",
                })
        return jobs
    except Exception as e:
        print(f"[scrapers] Microsoft error: {e}")
        return []


def scrape_nvidia() -> List[Dict]:
    try:
        url = "https://nvidia.wd5.myworkdayjobs.com/wday/cxs/nvidia/NVIDIAExternalCareerSite/jobs"
        payload = {"appliedFacets": {}, "limit": 20, "offset": 0, "searchText": "strategy"}
        resp = requests.post(url, json=payload, headers={**HEADERS, "Content-Type": "application/json"}, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        jobs = []
        for job in data.get("jobPostings", []):
            title = job.get("title", "")
            if is_strategy_role(title):
                external_path = job.get("externalPath", "")
                jobs.append({
                    "id": job.get("bulletFields", [""])[0] if job.get("bulletFields") else title,
                    "title": title,
                    "company": "NVIDIA",
                    "location": job.get("locationsText", "Unknown"),
                    "url": f"https://nvidia.wd5.myworkdayjobs.com/en-US/NVIDIAExternalCareerSite{external_path}",
                    "description": job.get("jobDescription", ""),
                    "source": "nvidia",
                })
        return jobs
    except Exception as e:
        print(f"[scrapers] NVIDIA error: {e}")
        return []


def scrape_amd() -> List[Dict]:
    try:
        url = "https://amd.wd1.myworkdayjobs.com/wday/cxs/amd/AMD/jobs"
        payload = {"appliedFacets": {}, "limit": 20, "offset": 0, "searchText": "strategy"}
        resp = requests.post(url, json=payload, headers={**HEADERS, "Content-Type": "application/json"}, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        jobs = []
        for job in data.get("jobPostings", []):
            title = job.get("title", "")
            if is_strategy_role(title):
                external_path = job.get("externalPath", "")
                jobs.append({
                    "id": title,
                    "title": title,
                    "company": "AMD",
                    "location": job.get("locationsText", "Unknown"),
                    "url": f"https://amd.wd1.myworkdayjobs.com/en-US/AMD{external_path}",
                    "description": job.get("jobDescription", ""),
                    "source": "amd",
                })
        return jobs
    except Exception as e:
        print(f"[scrapers] AMD error: {e}")
        return []


def scrape_all_jobs(keywords: List[str] = None, progress_callback=None) -> List[Dict]:
    global _active_keywords
    _active_keywords = [k.lower() for k in keywords] if keywords else DEFAULT_KEYWORDS

    all_jobs = []
    scrapers = []

    for token, name in GREENHOUSE_COMPANIES.items():
        scrapers.append(("greenhouse", token, name))
    for token, name in LEVER_COMPANIES.items():
        scrapers.append(("lever", token, name))
    scrapers += [
        ("apple", None, "Apple"),
        ("google", None, "Google"),
        ("microsoft", None, "Microsoft"),
        ("nvidia", None, "NVIDIA"),
        ("amd", None, "AMD"),
    ]

    total = len(scrapers)
    for i, (source, token, name) in enumerate(scrapers):
        if progress_callback:
            progress_callback(i, total, f"Scraping {name}...")

        if source == "greenhouse":
            jobs = scrape_greenhouse(token, name)
        elif source == "lever":
            jobs = scrape_lever(token, name)
        elif source == "apple":
            jobs = scrape_apple()
        elif source == "google":
            jobs = scrape_google()
        elif source == "microsoft":
            jobs = scrape_microsoft()
        elif source == "nvidia":
            jobs = scrape_nvidia()
        elif source == "amd":
            jobs = scrape_amd()
        else:
            jobs = []

        all_jobs.extend(jobs[:5])  # Cap 5 per company for diversity
        time.sleep(0.3)

    if progress_callback:
        progress_callback(total, total, "Scraping complete")

    # Deduplicate by title+company
    seen = set()
    unique = []
    for job in all_jobs:
        key = (job["company"], job["title"].lower().strip())
        if key not in seen:
            seen.add(key)
            unique.append(job)

    return unique
