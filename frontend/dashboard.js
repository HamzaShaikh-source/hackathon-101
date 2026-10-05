(function () {
  'use strict';

  const params = new URLSearchParams(window.location.search);
  const jobId = params.get('job_id') || params.get('jobId') || window.localStorage.getItem('job_id');
  const state = { candidates: [], queue: [], busy: false, editingCandidate: null };
  const $ = (selector) => document.querySelector(selector);

  $('#jobIdLabel').textContent = jobId || 'Not selected';

  function setNotice(message, type) {
    const notice = $('#notice');
    notice.textContent = message || '';
    notice.className = message ? `notice show ${type || 'success'}` : 'notice';
  }

  function escapeHtml(value) {
    return String(value ?? '').replace(/[&<>'"]/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[char]));
  }

  function initials(name) {
    return String(name || '?').split(/\s+/).filter(Boolean).slice(0, 2).map((word) => word[0]).join('').toUpperCase() || '?';
  }

  function percent(value) {
    const number = Number(value);
    return Number.isFinite(number) ? `${Math.round(number * 100)}%` : '—';
  }

  function labelForRequirement(id) {
    return String(id || 'Requirement').replace(/[_-]+/g, ' ').replace(/\b\w/g, (letter) => letter.toUpperCase());
  }

  function normalizeEvidence(candidate) {
    const items = [];
    (candidate.matches || []).forEach((match) => {
      (match.evidence || []).forEach((evidence, evidenceIndex) => {
        const status = evidence.status || match.status || 'missing';
        if (status === 'uncertain' || status === 'contradicted') {
          items.push({ candidate, match, evidence, evidenceIndex, status, confidence: Number(evidence.confidence) || 0 });
        }
      });
    });
    return items;
  }

  function renderSummary() {
    $('#candidateCount').textContent = state.candidates.length;
    $('#topScore').textContent = state.candidates.length ? percent(state.candidates[0].score) : '—';
    $('#queueCount').textContent = state.queue.length;
  }

  function renderCandidates() {
    const rows = $('#candidateRows');
    if (!state.candidates.length) {
      rows.innerHTML = '<tr><td colspan="5" class="empty">No scored candidates found for this job.</td></tr>';
      return;
    }
    rows.innerHTML = state.candidates.map((candidate, index) => {
      const needsReview = normalizeEvidence(candidate).length;
      const skills = (candidate.skills || []).slice(0, 5).map((skill) => `<span class="chip">${escapeHtml(skill)}</span>`).join('') || '<span class="confidence">No extracted skills</span>';
      return `<tr>
        <td><span class="rank">${index + 1}</span></td>
        <td><div class="candidate"><span class="avatar">${escapeHtml(initials(candidate.name))}</span><span><strong>${escapeHtml(candidate.name || 'Unnamed candidate')}</strong><small>${escapeHtml(candidate.email || 'No email')}</small></span></div></td>
        <td><span class="score">${percent(candidate.score)}</span><span class="score-label">verified fit</span></td>
        <td><div class="chips">${skills}</div></td>
        <td><button class="row-toggle" data-action="toggle" data-candidate="${escapeHtml(candidate.id)}" aria-expanded="false">${needsReview ? `${needsReview} to review` : 'View evidence'} ↗</button></td>
      </tr><tr class="detail-row" id="detail-${escapeHtml(candidate.id)}"><td colspan="5"><div class="evidence-grid">${renderEvidence(candidate)}</div><button class="row-toggle" data-action="facts" data-candidate="${escapeHtml(candidate.id)}">Correct candidate facts</button></td></tr>`;
    }).join('');
  }

  function renderEvidence(candidate) {
    if (!candidate.matches || !candidate.matches.length) return '<div class="empty">No requirement evidence was returned.</div>';
    return candidate.matches.map((match) => {
      const evidence = (match.evidence || []).map((item) => `<article class="evidence-card"><span class="status ${escapeHtml(item.status || match.status || 'missing')}">${escapeHtml(item.status || match.status || 'missing')}</span><p>${escapeHtml(item.snippet || 'No source snippet')}</p><span class="confidence">Confidence ${percent(item.confidence)}</span></article>`).join('');
      return `<div><strong>${escapeHtml(labelForRequirement(match.requirement_id))}</strong><div class="evidence-grid" style="margin-top:8px">${evidence || '<span class="confidence">No evidence</span>'}</div></div>`;
    }).join('');
  }

  function renderQueue() {
    const queue = $('#evidenceQueue');
    if (!state.queue.length) {
      queue.innerHTML = '<div class="empty">All evidence is resolved. Your shortlist is ready to export.</div>';
      return;
    }
    queue.innerHTML = state.queue.map((item) => `<article class="queue-item">
      <div class="queue-top"><span class="queue-name">${escapeHtml(item.candidate.name || 'Unnamed candidate')}</span><span class="status ${escapeHtml(item.status)}">${escapeHtml(item.status)}</span></div>
      <p><strong>${escapeHtml(labelForRequirement(item.match.requirement_id))}</strong><br>${escapeHtml(item.evidence.snippet || 'No source snippet')}</p>
      <div class="queue-meta"><small>${percent(item.confidence)} confidence</small><div class="queue-buttons"><button class="secondary" data-action="resolve" data-status="verified" data-candidate="${escapeHtml(item.candidate.id)}" data-requirement="${escapeHtml(item.match.requirement_id)}">Accept</button><button class="secondary" data-action="resolve" data-status="contradicted" data-candidate="${escapeHtml(item.candidate.id)}" data-requirement="${escapeHtml(item.match.requirement_id)}">Reject</button></div></div>
    </article>`).join('');
  }

  async function request(path, options) {
    const response = await fetch(path, { headers: { 'Content-Type': 'application/json', ...(options && options.headers) }, ...options });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.detail || `Request failed (${response.status})`);
    return data;
  }

  async function loadCandidates() {
    if (!jobId) {
      setNotice('No job selected. Open the dashboard with ?job_id=<job id>.', 'error');
      $('#candidateRows').innerHTML = '<tr><td colspan="5" class="empty">Choose a job to load its ranked candidates.</td></tr>';
      $('#evidenceQueue').innerHTML = '<div class="empty">No job selected.</div>';
      return;
    }
    $('#refreshBtn').disabled = true;
    try {
      const data = await request(`/api/jobs/${encodeURIComponent(jobId)}/candidates`);
      state.candidates = Array.isArray(data.candidates) ? data.candidates : [];
      state.queue = state.candidates.flatMap(normalizeEvidence).sort((a, b) => a.confidence - b.confidence);
      renderSummary(); renderCandidates(); renderQueue();
    } catch (error) {
      setNotice(error.message || 'Could not load candidates.', 'error');
      $('#candidateRows').innerHTML = '<tr><td colspan="5" class="empty">The candidate list could not be loaded.</td></tr>';
    } finally { $('#refreshBtn').disabled = false; }
  }

  async function resolveEvidence(button) {
    const { candidate, requirement, status } = button.dataset;
    button.disabled = true;
    try {
      await request(`/api/candidates/${encodeURIComponent(candidate)}/evidence/${encodeURIComponent(requirement)}/status`, { method: 'POST', body: JSON.stringify({ status }) });
      setNotice(`Evidence marked ${status}. Scores recalculated.`, 'success');
      await loadCandidates();
    } catch (error) { setNotice(error.message || 'Could not update evidence.', 'error'); button.disabled = false; }
  }

  function openFacts(candidateId) {
    const candidate = state.candidates.find((item) => String(item.id) === String(candidateId));
    if (!candidate) return;
    state.editingCandidate = candidate;
    $('#factsCandidate').textContent = `${candidate.name || 'Candidate'} · ${candidate.email || 'No email'}`;
    $('#factField').value = 'name'; $('#factValue').value = candidate.name || '';
    $('#factsDialog').showModal();
  }

  async function saveFacts(event) {
    event.preventDefault();
    const candidate = state.editingCandidate; if (!candidate) return;
    const field = $('#factField').value; const value = field === 'experience_years' ? Number($('#factValue').value) : $('#factValue').value.trim();
    if (field === 'experience_years' && !Number.isFinite(value)) { setNotice('Years of experience must be a number.', 'error'); return; }
    try {
      await request(`/api/candidates/${encodeURIComponent(candidate.id)}/facts`, { method: 'PATCH', body: JSON.stringify({ field, value }) });
      $('#factsDialog').close(); setNotice('Candidate fact saved. Scores recalculated.', 'success'); await loadCandidates();
    } catch (error) { setNotice(error.message || 'Could not save candidate fact.', 'error'); }
  }

  async function exportShortlist() {
    if (!jobId) { setNotice('Select a job before exporting.', 'error'); return; }
    $('#exportBtn').disabled = true;
    try {
      const data = await request(`/api/jobs/${encodeURIComponent(jobId)}/export`);
      const blob = new Blob([data.markdown || ''], { type: 'text/markdown;charset=utf-8' });
      const link = document.createElement('a'); link.href = URL.createObjectURL(blob); link.download = `shortlist-${jobId}.md`; link.click(); URL.revokeObjectURL(link.href);
      setNotice('Evidence-backed shortlist exported.', 'success');
    } catch (error) { setNotice(error.message || 'Could not export shortlist.', 'error'); } finally { $('#exportBtn').disabled = false; }
  }

  document.addEventListener('click', (event) => {
    const button = event.target.closest('[data-action]'); if (!button) return;
    if (button.dataset.action === 'resolve') resolveEvidence(button);
    if (button.dataset.action === 'facts') openFacts(button.dataset.candidate);
    if (button.dataset.action === 'toggle') {
      const row = document.getElementById(`detail-${button.dataset.candidate}`); const open = row.classList.toggle('open'); button.setAttribute('aria-expanded', String(open));
    }
  });
  $('#refreshBtn').addEventListener('click', loadCandidates);
  $('#exportBtn').addEventListener('click', exportShortlist);
  $('#factsForm').addEventListener('submit', saveFacts);
  $('#cancelFacts').addEventListener('click', () => $('#factsDialog').close());
  loadCandidates();
}());
