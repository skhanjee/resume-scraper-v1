const API = '';
let pollInterval = null;
let jobs = [];
let selectedRemote = 'any';
let locations = [];
let selectedCompanies = new Set();
let allCompanies = [];
let showAllCompanies = false;

const DEFAULT_KEYWORDS = [
  'strategy', 'strategic', 'business development', 'partnerships',
  'chief of staff', 'go-to-market', 'corporate development',
  'business operations', 'growth'
];
let keywords = [...DEFAULT_KEYWORDS];

// Init
window.addEventListener('DOMContentLoaded', async () => {
  renderKeywordTags();
  renderLocationTags();
  await checkResumeStatus();
  await checkExistingScan();
});

// ── Keywords ──────────────────────────────────────────────
function renderKeywordTags() {
  const container = document.getElementById('keyword-tags');
  container.innerHTML = keywords.map((kw, i) => `
    <span class="kw-tag">
      ${esc(kw)}
      <button class="kw-remove" onclick="removeKeyword(${i})">&times;</button>
    </span>
  `).join('');
}

function removeKeyword(i) {
  keywords.splice(i, 1);
  renderKeywordTags();
}

function handleKeywordInput(e) {
  if (e.key === 'Enter') {
    const val = e.target.value.trim().toLowerCase();
    if (val && !keywords.includes(val)) {
      keywords.push(val);
      renderKeywordTags();
    }
    e.target.value = '';
  }
}

// ── Locations ─────────────────────────────────────────────
function renderLocationTags() {
  const container = document.getElementById('location-tags');
  container.innerHTML = locations.map((loc, i) => `
    <span class="kw-tag">
      ${esc(loc)}
      <button class="kw-remove" onclick="removeLocation(${i})">&times;</button>
    </span>
  `).join('');
}

function removeLocation(i) {
  locations.splice(i, 1);
  renderLocationTags();
}

function handleLocationInput(e) {
  if (e.key === 'Enter') {
    const val = e.target.value.trim();
    if (val && !locations.map(l => l.toLowerCase()).includes(val.toLowerCase())) {
      locations.push(val);
      renderLocationTags();
    }
    e.target.value = '';
  }
}

// ── Work style toggle ─────────────────────────────────────
function setRemote(btn) {
  document.querySelectorAll('.wfh-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  selectedRemote = btn.dataset.value;
}

// ── Resume ────────────────────────────────────────────────
async function checkResumeStatus() {
  try {
    const res = await fetch(`${API}/api/resume-status`);
    const data = await res.json();
    if (data.has_resume) setResumeLoaded(data.parsed);
  } catch (e) {
    console.error('Resume status check failed', e);
  }
}

async function uploadResume(event) {
  const file = event.target.files[0];
  if (!file) return;

  document.getElementById('resume-status-text').textContent = 'Uploading...';
  document.getElementById('resume-icon').textContent = '⏳';

  const formData = new FormData();
  formData.append('file', file);

  try {
    const res = await fetch(`${API}/api/upload-resume`, { method: 'POST', body: formData });
    const data = await res.json();
    if (data.success) setResumeLoaded(null);
    else document.getElementById('resume-status-text').textContent = 'Upload failed';
  } catch (e) {
    document.getElementById('resume-status-text').textContent = 'Upload error';
  }
}

function setResumeLoaded(parsed) {
  document.getElementById('resume-zone').classList.add('has-resume');
  document.getElementById('resume-icon').textContent = '✓';
  document.getElementById('resume-status-text').textContent = 'Resume loaded — click to replace';

  const infoEl = document.getElementById('resume-info');
  if (parsed && parsed.name) {
    infoEl.classList.remove('hidden');
    infoEl.innerHTML = `
      <strong>${esc(parsed.name)}</strong>
      ${parsed.current_role ? `<span>${esc(parsed.current_role)}</span><br>` : ''}
      ${parsed.experience_years ? `<span>${parsed.experience_years} yrs experience</span>` : ''}
    `;
  }
}

// ── Scan ──────────────────────────────────────────────────
async function checkExistingScan() {
  try {
    const res = await fetch(`${API}/api/status`);
    const data = await res.json();
    if (data.status === 'scraping' || data.status === 'analyzing') {
      document.getElementById('scan-btn').disabled = true;
      document.getElementById('scan-status').classList.remove('hidden');
      setProgress(data.progress, data.total, data.message);
      pollInterval = setInterval(pollStatus, 1200);
    } else if (data.status === 'done' && data.jobs_count > 0) {
      await loadJobs();
    }
  } catch (e) {
    console.error('Scan check failed', e);
  }
}

async function startScan() {
  const btn = document.getElementById('scan-btn');
  btn.disabled = true;
  document.getElementById('scan-status').classList.remove('hidden');
  setProgress(0, 1, 'Starting scan...');

  const prefs = {
    keywords: keywords.length ? keywords : DEFAULT_KEYWORDS,
    locations: locations,
    remote: selectedRemote,
  };

  try {
    const res = await fetch(`${API}/api/scan`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(prefs),
    });
    if (!res.ok) {
      const err = await res.json();
      alert(err.detail || 'Scan failed to start.');
      btn.disabled = false;
      return;
    }
  } catch (e) {
    alert('Could not connect to the server.');
    btn.disabled = false;
    return;
  }

  pollInterval = setInterval(pollStatus, 1200);
}

async function pollStatus() {
  try {
    const res = await fetch(`${API}/api/status`);
    const data = await res.json();
    setProgress(data.progress, data.total, data.message);

    if (data.status === 'done' || data.status === 'error') {
      clearInterval(pollInterval);
      pollInterval = null;
      document.getElementById('scan-btn').disabled = false;
      await loadJobs();
    }
  } catch (e) {
    console.error('Poll error', e);
  }
}

function setProgress(progress, total, message) {
  const pct = total > 0 ? Math.round((progress / total) * 100) : 0;
  document.getElementById('progress-bar').style.width = `${Math.max(pct, 3)}%`;
  document.getElementById('scan-message').textContent = message || '';
}

// ── Jobs ──────────────────────────────────────────────────
async function loadJobs() {
  try {
    const res = await fetch(`${API}/api/jobs`);
    const data = await res.json();
    jobs = data.jobs || [];
    if (data.resume) setResumeLoaded(data.resume);
    renderCompanyList();
    renderJobs();
  } catch (e) {
    console.error('Load jobs failed', e);
  }
}

function renderJobs() {
  const grid = document.getElementById('jobs-grid');
  const empty = document.getElementById('empty-state');
  const count = document.getElementById('results-count');

  if (!jobs || jobs.length === 0) {
    grid.classList.add('hidden');
    empty.classList.remove('hidden');
    count.classList.add('hidden');
    return;
  }

  const sortKey = document.getElementById('sort-select').value;
  const sorted = [...jobs].sort((a, b) => {
    if (sortKey === 'company') return (a.company || '').localeCompare(b.company || '');
    return (b[sortKey] || 0) - (a[sortKey] || 0);
  });

  const filtered = selectedCompanies.size > 0
    ? sorted.filter(j => selectedCompanies.has(j.company))
    : sorted;

  grid.innerHTML = filtered.map(jobCard).join('');
  grid.classList.remove('hidden');
  empty.classList.add('hidden');
  count.classList.remove('hidden');
  count.textContent = selectedCompanies.size > 0
    ? `${filtered.length} of ${jobs.length} roles`
    : `${jobs.length} roles found`;
}

// ── Company list ───────────────────────────────────────────
function renderCompanyList() {
  allCompanies = [...new Set(jobs.map(j => j.company))].sort();
  const section = document.getElementById('companies-section');
  const list = document.getElementById('company-list');

  if (!allCompanies.length) {
    section.classList.add('hidden');
    return;
  }
  section.classList.remove('hidden');

  const SHOW_MAX = 8;
  const toShow = showAllCompanies ? allCompanies : allCompanies.slice(0, SHOW_MAX);
  const hasMore = allCompanies.length > SHOW_MAX;

  list.innerHTML = toShow.map(c => `
    <li class="${selectedCompanies.has(c) ? 'active' : ''}" onclick="toggleCompany(${JSON.stringify(c)})">${esc(c)}</li>
  `).join('');

  if (hasMore) {
    const label = showAllCompanies ? 'Show less' : `+${allCompanies.length - SHOW_MAX} more`;
    list.innerHTML += `<li class="company-more" onclick="toggleShowAllCompanies()">${label}</li>`;
  }
}

function toggleCompany(name) {
  if (selectedCompanies.has(name)) selectedCompanies.delete(name);
  else selectedCompanies.add(name);
  renderCompanyList();
  renderJobs();
}

function toggleShowAllCompanies() {
  showAllCompanies = !showAllCompanies;
  renderCompanyList();
}

function jobCard(job) {
  const score = job.match_score || 0;
  const likelihood = job.interview_likelihood || 'Unknown';
  const likelihoodPct = job.interview_likelihood_pct || 0;
  const rec = job.recommendation || 'Maybe';
  const skills = job.matched_skills || [];
  const gaps = job.gaps || [];
  const wfh = job.wfh_compatible;

  const scoreClass = score >= 70 ? 'high' : score >= 45 ? 'mid' : 'low';
  const likelihoodClass = likelihood.toLowerCase().replace(' ', '-');
  const recClass = { 'Strong Apply': 'strong-apply', 'Apply': 'apply', 'Maybe': 'maybe', 'Skip': 'skip' }[rec] || 'maybe';

  const skillTags = skills.slice(0, 4).map(s => `<span class="skill-tag">${esc(s)}</span>`).join('');
  const gapTags = gaps.slice(0, 2).map(g => `<span class="gap-tag">&#8722; ${esc(g)}</span>`).join('');
  const wfhBadge = wfh === true
    ? `<span class="wfh-badge wfh-yes">WFH Compatible</span>`
    : wfh === false
      ? `<span class="wfh-badge wfh-no">On-site</span>`
      : '';

  return `
    <div class="job-card">
      <div class="card-header">
        <div>
          <div class="card-company">${esc(job.company)}</div>
          <div class="card-title">${esc(job.title)}</div>
          <div class="card-meta">
            <span>&#128205; ${esc(job.location || 'Unknown')}</span>
            ${wfhBadge}
          </div>
        </div>
        <span class="likelihood-badge likelihood-${likelihoodClass}">${esc(likelihood)}</span>
      </div>

      <div>
        <div class="score-row">
          <span class="score-label">Match</span>
          <div class="score-track"><div class="score-fill ${scoreClass}" style="width:${score}%"></div></div>
          <span class="score-pct" style="color:${scoreColor(score)}">${score}%</span>
        </div>
        <div class="score-row" style="margin-top:6px">
          <span class="score-label">Interview</span>
          <div class="score-track"><div class="score-fill ${scoreClass}" style="width:${likelihoodPct}%"></div></div>
          <span class="score-pct" style="color:${scoreColor(likelihoodPct)}">${likelihoodPct}%</span>
        </div>
      </div>

      ${skillTags || gapTags ? `<div class="skills-row">${skillTags}${gapTags}</div>` : ''}

      ${job.reasoning ? `<div class="card-reasoning">${esc(job.reasoning)}</div>` : ''}

      <div class="card-footer">
        <span class="rec-badge rec-${recClass}">${esc(rec)}</span>
        ${job.url ? `<a class="apply-btn" href="${esc(job.url)}" target="_blank" rel="noopener">Apply &rarr;</a>` : ''}
      </div>
    </div>
  `;
}

function scoreColor(pct) {
  if (pct >= 70) return '#10b981';
  if (pct >= 45) return '#f59e0b';
  return '#ef4444';
}

function esc(str) {
  return String(str || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}
