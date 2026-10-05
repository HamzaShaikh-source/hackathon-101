// Evidence-First Resume Triage - Upload Controller

document.addEventListener('DOMContentLoaded', () => {
  // State
  let currentJobId = null;
  let selectedFiles = [];

  // DOM Elements - Job Section
  const jobForm = document.getElementById('job-form');
  const jobDescriptionInput = document.getElementById('job-description');
  const btnSubmitJob = document.getElementById('btn-submit-job');
  const jobSpinner = document.getElementById('job-spinner');
  const jobAlert = document.getElementById('job-alert');
  const btnLoadSample = document.getElementById('btn-load-sample');
  const btnClearJob = document.getElementById('btn-clear-job');
  const requirementsContainer = document.getElementById('requirements-container');
  const requirementsList = document.getElementById('requirements-list');
  const displayJobId = document.getElementById('display-job-id');
  const mustCountBadge = document.getElementById('must-count-badge');
  const niceCountBadge = document.getElementById('nice-count-badge');
  const stepJobCard = document.getElementById('step-job');

  // DOM Elements - Upload Section
  const stepUploadCard = document.getElementById('step-upload');
  const uploadStatusBadge = document.getElementById('upload-status-badge');
  const resumeForm = document.getElementById('resume-form');
  const dropzone = document.getElementById('dropzone');
  const fileInput = document.getElementById('resume-files');
  const fileList = document.getElementById('file-list');
  const btnSubmitUpload = document.getElementById('btn-submit-upload');
  const uploadSpinner = document.getElementById('upload-spinner');
  const uploadAlert = document.getElementById('upload-alert');
  const uploadSuccessSection = document.getElementById('upload-success-section');
  const btnGotoDashboard = document.getElementById('btn-goto-dashboard');
  const navDashboardLink = document.getElementById('nav-dashboard-link');
  const candidateCount = document.getElementById('candidate-count');
  const candidatesTbody = document.getElementById('candidates-tbody');

  // Check URL params for existing job_id
  const urlParams = new URLSearchParams(window.location.search);
  const paramJobId = urlParams.get('job_id');
  if (paramJobId) {
    setJobId(paramJobId);
  }

  // --- Sample Job Data ---
  const SAMPLE_JOB = `Senior Full-Stack Engineer

About the Role:
We are looking for a Senior Full-Stack Engineer to lead the design and implementation of verifiable, bias-resistant hiring tools. You will build high-throughput APIs and responsive client applications.

Must-Have Requirements:
- At least 4 years of professional software engineering experience
- Strong proficiency in Python and FastAPI or Django
- Hands-on experience building frontend web applications with modern JavaScript / TypeScript and React
- Solid understanding of relational databases and SQL (PostgreSQL or SQLite)

Nice-to-Have Requirements:
- Experience with text parsing, document extraction (PyMuPDF or docx), or NLP
- Familiarity with Docker containerization and CI/CD pipelines
- Background in building accessible and responsive user interfaces
- Previous experience in HR-tech or evidence-based decision support systems`;

  if (btnLoadSample) {
    btnLoadSample.addEventListener('click', () => {
      jobDescriptionInput.value = SAMPLE_JOB;
      hideAlert(jobAlert);
    });
  }

  if (btnClearJob) {
    btnClearJob.addEventListener('click', () => {
      jobDescriptionInput.value = '';
      hideAlert(jobAlert);
    });
  }

  // --- Helper Functions ---
  function showAlert(alertEl, message, type = 'danger') {
    alertEl.textContent = message;
    alertEl.className = `alert alert-${type}`;
    alertEl.classList.remove('hidden');
  }

  function hideAlert(alertEl) {
    alertEl.classList.add('hidden');
    alertEl.textContent = '';
  }

  function formatFileSize(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  }

  function setJobId(jobId) {
    currentJobId = jobId;
    if (displayJobId) {
      displayJobId.textContent = jobId;
    }
    const dashboardUrl = `dashboard.html?job_id=${encodeURIComponent(jobId)}`;
    if (btnGotoDashboard) btnGotoDashboard.href = dashboardUrl;
    if (navDashboardLink) navDashboardLink.href = dashboardUrl;

    // Unlock upload card
    stepUploadCard.classList.remove('disabled');
    uploadStatusBadge.textContent = `Active Job: ${jobId.substring(0, 8)}...`;
    uploadStatusBadge.className = 'req-badge nice';
    updateUploadButtonState();
  }

  function escapeHtml(str) {
    if (!str) return '';
    return str
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  // --- Job Form Submission ---
  jobForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    hideAlert(jobAlert);

    const description = jobDescriptionInput.value.trim();
    if (!description) {
      showAlert(jobAlert, 'Please enter or paste a job description.');
      return;
    }

    btnSubmitJob.disabled = true;
    jobSpinner.classList.remove('hidden');
    btnSubmitJob.querySelector('.btn-text').textContent = 'Extracting...';

    try {
      const response = await fetch('/api/jobs', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ description }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || errorData.message || `Request failed with status ${response.status}`);
      }

      const data = await response.json();
      const jobId = data.job_id;
      const requirements = data.requirements || [];

      setJobId(jobId);
      renderRequirements(requirements);

      stepJobCard.classList.add('completed');
      requirementsContainer.classList.remove('hidden');

      // Smooth scroll to requirements / upload
      requirementsContainer.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    } catch (err) {
      showAlert(jobAlert, `Failed to extract requirements: ${err.message}`);
    } finally {
      btnSubmitJob.disabled = false;
      jobSpinner.classList.add('hidden');
      btnSubmitJob.querySelector('.btn-text').textContent = 'Extract Requirements';
    }
  });

  function renderRequirements(requirements) {
    requirementsList.innerHTML = '';
    let mustCount = 0;
    let niceCount = 0;

    requirements.forEach((req) => {
      const isMust = req.type === 'must';
      if (isMust) mustCount++;
      else niceCount++;

      const card = document.createElement('div');
      card.className = `req-card ${isMust ? 'must' : 'nice'}`;
      card.innerHTML = `
        <span class="req-badge ${isMust ? 'must' : 'nice'}">${isMust ? 'Must-Have' : 'Nice-to-Have'}</span>
        <div class="req-text">${escapeHtml(req.text)}</div>
      `;
      requirementsList.appendChild(card);
    });

    mustCountBadge.textContent = `${mustCount} Must-Have`;
    niceCountBadge.textContent = `${niceCount} Nice-to-Have`;
  }

  // --- Resume Upload Management ---
  function updateUploadButtonState() {
    btnSubmitUpload.disabled = !currentJobId || selectedFiles.length === 0;
  }

  function addFiles(files) {
    const validExtensions = ['.pdf', '.docx', '.txt'];
    const addedFiles = [];

    Array.from(files).forEach((file) => {
      const ext = '.' + file.name.split('.').pop().toLowerCase();
      if (!validExtensions.includes(ext)) {
        showAlert(uploadAlert, `File "${file.name}" ignored: Only .pdf, .docx, and .txt files are accepted.`);
        return;
      }

      // Check duplicate by name and size
      const exists = selectedFiles.some(f => f.name === file.name && f.size === file.size);
      if (!exists) {
        selectedFiles.push(file);
        addedFiles.push(file);
      }
    });

    renderFileList();
    updateUploadButtonState();
  }

  function removeFile(index) {
    selectedFiles.splice(index, 1);
    renderFileList();
    updateUploadButtonState();
  }

  function renderFileList() {
    fileList.innerHTML = '';
    if (selectedFiles.length === 0) return;

    selectedFiles.forEach((file, idx) => {
      const item = document.createElement('div');
      item.className = 'file-item';
      item.innerHTML = `
        <div class="file-info">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="color: var(--text-muted); flex-shrink: 0;">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
            <polyline points="14 2 14 8 20 8"></polyline>
          </svg>
          <span class="file-name" title="${escapeHtml(file.name)}">${escapeHtml(file.name)}</span>
          <span class="file-size">(${formatFileSize(file.size)})</span>
        </div>
        <button type="button" class="file-remove" title="Remove file" data-index="${idx}">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        </button>
      `;
      fileList.appendChild(item);
    });

    fileList.querySelectorAll('.file-remove').forEach((btn) => {
      btn.addEventListener('click', (e) => {
        const index = parseInt(e.currentTarget.getAttribute('data-index'), 10);
        removeFile(index);
      });
    });
  }

  // File Input Change
  fileInput.addEventListener('change', (e) => {
    if (e.target.files && e.target.files.length > 0) {
      addFiles(e.target.files);
      fileInput.value = ''; // Reset so the same file can be re-selected if removed
    }
  });

  // Drag and Drop
  ['dragenter', 'dragover'].forEach((eventName) => {
    dropzone.addEventListener(eventName, (e) => {
      e.preventDefault();
      e.stopPropagation();
      dropzone.classList.add('dragover');
    });
  });

  ['dragleave', 'drop'].forEach((eventName) => {
    dropzone.addEventListener(eventName, (e) => {
      e.preventDefault();
      e.stopPropagation();
      dropzone.classList.remove('dragover');
    });
  });

  dropzone.addEventListener('drop', (e) => {
    if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      addFiles(e.dataTransfer.files);
    }
  });

  // --- Resume Upload Submission ---
  resumeForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    hideAlert(uploadAlert);

    if (!currentJobId) {
      showAlert(uploadAlert, 'Please submit a job description first before uploading resumes.');
      return;
    }

    if (selectedFiles.length === 0) {
      showAlert(uploadAlert, 'Please select at least one resume file to upload.');
      return;
    }

    btnSubmitUpload.disabled = true;
    uploadSpinner.classList.remove('hidden');
    btnSubmitUpload.querySelector('.btn-text').textContent = 'Uploading & Analyzing...';

    const formData = new FormData();
    formData.append('job_id', currentJobId);
    selectedFiles.forEach((file) => {
      formData.append('files', file);
    });

    try {
      const response = await fetch('/api/candidates/upload', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || errorData.message || `Upload failed with status ${response.status}`);
      }

      const data = await response.json();
      const candidates = data.candidates || [];

      // Render candidates preview
      renderUploadedCandidates(candidates);

      // Show success section
      uploadSuccessSection.classList.remove('hidden');
      stepUploadCard.classList.add('completed');
      uploadSuccessSection.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

      // Clear the queued files
      selectedFiles = [];
      renderFileList();
    } catch (err) {
      showAlert(uploadAlert, `Upload failed: ${err.message}`);
    } finally {
      btnSubmitUpload.disabled = false;
      uploadSpinner.classList.add('hidden');
      btnSubmitUpload.querySelector('.btn-text').textContent = 'Upload & Analyze Resumes';
      updateUploadButtonState();
    }
  });

  function renderUploadedCandidates(candidates) {
    candidateCount.textContent = candidates.length;
    candidatesTbody.innerHTML = '';

    if (candidates.length === 0) {
      const emptyRow = document.createElement('tr');
      emptyRow.innerHTML = '<td colspan="5" style="text-align: center; color: var(--text-muted);">No candidates returned.</td>';
      candidatesTbody.appendChild(emptyRow);
      return;
    }

    candidates.forEach((cand) => {
      const row = document.createElement('tr');
      const skillsStr = Array.isArray(cand.skills) && cand.skills.length > 0
        ? cand.skills.slice(0, 4).join(', ') + (cand.skills.length > 4 ? ` +${cand.skills.length - 4}` : '')
        : 'None extracted';

      const expStr = typeof cand.experience_years === 'number'
        ? `${cand.experience_years.toFixed(1)} yrs`
        : (cand.experience_years || 'N/A');

      const scoreVal = typeof cand.score === 'number' ? cand.score.toFixed(1) : (cand.score ?? 'N/A');

      row.innerHTML = `
        <td><strong>${escapeHtml(cand.name || 'Unknown Candidate')}</strong></td>
        <td>${escapeHtml(cand.email || 'N/A')}</td>
        <td>${escapeHtml(expStr)}</td>
        <td>${escapeHtml(skillsStr)}</td>
        <td><span class="score-pill">${escapeHtml(String(scoreVal))}</span></td>
      `;
      candidatesTbody.appendChild(row);
    });
  }
});
