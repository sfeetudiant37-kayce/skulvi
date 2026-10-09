'use strict';

const API = '/api/v1';
const PAGE_SIZE = 12;
const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];

const state = {
  catalog: null,
  meta: null,
  page: 1,
  pages: 1,
  total: 0,
  rows: [],
  activeCandidate: null,
  searchTimer: null,
};

function escapeHTML(value) {
  const entities = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };
  return String(value ?? '').replace(/[&<>"']/g, char => entities[char]);
}

function initials(name) {
  return String(name || '?').trim().split(/\s+/).filter(Boolean).slice(0, 2)
    .map(part => part.charAt(0)).join('').toUpperCase() || '?';
}

function formatDate(value, withTime = false) {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '—';
  const options = withTime
    ? { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' }
    : { day: '2-digit', month: 'short', year: 'numeric' };
  return new Intl.DateTimeFormat('fr-FR', options).format(date);
}

function showToast(message, type = 'success') {
  const toast = document.createElement('div');
  toast.className = `toast${type === 'error' ? ' error' : ''}`;
  toast.textContent = message;
  $('#toastStack').appendChild(toast);
  window.setTimeout(() => toast.remove(), 4200);
}

function showAlert(message, visible = true) {
  const alert = $('#globalAlert');
  alert.textContent = message;
  alert.hidden = !visible;
}

async function apiRequest(path, options = {}) {
  const headers = new Headers(options.headers || {});
  if (options.body && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json');
  headers.set('Accept', 'application/json');
  let response;
  try {
    response = await fetch(`${API}${path}`, { ...options, headers });
  } catch {
    throw new Error('Le service est injoignable. Vérifiez que le serveur est démarré.');
  }
  if (response.status === 204) return null;
  const contentType = response.headers.get('content-type') || '';
  const payload = contentType.includes('application/json') ? await response.json() : await response.text();
  if (!response.ok) {
    const detail = typeof payload === 'object' && payload ? payload.detail : payload;
    const message = Array.isArray(detail)
      ? detail.map(item => item.msg || 'Valeur invalide').join(' · ')
      : String(detail || `Erreur ${response.status}`);
    throw new Error(message);
  }
  return payload;
}

function statusLabel(status) {
  return state.catalog?.statuses.find(item => item.value === status)?.label || status || 'Nouveau';
}

function avatarColor(name) {
  const colors = ['green', 'orange', 'blue', 'coral'];
  const seed = [...String(name || '')].reduce((value, char) => value + char.charCodeAt(0), 0);
  return colors[seed % colors.length];
}

function priorityMarkup(code, label) {
  const safeCode = ['high', 'medium', 'low'].includes(code) ? code : 'low';
  return `<span class="priority-pill ${safeCode}">${escapeHTML(label)}</span>`;
}

function scoreMarkup(candidate) {
  const score = candidate.score;
  const complete = score.review_complete;
  const value = complete ? score.final_score : score.skill_score;
  const max = complete ? score.final_max : score.skill_max;
  const percent = Math.max(0, Math.min(100, score.triage_index));
  const widthStep = Math.round(percent / 5) * 5;
  return `<div class="score-cell">
    <div class="score-line"><strong>${value}</strong><small>/${max} ${complete ? 'final' : 'pré-score'}</small></div>
    <div class="score-bar ${escapeHTML(score.priority_code)}" role="img" aria-label="Indice de tri ${percent} sur 100"><span class="w-${widthStep}"></span></div>
  </div>`;
}

function renderRows(items) {
  const body = $('#candidateRows');
  body.innerHTML = items.map(candidate => `
    <tr class="candidate-row" data-candidate-id="${escapeHTML(candidate.id)}">
      <td><div class="person-cell"><span class="person-avatar ${avatarColor(candidate.name)}" aria-hidden="true">${escapeHTML(initials(candidate.name))}</span><span class="person-copy"><span class="person-name">${escapeHTML(candidate.name)}</span><span class="person-email">${escapeHTML(candidate.email)}</span></span></div></td>
      <td><span class="track-chip">${escapeHTML(candidate.track)}</span></td>
      <td class="date-cell">${escapeHTML(formatDate(candidate.created_at))}</td>
      <td>${scoreMarkup(candidate)}</td>
      <td>${priorityMarkup(candidate.score.priority_code, candidate.score.priority_label)}</td>
      <td><span class="status-pill status-${escapeHTML(candidate.status)}">${escapeHTML(statusLabel(candidate.status))}</span></td>
      <td><button class="row-open" type="button" data-open-id="${escapeHTML(candidate.id)}" aria-label="Consulter ${escapeHTML(candidate.name)}"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="m9 18 6-6-6-6"/></svg></button></td>
    </tr>`).join('');

  const hasRows = items.length > 0;
  $('#tableWrap').hidden = !hasRows;
  $('#emptyState').hidden = hasRows;
  $('#loadingState').hidden = true;
  $('#filteredTotal').textContent = String(state.total);
  $('#resultsSummary').textContent = state.total === 0
    ? 'Aucun dossier'
    : `${state.total} dossier${state.total === 1 ? '' : 's'} correspondant${state.total === 1 ? '' : 's'}`;
  $('#pageSummary').textContent = `Page ${state.page} sur ${Math.max(1, state.pages)}`;
  $('#prevPage').disabled = state.page <= 1;
  $('#nextPage').disabled = state.page >= state.pages;
  $('#navCount').textContent = String(state.total);
}

function renderPriorityList(items) {
  const prioritized = [...items]
    .filter(candidate => candidate.status !== 'closed' &&
      (candidate.score.priority_code === 'high' || !candidate.score.review_complete))
    .sort((a, b) => b.score.triage_index - a.score.triage_index)
    .slice(0, 4);
  const list = $('#priorityList');
  if (!prioritized.length) {
    list.innerHTML = '<div class="priority-empty">Aucun dossier à prioriser sur cette page.</div>';
    return;
  }
  list.innerHTML = prioritized.map((candidate, index) => {
    const score = candidate.score.review_complete
      ? `${candidate.score.final_score}<small>/100 final</small>`
      : `${candidate.score.skill_score}<small>/40 pré-score</small>`;
    return `<button class="priority-item" type="button" data-open-id="${escapeHTML(candidate.id)}">
      <span class="priority-number">${String(index + 1).padStart(2, '0')}</span>
      <span class="priority-item-copy"><strong>${escapeHTML(candidate.name)}</strong><small>${escapeHTML(candidate.track)} · ${escapeHTML(statusLabel(candidate.status))}</small></span>
      <span class="priority-item-score">${score}</span>
    </button>`;
  }).join('');
}

function renderStats(stats) {
  $('#statTotal').textContent = String(stats.total);
  $('#statPriority').textContent = String(stats.priority);
  $('#statPending').textContent = String(stats.pending_review);
  $('#statShortlisted').textContent = String(stats.shortlisted);
}

async function refreshDashboard({ keepPage = true } = {}) {
  if (!keepPage) state.page = 1;
  $('#loadingState').hidden = false;
  $('#tableWrap').hidden = true;
  $('#emptyState').hidden = true;
  showAlert('', false);

  const params = new URLSearchParams({ page: String(state.page), page_size: String(PAGE_SIZE) });
  const query = $('#searchInput').value.trim();
  const track = $('#trackFilter').value;
  const status = $('#statusFilter').value;
  if (query) params.set('q', query);
  if (track) params.set('track', track);
  if (status) params.set('status', status);

  try {
    const [pageData, stats] = await Promise.all([
      apiRequest(`/candidates?${params.toString()}`),
      apiRequest('/stats'),
    ]);
    state.rows = pageData.items;
    state.total = pageData.total;
    state.page = pageData.page;
    state.pages = Math.max(1, pageData.pages);
    renderRows(state.rows);
    renderPriorityList(state.rows);
    renderStats(stats);
    $('#lastUpdated').textContent = formatDate(new Date().toISOString(), true);
    $('#apiStatus').textContent = 'Service opérationnel';
    $('#apiLight').classList.add('online');
    $('#apiLight').classList.remove('offline');
    $('#refreshButton').disabled = false;
  } catch (error) {
    $('#loadingState').hidden = true;
    $('#tableWrap').hidden = true;
    $('#emptyState').hidden = true;
    $('#apiStatus').textContent = 'Service indisponible';
    $('#apiLight').classList.remove('online');
    $('#apiLight').classList.add('offline');
    showAlert(`${error.message} Pour lancer l’application : consultez le README et démarrez l’API.`);
  }
}

function addOptions(select, items, { placeholder = null, labelKey = 'value' } = {}) {
  select.innerHTML = '';
  if (placeholder !== null) {
    const option = document.createElement('option');
    option.value = '';
    option.textContent = placeholder;
    select.appendChild(option);
  }
  items.forEach(item => {
    const option = document.createElement('option');
    option.value = typeof item === 'string' ? item : item.value;
    option.textContent = typeof item === 'string' ? item : (item[labelKey] || item.value);
    select.appendChild(option);
  });
}

function renderSkillChoices(track, selected = []) {
  const trackEntry = state.catalog?.tracks.find(item => item.value === track);
  const choices = trackEntry?.skills || [];
  $('#skillChoices').innerHTML = choices.map(skill => `
    <label class="skill-option"><input type="checkbox" name="skills" value="${escapeHTML(skill)}" ${selected.includes(skill) ? 'checked' : ''}><span>${escapeHTML(skill)}</span></label>`).join('');
}

function setFormError(message = '') {
  const error = $('#formError');
  error.textContent = message;
  error.hidden = !message;
}

function openCandidateForm(candidate = null) {
  const form = $('#candidateForm');
  form.reset();
  setFormError('');
  $('#editingCandidateId').value = candidate?.id || '';
  $('#candidateDialogKicker').textContent = candidate ? 'MISE À JOUR DU DOSSIER' : 'NOUVEAU DOSSIER';
  $('#candidateDialogTitle').textContent = candidate ? 'Modifier une candidature' : 'Ajouter une candidature';
  $('#saveCandidateButton').textContent = candidate ? 'Enregistrer les modifications' : 'Enregistrer le dossier';
  $('#candidateName').value = candidate?.name || '';
  $('#candidateEmail').value = candidate?.email || '';
  $('#candidateTrack').value = candidate?.track || '';
  $('#experienceYears').value = candidate?.experience_years ?? '';
  $('#projectCount').value = candidate?.project_count ?? 0;
  $('#portfolioUrl').value = candidate?.portfolio_url || '';
  $('#projectSummary').value = candidate?.project_summary || '';
  $('#motivation').value = candidate?.motivation || '';
  $('#otherSkills').value = candidate?.other_skills || '';
  $('#availability').value = candidate?.availability || '';
  renderSkillChoices(candidate?.track || '', candidate?.skills || []);
  if (!$('#candidateDialog').open) $('#candidateDialog').showModal();
  window.setTimeout(() => $('#candidateName').focus(), 40);
}

function buildCandidatePayload() {
  const skills = $$('input[name="skills"]:checked', $('#candidateForm')).map(input => input.value);
  const otherSkills = $('#otherSkills').value.trim();
  if (!skills.length && !otherSkills) {
    throw new Error('Choisissez au moins une compétence ou indiquez une autre compétence.');
  }
  const experienceRaw = $('#experienceYears').value;
  return {
    name: $('#candidateName').value.trim(),
    email: $('#candidateEmail').value.trim(),
    track: $('#candidateTrack').value,
    skills,
    other_skills: otherSkills,
    experience_years: experienceRaw === '' ? null : Number(experienceRaw),
    project_count: Number($('#projectCount').value || 0),
    portfolio_url: $('#portfolioUrl').value.trim() || null,
    project_summary: $('#projectSummary').value.trim(),
    motivation: $('#motivation').value.trim(),
    availability: $('#availability').value || null,
  };
}

async function saveCandidate(event) {
  event.preventDefault();
  setFormError('');
  if (!$('#candidateForm').reportValidity()) return;
  let payload;
  try {
    payload = buildCandidatePayload();
  } catch (error) {
    setFormError(error.message);
    return;
  }
  const candidateId = $('#editingCandidateId').value;
  const button = $('#saveCandidateButton');
  button.disabled = true;
  button.textContent = 'Enregistrement…';
  try {
    await apiRequest(candidateId ? `/candidates/${encodeURIComponent(candidateId)}` : '/candidates', {
      method: candidateId ? 'PUT' : 'POST',
      body: JSON.stringify(payload),
    });
    $('#candidateDialog').close();
    await refreshDashboard({ keepPage: !candidateId });
    showToast(candidateId ? 'Le dossier a été mis à jour.' : 'La candidature a été ajoutée au pipeline.');
  } catch (error) {
    setFormError(error.message);
  } finally {
    button.disabled = false;
    button.textContent = candidateId ? 'Enregistrer les modifications' : 'Enregistrer le dossier';
  }
}

function scoreOptions(max, current) {
  const options = ['<option value="">À évaluer</option>'];
  for (let value = 0; value <= max; value += 1) {
    options.push(`<option value="${value}" ${current === value ? 'selected' : ''}>${value} / ${max}</option>`);
  }
  return options.join('');
}

function externalLink(value) {
  if (!value) return '<span class="muted-value">Non renseigné</span>';
  // URLs are validated on the API; this check also protects imported/legacy rows.
  try {
    const url = new URL(value);
    if (!['http:', 'https:'].includes(url.protocol)) return '<span class="muted-value">Lien non valide</span>';
    return `<a href="${escapeHTML(url.href)}" target="_blank" rel="noopener noreferrer">Ouvrir le portfolio <span aria-hidden="true">↗</span></a>`;
  } catch {
    return '<span class="muted-value">Lien non valide</span>';
  }
}

function renderCandidateDetail(candidate) {
  state.activeCandidate = candidate;
  $('#editCandidateButton').dataset.candidateId = candidate.id;
  const score = candidate.score;
  $('#detailDialogTitle').textContent = candidate.name;
  $('#detailDialogSubtitle').textContent = `${candidate.email} · ${candidate.track} · reçu le ${formatDate(candidate.created_at)}`;

  const skills = [...candidate.skills, ...String(candidate.other_skills || '').split(',').map(item => item.trim()).filter(Boolean)];
  const finalDisplay = score.review_complete ? `${score.final_score}<small>/100 · score final</small>` : `${score.skill_score}<small>/40 · pré-score</small>`;
  const summaryText = candidate.project_summary || 'Aucun projet renseigné.';
  const motivationText = candidate.motivation || 'Aucune réponse renseignée.';
  const statusOptions = state.catalog.statuses.map(item => `<option value="${escapeHTML(item.value)}" ${item.value === candidate.status ? 'selected' : ''}>${escapeHTML(item.label)}</option>`).join('');

  $('#detailContent').innerHTML = `
    <section class="detail-profile">
      <div class="detail-identity"><span class="detail-avatar ${avatarColor(candidate.name)}">${escapeHTML(initials(candidate.name))}</span><div><h3>${escapeHTML(candidate.name)}</h3><p>${escapeHTML(candidate.email)}<br>${escapeHTML(candidate.track)} · reçu le ${escapeHTML(formatDate(candidate.created_at))}</p></div></div>
      <div class="detail-score"><strong>${finalDisplay}</strong>${priorityMarkup(score.priority_code, score.priority_label)}</div>
    </section>
    <div class="detail-columns">
      <section class="detail-card">
        <h4>Informations du dossier</h4>
        <dl class="detail-facts">
          <dt>Parcours</dt><dd>${escapeHTML(candidate.track)}</dd>
          <dt>Compétences</dt><dd>${skills.length ? skills.map(escapeHTML).join(', ') : 'Non renseignées'}</dd>
          <dt>Expérience</dt><dd>${candidate.experience_years === null ? 'Non précisée' : `${candidate.experience_years} an${candidate.experience_years > 1 ? 's' : ''} · non notée`}</dd>
          <dt>Disponibilité</dt><dd>${escapeHTML(candidate.availability || 'Non précisée')} · non notée</dd>
          <dt>Portfolio</dt><dd>${externalLink(candidate.portfolio_url)}</dd>
        </dl>
        <div class="detail-section-label">PROJET & CONTRIBUTION</div><p class="detail-copy">${escapeHTML(summaryText)}</p>
        <div class="detail-section-label">MOTIVATION</div><p class="detail-copy">${escapeHTML(motivationText)}</p>
        ${candidate.is_sample ? '<div class="review-callout">Profil fictif — données d’exemple.</div>' : ''}
      </section>
      <section class="detail-card">
        <h4>Décomposition du score</h4>
        <div class="score-breakdown">
          <div class="breakdown-line"><span>Compétences déclarées</span><strong>${score.skill_score} / ${score.skill_max}</strong></div>
          <div class="breakdown-line"><span>Compétences correspondantes</span><strong>${score.matched_skills.length} / 4</strong></div>
          <div class="breakdown-line"><span>Revue humaine renseignée</span><strong>${score.review_score} / ${score.review_max}</strong></div>
          <div class="breakdown-line total"><span>Score final</span><strong>${score.final_score === null ? 'En attente' : `${score.final_score} / ${score.final_max}`}</strong></div>
        </div>
        <div class="review-fields">
          <div class="review-field"><label for="reviewProject">Projet & contribution <small>0–25 points</small></label><select id="reviewProject">${scoreOptions(25, candidate.review_project)}</select><p class="review-hint">Pertinence, rôle exact, raisonnement et résultats observables.</p></div>
          <div class="review-field"><label for="reviewMotivation">Motivation & compréhension <small>0–20 points</small></label><select id="reviewMotivation">${scoreOptions(20, candidate.review_motivation)}</select><p class="review-hint">Objectif d’apprentissage concret et compréhension du programme.</p></div>
          <div class="review-field"><label for="reviewLearning">Apprentissage & autonomie <small>0–15 points</small></label><select id="reviewLearning">${scoreOptions(15, candidate.review_learning)}</select><p class="review-hint">Initiative, démarche de résolution et progression.</p></div>
          <div class="review-field"><label for="reviewStatus">Statut du dossier</label><select id="reviewStatus">${statusOptions}</select></div>
          <div class="review-field"><label for="reviewNotes">Note interne <small>facultatif</small></label><textarea id="reviewNotes" maxlength="2000" rows="3" placeholder="Éléments vérifiés, questions à poser…">${escapeHTML(candidate.review_notes || '')}</textarea></div>
        </div>
        <div class="review-callout">Appliquez les mêmes repères à chaque dossier. Un pré-score n’est pas une décision de recrutement.</div>
      </section>
    </div>`;
}

async function openCandidateDetail(candidateId) {
  try {
    const candidate = await apiRequest(`/candidates/${encodeURIComponent(candidateId)}`);
    renderCandidateDetail(candidate);
    if (!$('#detailDialog').open) $('#detailDialog').showModal();
  } catch (error) {
    showToast(error.message, 'error');
  }
}

async function saveReview() {
  const candidate = state.activeCandidate;
  if (!candidate) return;
  const parseScore = selector => $(selector).value === '' ? null : Number($(selector).value);
  const payload = {
    review_project: parseScore('#reviewProject'),
    review_motivation: parseScore('#reviewMotivation'),
    review_learning: parseScore('#reviewLearning'),
    review_notes: $('#reviewNotes').value.trim(),
    status: $('#reviewStatus').value,
  };
  const button = $('#saveReviewButton');
  button.disabled = true;
  button.textContent = 'Enregistrement…';
  try {
    const updated = await apiRequest(`/candidates/${encodeURIComponent(candidate.id)}/review`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    });
    renderCandidateDetail(updated);
    await refreshDashboard();
    showToast(updated.score.review_complete ? 'La revue est enregistrée et le score final est calculé.' : 'La revue partielle a été enregistrée.');
  } catch (error) {
    showToast(error.message, 'error');
  } finally {
    button.disabled = false;
    button.textContent = 'Enregistrer la revue';
  }
}

async function deleteCandidate() {
  const candidate = state.activeCandidate;
  if (!candidate) return;
  if (!window.confirm(`Supprimer le dossier de ${candidate.name} ? Cette action est définitive.`)) return;
  try {
    await apiRequest(`/candidates/${encodeURIComponent(candidate.id)}`, { method: 'DELETE' });
    $('#detailDialog').close();
    await refreshDashboard({ keepPage: false });
    showToast('Le dossier a été supprimé.');
  } catch (error) {
    showToast(error.message, 'error');
  }
}

async function loadReferenceData() {
  const [catalog, meta] = await Promise.all([apiRequest('/options'), apiRequest('/meta')]);
  state.catalog = catalog;
  state.meta = meta;
  $('#criteriaTrackList').innerHTML = catalog.tracks.map(track => `<div class="criteria-track"><strong>${escapeHTML(track.value)}</strong><span>${track.skills.map(escapeHTML).join(' · ')}</span></div>`).join('');
  addOptions($('#candidateTrack'), catalog.tracks, { placeholder: 'Sélectionner un parcours' });
  addOptions($('#trackFilter'), catalog.tracks, { placeholder: 'Tous les parcours' });
  addOptions($('#statusFilter'), catalog.statuses, { placeholder: 'Tous les statuts', labelKey: 'label' });
  addOptions($('#availability'), catalog.availability.filter(value => value !== 'À préciser'), { placeholder: 'À préciser' });
  if (meta.sample_data) {
    $('#environmentPill').classList.add('sample');
    $('#environmentLabel').textContent = 'Jeu de données fictif';
    $('#sampleNotice').hidden = false;
  } else {
    $('#environmentLabel').textContent = meta.environment === 'production' ? 'Environnement sécurisé' : 'Base locale';
  }
}

async function initialize() {
  bindEvents();
  try {
    await loadReferenceData();
    await refreshDashboard({ keepPage: false });
  } catch (error) {
    $('#loadingState').hidden = true;
    $('#apiStatus').textContent = 'Service indisponible';
    $('#apiLight').classList.add('offline');
    $('#environmentLabel').textContent = 'Connexion requise';
    showAlert(`${error.message} Démarrez le serveur selon les instructions du README.`);
  }
}

async function editActiveCandidate() {
  const candidateId = $('#editCandidateButton').dataset.candidateId;
  if (!candidateId) {
    showToast('Impossible d’identifier le dossier à modifier. Rouvrez-le, puis réessayez.', 'error');
    return;
  }

  let candidate;
  try {
    candidate = await apiRequest(`/candidates/${encodeURIComponent(candidateId)}`);
  } catch (error) {
    showToast(error.message, 'error');
    return;
  }

  const detailDialog = $('#detailDialog');
  let opened = false;
  let fallbackTimer = 0;
  const openForm = () => {
    if (opened) return;
    opened = true;
    window.clearTimeout(fallbackTimer);
    detailDialog.removeEventListener('close', openForm);
    try {
      openCandidateForm(candidate);
    } catch (error) {
      showToast(`Impossible d’ouvrir le formulaire : ${error.message}`, 'error');
    }
  };

  if (detailDialog.open) {
    detailDialog.addEventListener('close', openForm, { once: true });
    detailDialog.close();
    fallbackTimer = window.setTimeout(openForm, 120);
  } else {
    openForm();
  }
}

function bindEvents() {
  $('#newCandidateButton').addEventListener('click', () => openCandidateForm());
  $('#emptyAddButton').addEventListener('click', () => openCandidateForm());
  $('#candidateForm').addEventListener('submit', saveCandidate);
  $('#candidateTrack').addEventListener('change', () => renderSkillChoices($('#candidateTrack').value));
  $('#saveReviewButton').addEventListener('click', saveReview);
  $('#deleteCandidateButton').addEventListener('click', deleteCandidate);
  $('#refreshButton').addEventListener('click', () => refreshDashboard());
  $('#prevPage').addEventListener('click', () => { if (state.page > 1) { state.page -= 1; refreshDashboard(); } });
  $('#nextPage').addEventListener('click', () => { if (state.page < state.pages) { state.page += 1; refreshDashboard(); } });
  $('#viewAllButton').addEventListener('click', () => document.querySelector('.pipeline-panel').scrollIntoView({ behavior: 'smooth', block: 'start' }));
  $('#openCriteriaButton').addEventListener('click', () => $('#criteriaDialog').showModal());
  $('#methodNav').addEventListener('click', event => { event.preventDefault(); $('#criteriaDialog').showModal(); });
  $('#criteriaDialog').addEventListener('click', event => {
    if (event.target.closest('[data-close-criteria]') || event.target === $('#criteriaDialog')) $('#criteriaDialog').close();
  });
  $('#editCandidateButton').addEventListener('click', editActiveCandidate);
  $('#dismissSampleNotice').addEventListener('click', () => { $('#sampleNotice').hidden = true; });
  $('#searchInput').addEventListener('input', () => {
    window.clearTimeout(state.searchTimer);
    state.searchTimer = window.setTimeout(() => refreshDashboard({ keepPage: false }), 240);
  });
  $('#trackFilter').addEventListener('change', () => refreshDashboard({ keepPage: false }));
  $('#statusFilter').addEventListener('change', () => refreshDashboard({ keepPage: false }));
  $('#candidateRows').addEventListener('click', event => {
    const button = event.target.closest('[data-open-id]');
    const row = event.target.closest('[data-candidate-id]');
    const id = button?.dataset.openId || row?.dataset.candidateId;
    if (id) openCandidateDetail(id);
  });
  $('#priorityList').addEventListener('click', event => {
    const button = event.target.closest('[data-open-id]');
    if (button) openCandidateDetail(button.dataset.openId);
  });
  for (const [dialogId, closeValue] of [['candidateDialog', 'candidate'], ['detailDialog', 'detail']]) {
    const dialog = $(`#${dialogId}`);
    dialog.addEventListener('click', event => {
      if (event.target.closest(`[data-close-dialog="${closeValue}"]`)) dialog.close();
      else if (event.target === dialog) dialog.close();
    });
    dialog.addEventListener('close', () => {
      if (closeValue === 'detail' && !dialog.open) state.activeCandidate = null;
    });
  }
  document.addEventListener('keydown', event => {
    if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
      event.preventDefault();
      $('#searchInput').focus();
    }
  });
}

document.addEventListener('DOMContentLoaded', initialize, { once: true });
