"""
FastAPI web interface for isolint.

Provides a minimal REST API and HTML dashboard for metadata
validation, suggestion, and FAIR scoring. Designed for local
use — no external API calls, no telemetry.

Endpoints:
  GET  /           — HTML dashboard
  POST /validate   — validate uploaded file(s)
  POST /suggest    — get improvement suggestions
  POST /fair       — compute FAIR score
  GET  /health     — health check
"""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse

from isolint.engine import ValidationConfig, ValidationEngine
from isolint.fair import FAIRScorer
from isolint.suggest import suggest_improvements

logger = logging.getLogger(__name__)

app = FastAPI(
    title="isolint",
    description="ISO 19115-2, CF-1.8, and ACDD-1.3 metadata linter",
    version="1.0.0",
)


DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>isolint — Metadata Linter</title>
  <style>
    :root { --bg: #0d1117; --fg: #c9d1d9; --accent: #58a6ff; --border: #30363d;
            --green: #3fb950; --red: #f85149; --yellow: #d29922; }
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
           background: var(--bg); color: var(--fg); padding: 2rem; }
    h1 { color: var(--accent); margin-bottom: 0.5rem; }
    .subtitle { color: #8b949e; margin-bottom: 2rem; }
    .upload-zone { border: 2px dashed var(--border); border-radius: 8px;
                   padding: 3rem; text-align: center; margin: 1rem 0;
                   transition: border-color 0.2s; cursor: pointer; }
    .upload-zone:hover { border-color: var(--accent); }
    .upload-zone input { display: none; }
    .btn { background: var(--accent); color: var(--bg); border: none;
           padding: 0.6rem 1.5rem; border-radius: 6px; cursor: pointer;
           font-size: 1rem; margin: 0.5rem 0.25rem; }
    .btn:hover { opacity: 0.9; }
    .btn-secondary { background: var(--border); color: var(--fg); }
    #results { margin-top: 2rem; }
    .finding { padding: 0.8rem; margin: 0.5rem 0; border-radius: 6px;
               border-left: 4px solid; }
    .finding.error { border-color: var(--red); background: rgba(248,81,73,0.1); }
    .finding.warning { border-color: var(--yellow); background: rgba(210,153,34,0.1); }
    .finding.info { border-color: var(--accent); background: rgba(88,166,255,0.1); }
    .tag { display: inline-block; padding: 0.15rem 0.5rem; border-radius: 12px;
           font-size: 0.75rem; font-weight: 600; }
    .tag-error { background: var(--red); color: #fff; }
    .tag-warning { background: var(--yellow); color: #000; }
    .tag-info { background: var(--accent); color: #000; }
    .summary { display: flex; gap: 1rem; margin: 1rem 0; }
    .stat { background: var(--border); padding: 1rem; border-radius: 6px;
            text-align: center; flex: 1; }
    .stat .number { font-size: 2rem; font-weight: bold; }
    pre { background: #161b22; padding: 1rem; border-radius: 6px;
          overflow-x: auto; font-size: 0.85rem; margin: 0.5rem 0; }
    .fair-bar { height: 20px; border-radius: 10px; background: var(--border);
                overflow: hidden; margin: 0.3rem 0; }
    .fair-fill { height: 100%; border-radius: 10px; transition: width 0.5s; }
  </style>
</head>
<body>
  <h1>isolint</h1>
  <p class="subtitle">ISO 19115-2 / CF-1.8 / ACDD-1.3 Metadata Linter</p>

  <div class="upload-zone" onclick="document.getElementById('fileInput').click()">
    <p>Drop metadata files here or click to upload</p>
    <p style="color:#8b949e;font-size:0.85rem;margin-top:0.5rem">
      Supports .xml (ISO 19115-2) and .nc (CF/ACDD) files
    </p>
    <input type="file" id="fileInput" multiple accept=".xml,.nc,.sha256">
  </div>

  <div>
    <button class="btn" onclick="runValidation()">Validate</button>
    <button class="btn btn-secondary" onclick="runSuggest()">Suggest</button>
    <button class="btn btn-secondary" onclick="runFAIR()">FAIR Score</button>
  </div>

  <div id="results"></div>

  <script>
    const fileInput = document.getElementById('fileInput');
    const results = document.getElementById('results');

    async function uploadAndPost(endpoint) {
      const files = fileInput.files;
      if (!files.length) { results.innerHTML = '<p>No files selected.</p>'; return null; }
      const form = new FormData();
      for (const f of files) form.append('files', f);
      const resp = await fetch(endpoint, { method: 'POST', body: form });
      return await resp.json();
    }

    async function runValidation() {
      const data = await uploadAndPost('/validate');
      if (!data) return;
      let html = '<h2>Validation Results</h2>';
      html += `<div class="summary">
        <div class="stat"><div class="number" style="color:${data.passed?'var(--green)':'var(--red)'}">
          ${data.passed?'PASS':'FAIL'}</div><div>Status</div></div>
        <div class="stat"><div class="number">${data.summary.errors}</div><div>Errors</div></div>
        <div class="stat"><div class="number">${data.summary.warnings}</div><div>Warnings</div></div>
        <div class="stat"><div class="number">${data.summary.info}</div><div>Info</div></div>
      </div>`;
      for (const f of data.findings) {
        html += `<div class="finding ${f.severity}">
          <span class="tag tag-${f.severity}">${f.severity.toUpperCase()}</span>
          <strong> ${f.message}</strong>
          ${f.source ? '<br><small>Source: '+f.source+'</small>' : ''}
          ${f.xpath ? '<br><small>XPath: <code>'+f.xpath+'</code></small>' : ''}
          ${f.suggestion ? '<br><small>Fix: '+f.suggestion+'</small>' : ''}
        </div>`;
      }
      results.innerHTML = html;
    }

    async function runSuggest() {
      const data = await uploadAndPost('/suggest');
      if (!data) return;
      let html = '<h2>Improvement Suggestions</h2>';
      for (const s of data.suggestions) {
        const color = {high:'var(--red)',medium:'var(--yellow)',low:'var(--green)'}[s.priority];
        html += `<div class="finding" style="border-color:${color}">
          <strong>[${s.priority.toUpperCase()}] ${s.title}</strong>
          <br>${s.description}
          ${s.xpath ? '<br><small>XPath: <code>'+s.xpath+'</code></small>' : ''}
        </div>`;
      }
      results.innerHTML = html;
    }

    async function runFAIR() {
      const data = await uploadAndPost('/fair');
      if (!data) return;
      const s = data.score;
      let html = `<h2>FAIR Score: ${(s.overall*100).toFixed(0)}% (Grade: ${s.grade})</h2>`;
      for (const [k,v] of [['Findable',s.findable],['Accessible',s.accessible],
                            ['Interoperable',s.interoperable],['Reusable',s.reusable]]) {
        const pct = (v*100).toFixed(0);
        const color = v>=0.8?'var(--green)':v>=0.6?'var(--yellow)':'var(--red)';
        html += `<p><strong>${k}: ${pct}%</strong></p>
          <div class="fair-bar"><div class="fair-fill"
            style="width:${pct}%;background:${color}"></div></div>`;
      }
      results.innerHTML = html;
    }
  </script>
</body>
</html>"""


@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """Serve the HTML dashboard."""
    return DASHBOARD_HTML


@app.post("/validate")
async def validate_files(files: list[UploadFile] = File(...)):
    """Validate uploaded metadata files."""
    engine = ValidationEngine(ValidationConfig())

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        for upload in files:
            dest = tmp / upload.filename
            content = await upload.read()
            dest.write_bytes(content)

        report = engine.validate_directory(tmp)

    return JSONResponse(content=report.to_dict())


@app.post("/suggest")
async def suggest_files(files: list[UploadFile] = File(...)):
    """Get improvement suggestions for uploaded files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        for upload in files:
            dest = tmp / upload.filename
            content = await upload.read()
            dest.write_bytes(content)

        suggestions = suggest_improvements(tmp)

    return JSONResponse(content={
        "suggestions": [s.to_dict() for s in suggestions],
    })


@app.post("/fair")
async def fair_score(files: list[UploadFile] = File(...)):
    """Compute FAIR score for uploaded files."""
    scorer = FAIRScorer()
    scores = []

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        for upload in files:
            dest = tmp / upload.filename
            content = await upload.read()
            dest.write_bytes(content)

        for xml in tmp.glob("*.xml"):
            scores.append(scorer.score_xml(xml))
        for nc in tmp.glob("*.nc"):
            scores.append(scorer.score_netcdf(nc))

    if not scores:
        return JSONResponse(content={"score": {"overall": 0, "grade": "F"}})

    # Average scores if multiple files
    avg = scores[0]
    if len(scores) > 1:
        avg.findable = sum(s.findable for s in scores) / len(scores)
        avg.accessible = sum(s.accessible for s in scores) / len(scores)
        avg.interoperable = sum(s.interoperable for s in scores) / len(scores)
        avg.reusable = sum(s.reusable for s in scores) / len(scores)

    return JSONResponse(content={"score": avg.to_dict()})


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "version": "1.0.0"}
