/* Owner tools. Credentials and model requests are handled by the server. */
(() => {
  const bridge = window.resumeStudio;
  const $ = id => document.getElementById(id);
  let type = 'software', signedIn = false, busy = false, epoch = 0;
  let revision = null, historyCursor = null, proposal = null;
  const panel = document.createElement('section');
  panel.id = 'studio';
  panel.innerHTML = `
    <div class="studio-heading"><div><span class="studio-eyebrow">PERSONAL WORKSPACE</span><h2>Your next chapter.</h2></div><span id="studioBadge">Private tools</span></div>
    <p class="studio-intro">Three perspectives. One story. Tailor a CV, review it, and keep every saved version.</p>
    <form id="studioLogin"><label for="accessCode">Your access code</label><div class="studio-row"><input id="accessCode" type="password" autocomplete="current-password" required maxlength="128" placeholder="Enter your private code"><button type="submit">Unlock</button></div><p class="studio-hint">The code unlocks AI and cloud history. Public templates stay available to everyone.</p></form>
    <div id="studioTools" hidden>
      <div class="studio-row studio-account"><span>Private workspace unlocked</span><button id="studioLogout" type="button" class="quiet">Lock</button></div>
      <label for="aiPrompt">What should this CV focus on?</label>
      <textarea id="aiPrompt" maxlength="4000" rows="4" placeholder="e.g. Tailor my academic CV for a digital project management master's in France. Emphasise project delivery and relevant education."></textarea>
      <p class="studio-hint">Your instruction and CV text are sent to Qwen. Check dates and claims before saving. Supporting identity documents are never uploaded.</p>
      <button id="generateCv" type="button" class="studio-primary">Generate a draft</button>
      <div id="proposalReview" hidden><h3>Review the AI draft</h3><p id="aiNotes"></p><details><summary>Compare with current CV</summary><pre id="previousDraft"></pre></details><div class="studio-row"><button id="acceptDraft" type="button">Use draft in editor</button><button id="discardDraft" type="button" class="quiet">Discard draft</button></div><p class="studio-hint">Accepting changes the editor. Save a version when you are ready.</p></div>
      <hr><label for="versionNote">Version note <span>(optional)</span></label>
      <input id="versionNote" maxlength="160" placeholder="e.g. Toulouse digital project management">
      <button id="saveVersion" type="button" class="studio-primary">Save version to cloud</button>
      <p class="studio-hint">Saved CVs and history are private. Saving does not replace the public template.</p>
      <div class="studio-row"><h3>Version history</h3><button id="refreshVersions" type="button" class="quiet">Refresh</button></div>
      <ol id="versionHistory"></ol><button id="moreVersions" type="button" class="quiet" hidden>Load older versions</button>
    </div><p id="studioStatus" role="status" aria-live="polite">Choose a CV type above, then open the editor to personalise it.</p>`;
  $('editorPane').prepend(panel);
  const status = message => { $('studioStatus').textContent = message; };
  function pending(value) {
    busy = value;
    panel.querySelectorAll('button').forEach(button => { button.disabled = value; });
    $('resumeType').disabled = value;
    $('studioBadge').textContent = value ? 'Working…' : signedIn ? 'Unlocked' : 'Private tools';
  }
  async function api(path, body) {
    const options = {credentials: 'same-origin', headers: {}};
    if (body !== undefined) {
      options.method = 'POST';
      options.body = JSON.stringify(body);
      options.headers['Content-Type'] = 'application/json';
    }
    const response = await fetch(`/api/${path}`, options);
    const data = await response.json().catch(() => ({error: 'Server unavailable. Please try again.'}));
    if (response.status === 401) showSession(false);
    if (!response.ok) throw new Error(data.error || 'Request failed. Please try again.');
    return data;
  }
  function showSession(value) {
    signedIn = value;
    $('studioLogin').hidden = value;
    $('studioTools').hidden = !value;
    $('studioBadge').textContent = value ? 'Unlocked' : 'Private tools';
    if (!value) { revision = null; proposal = null; $('proposalReview').hidden = true; $('versionHistory').replaceChildren(); }
  }
  async function run(action) {
    if (busy) return;
    pending(true);
    try { await action(); } catch (error) { status(error.message); }
    finally { pending(false); }
  }
  async function history(append = false) {
    const stamp = epoch;
    const cursor = append && historyCursor ? `&cursor=${encodeURIComponent(historyCursor)}` : '';
    const data = await api(`versions?type=${type}${cursor}`);
    if (stamp !== epoch) return;
    if (!append) $('versionHistory').replaceChildren();
    historyCursor = data.cursor;
    $('moreVersions').hidden = !historyCursor;
    for (const version of data.versions) {
      const item = document.createElement('li');
      const text = document.createElement('span');
      const date = new Date(version.createdAt).toLocaleString();
      text.textContent = `${version.note || 'Saved version'} · ${date}`;
      const button = document.createElement('button');
      button.type = 'button'; button.className = 'quiet'; button.textContent = 'Load';
      button.addEventListener('click', () => run(async () => {
        if (!confirm('Load this version into the editor? Your current unsaved text will be replaced. Cloud history is preserved.')) return;
        const data = await api(`version?type=${type}&id=${encodeURIComponent(version.id)}`);
        bridge.setMarkdown(data.markdown);
        status('Earlier version loaded as a draft. Save it to create a new version.');
      }));
      item.append(text, button); $('versionHistory').append(item);
    }
    if (!data.versions.length && !append) {
      const item = document.createElement('li'); item.textContent = 'No saved versions yet. Your first save starts the history.';
      $('versionHistory').append(item);
    }
  }
  async function loadCloud() {
    const stamp = epoch;
    const data = await api(`current?type=${type}`);
    if (stamp !== epoch) return;
    revision = data.id;
    if (data.id && bridge.getMarkdown() !== data.markdown) {
      if (confirm('Load your latest cloud version? Choose Cancel to keep the draft currently in this browser.')) bridge.setMarkdown(data.markdown);
    }
    await history();
    status(data.id ? 'Cloud history loaded. Edit freely, then save a new version.' : 'Ready. Your first save will start private cloud history.');
  }
  $('openStudio').addEventListener('click', () => { bridge.openEditor(); });
  $('resumeType').addEventListener('change', () => run(async () => {
    type = $('resumeType').value; epoch++; revision = null; proposal = null;
    $('proposalReview').hidden = true; $('versionNote').value = '';
    await bridge.load(type);
    if (signedIn) await loadCloud();
    else status('Template loaded. Browser drafts are kept separately for each CV type.');
  }));
  $('studioLogin').addEventListener('submit', event => {
    event.preventDefault();
    run(async () => {
      const code = $('accessCode').value; $('accessCode').value = '';
      await api('login', {code}); showSession(true); await loadCloud();
    });
  });
  $('studioLogout').addEventListener('click', () => run(async () => {
    await api('logout', {}); showSession(false); status('Workspace locked. Your browser draft is still available in the editor.');
  }));
  $('generateCv').addEventListener('click', () => run(async () => {
    const instruction = $('aiPrompt').value.trim();
    if (!instruction) { $('aiPrompt').focus(); throw new Error('Describe the role, programme, or changes you want first.'); }
    status('Qwen is preparing a draft. This may take up to a minute.');
    const previous = bridge.getMarkdown();
    const data = await api('generate', {type, instruction, markdown: previous});
    proposal = data.markdown;
    $('aiNotes').textContent = data.notes || 'Review the draft for accuracy before using it.';
    $('previousDraft').textContent = previous;
    $('proposalReview').hidden = false;
    // Keep the generated text separate until the owner accepts it.
    let preview = $('proposedDraft');
    if (!preview) { preview = document.createElement('pre'); preview.id = 'proposedDraft'; $('proposalReview').insertBefore(preview, $('proposalReview').querySelector('.studio-row')); }
    preview.textContent = proposal;
    status('Draft ready for review. Your editor and saved versions are unchanged.');
  }));
  $('acceptDraft').addEventListener('click', () => {
    if (!proposal) return;
    bridge.setMarkdown(proposal); proposal = null; $('proposalReview').hidden = true;
    status('AI draft is now in the editor. Review the preview, then save a version or download.');
  });
  $('discardDraft').addEventListener('click', () => { proposal = null; $('proposalReview').hidden = true; status('AI draft discarded.'); });
  $('saveVersion').addEventListener('click', () => run(async () => {
    status('Saving a new version…');
    const data = await api('save', {type, markdown: bridge.getMarkdown(), baseId: revision, note: $('versionNote').value});
    revision = data.id; $('versionNote').value = ''; await history();
    status('Version saved. Previous versions remain available below.');
  }));
  $('refreshVersions').addEventListener('click', () => run(loadCloud));
  $('moreVersions').addEventListener('click', () => run(() => history(true)));
  api('session').then(data => {
    showSession(data.authenticated);
    if (signedIn) run(loadCloud);
  }).catch(() => status('Public templates and downloads are available. AI Studio needs the AWS backend.'));
})();
