import asyncio
import io
import os
from pathlib import Path
from typing import List, Optional

import pdfplumber
from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

load_dotenv()

from matcher import analyze_job_match, parse_resume
from scrapers import scrape_all_jobs

BASE_DIR = Path(__file__).parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"
RESUME_PATH = BASE_DIR / "resume.pdf"

app = FastAPI(title="ResumeMatch v1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

state = {
    "resume_text": None,
    "resume_parsed": None,
    "analyzed_jobs": [],
    "scan_status": "idle",
    "scan_message": "",
    "scan_progress": 0,
    "scan_total": 0,
    "prefs": {},
}

app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


@app.get("/")
async def root():
    return FileResponse(str(FRONTEND_DIR / "index.html"))


@app.post("/api/upload-resume")
async def upload_resume(file: UploadFile = File(...)):
    content = await file.read()
    RESUME_PATH.write_bytes(content)
    text = extract_pdf_text(content)
    state["resume_text"] = text
    state["resume_parsed"] = None
    return {"success": True, "filename": file.filename, "chars": len(text)}


@app.get("/api/resume-status")
async def resume_status():
    if state["resume_text"]:
        return {"has_resume": True, "parsed": state["resume_parsed"]}
    if RESUME_PATH.exists():
        text = extract_pdf_text(RESUME_PATH.read_bytes())
        state["resume_text"] = text
        return {"has_resume": True, "parsed": None}
    return {"has_resume": False}


class ScanPrefs(BaseModel):
    keywords: List[str] = ["strategy", "strategic", "business development", "partnerships",
                            "chief of staff", "go-to-market", "corporate development",
                            "business operations", "growth"]
    locations: List[str] = []
    remote: str = "any"  # any | remote | hybrid | onsite


@app.post("/api/scan")
async def start_scan(prefs: ScanPrefs, background_tasks: BackgroundTasks):
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise HTTPException(status_code=400, detail="ANTHROPIC_API_KEY not set in .env file.")
    if state["scan_status"] in ("scraping", "analyzing"):
        raise HTTPException(status_code=409, detail="Scan already in progress.")

    if not state["resume_text"]:
        if RESUME_PATH.exists():
            state["resume_text"] = extract_pdf_text(RESUME_PATH.read_bytes())
        else:
            raise HTTPException(status_code=400, detail="No resume found. Upload your resume first.")

    state["prefs"] = prefs.dict()
    state["scan_status"] = "scraping"
    state["scan_message"] = "Starting..."
    state["scan_progress"] = 0
    state["scan_total"] = 0
    state["analyzed_jobs"] = []

    background_tasks.add_task(run_scan)
    return {"started": True}


@app.get("/api/status")
async def get_status():
    return {
        "status": state["scan_status"],
        "message": state["scan_message"],
        "progress": state["scan_progress"],
        "total": state["scan_total"],
        "jobs_count": len(state["analyzed_jobs"]),
    }


@app.get("/api/jobs")
async def get_jobs():
    return {
        "jobs": state["analyzed_jobs"],
        "resume": state["resume_parsed"],
        "status": state["scan_status"],
    }


def extract_pdf_text(content: bytes) -> str:
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        return "\n".join(page.extract_text() or "" for page in pdf.pages)


def filter_by_location(jobs, locations: list, remote: str) -> list:
    loc_filters = [l.strip().lower() for l in locations if l.strip()]
    result = []
    for job in jobs:
        loc = (job.get("location") or "").lower()
        if remote == "remote" and "remote" not in loc:
            continue
        if remote == "hybrid" and "hybrid" not in loc:
            continue
        if remote == "onsite" and ("remote" in loc):
            continue
        if loc_filters and not any(lf in loc for lf in loc_filters) and "remote" not in loc:
            continue
        result.append(job)
    return result


async def run_scan():
    loop = asyncio.get_event_loop()
    prefs = state["prefs"]
    keywords = prefs.get("keywords", [])
    locations = prefs.get("locations", [])
    remote = prefs.get("remote", "any")

    try:
        def progress_cb(i, total, msg):
            state["scan_progress"] = i
            state["scan_total"] = total
            state["scan_message"] = msg

        state["scan_message"] = "Scraping job boards..."
        jobs = await loop.run_in_executor(
            None, lambda: scrape_all_jobs(keywords, progress_cb)
        )

        # Filter by location / remote preference
        if locations or remote != "any":
            jobs = filter_by_location(jobs, locations, remote)

        if not jobs:
            state["scan_status"] = "done"
            state["scan_message"] = "No matching roles found. Try adjusting your filters."
            return

        # Parse resume
        state["scan_status"] = "analyzing"
        state["scan_message"] = "Parsing your resume..."
        resume_parsed = await loop.run_in_executor(None, parse_resume, state["resume_text"])
        state["resume_parsed"] = resume_parsed

        # Analyze all matched jobs (already capped at 5 per company by scraper)
        jobs = jobs[:85]
        state["scan_total"] = len(jobs)
        analyzed = []
        for i, job in enumerate(jobs):
            state["scan_progress"] = i + 1
            state["scan_message"] = f"Analyzing {job['company']} — {job['title']} ({i+1}/{len(jobs)})"
            analysis = await loop.run_in_executor(
                None, analyze_job_match, state["resume_text"], job, prefs
            )
            analyzed.append({**job, **analysis})

        analyzed.sort(key=lambda x: x.get("match_score", 0), reverse=True)
        state["analyzed_jobs"] = analyzed
        state["scan_status"] = "done"
        state["scan_message"] = f"Done — {len(analyzed)} roles analyzed."

    except Exception as e:
        print(f"[main] Scan error: {e}")
        state["scan_status"] = "error"
        state["scan_message"] = str(e)
