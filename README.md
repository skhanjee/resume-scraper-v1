# ResumeMatch v1.0

A job board scraper that uses Claude AI to rank roles against your resume by match score and interview likelihood.

## Features

- **Multi-source scraping** — pulls jobs from Greenhouse, Lever, Apple, Google, Microsoft, NVIDIA, AMD, and more
- **AI-powered matching** — Claude analyzes each role against your resume and scores fit
- **Ranked results** — sorted by match score or interview likelihood
- **Filters** — keyword, location, and work style (remote / hybrid / on-site)
- **Resume upload** — drag and drop PDF; persists across sessions

## Stack

- **Backend**: FastAPI + pdfplumber + Anthropic Claude API
- **Frontend**: Vanilla HTML/CSS/JS

## Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Add your Anthropic API key
cp .env.example .env
# Edit .env and paste your key

# Run
cd backend
uvicorn main:app --reload
```

Open [http://localhost:8000](http://localhost:8000), upload your resume, set preferences, and click **Scan Jobs**.

## Notes

- Scans up to 85 roles per run (capped at 5 per company for diversity)
- `GoogleService-Info.plist` is excluded from this repo — add your own from the Firebase console
